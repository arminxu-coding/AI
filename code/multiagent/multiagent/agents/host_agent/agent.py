import base64
import json
import uuid

from typing import List, Optional, Dict, Any

import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    DataPart,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    TextPart,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from multiagent.agents.host_agent.remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from multiagent.agents.models.request.chat import ChatRequest


class HostAgent:
    """The host agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """

    def __init__(
            self,
            remote_agent_addresses: list[str],
            http_client: httpx.AsyncClient,
            task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.httpx_client = http_client
        self.remote_agent_addresses = remote_agent_addresses
        # 远程agent的连接对象，属于host_agent的单独实现方案 可任意定制，只需要保证 host_agent 和于远程agent正常建立请求即可
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        # agent_card的存储列表，key为agent_name，value为agent_card实例对象信息
        self.cards: dict[str, AgentCard] = {}
        # 远程agent的描述信息， 为一个字符串，是有 [{"name": "agent_name", "desc": "agent_desc"}] 拼接为一个字符串组成
        self.agents: str = ""

    async def chat_stream(self, request: ChatRequest):
        # TODO 调用model进行选择 agent -- start
        # mock 调用大模型执行了 选择agent
        root_agent = self.create_agent()
        agent_name = "机票 Agent"
        # TODO 调用model进行选择 agent -- end

        # 向远程 agent 发送消息
        response = await self.send_message(agent_name, request.query)

        yield response

    async def send_message(
            self,
            agent_name: str,
            message: str,
            # tool_context: ToolContext = None
    ) -> List[str | dict | DataPart]:
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.

        Yields:
          A dictionary of JSON data.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        client: RemoteAgentConnections = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')
        messageId = None

        # mock 假数据
        contextId = None
        taskId = None
        if not messageId:
            messageId = str(uuid.uuid4())
        if not contextId:
            contextId = str(uuid.uuid4())
        if not taskId:
            taskId = str(uuid.uuid4())

        request: MessageSendParams = MessageSendParams(
            id=str(uuid.uuid4()),
            message=Message(
                role='user',
                parts=[TextPart(text=message)],
                messageId=messageId,
                contextId=contextId,
                taskId=taskId,
            ),
            configuration=MessageSendConfiguration(
                acceptedOutputModes=['text', 'text/plain', 'image/png'],
            ),
        )
        response = await client.send_message(request, self.task_callback)

        return response

    def list_remote_agents(self) -> List[Dict[str, Any]]:
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(self.httpx_client, card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        self.agents = '\n'.join(agent_info)

    def create_agent(self) -> Agent:
        return Agent(
            model='gemini-2.0-flash-001',
            name='host_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This agent orchestrates the decomposition of the user request into'
                ' tasks that can be performed by the child agents.'
            ),
            tools=[
                self.list_remote_agents,
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_state(context)
        return f"""
You are an expert delegator that can delegate the user request to the
appropriate remote agents.

Discovery:
- You can use `list_remote_agents` to list the available remote agents you
can use to delegate the task.

Execution:
- For actionable requests, you can use `send_message` to interact with remote agents to take action.

Be sure to include the remote agent name when you respond to the user.

Please rely on tools to address the request, and don't make up the response. If you are not sure, please ask the user for more details.
Focus on the most recent parts of the conversation primarily.

Agents:
{self.agents}

Current agent: {current_agent['active_agent']}
"""

    def check_state(self, context: ReadonlyContext):
        state = context.state
        if (
                'context_id' in state
                and 'session_active' in state
                and state['session_active']
                and 'agent' in state
        ):
            return {'active_agent': f'{state["agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
            self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            state['session_active'] = True


async def convert_parts(parts: list[Part], tool_context: ToolContext) -> List[str | dict | DataPart]:
    rval = []
    for p in parts:
        rval.append(await convert_part(p, tool_context))
    return rval


async def convert_part(part: Part, tool_context: ToolContext) -> str | dict | DataPart:
    if part.root.kind == 'text':
        return part.root.text
    elif part.root.kind == 'data':
        return part.root.data
    elif part.root.kind == 'file':
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files
        file_id = part.root.file.name
        file_bytes = base64.b64decode(part.root.file.bytes)
        file_part = types.Part(
            inline_data=types.Blob(
                mime_type=part.root.file.mimeType, data=file_bytes
            )
        )
        await tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data={'artifact-file-id': file_id})
    return f'Unknown type: {part.kind}'


async def create_host_agent(
        remote_agent_addresses: list[str],
        http_client: httpx.AsyncClient,
        task_callback: Optional[TaskUpdateCallback] = None
) -> HostAgent:
    agent = HostAgent(
        remote_agent_addresses=remote_agent_addresses,
        http_client=http_client,
        task_callback=task_callback
    )

    for address in agent.remote_agent_addresses:
        resolver = A2ACardResolver(http_client, address)
        card: AgentCard = await resolver.get_agent_card()
        connection = RemoteAgentConnections(http_client, card)
        agent.remote_agent_connections[card.name] = connection
        agent.cards[card.name] = card

    agent_info = []
    for ra in agent.list_remote_agents():
        agent_info.append(json.dumps(ra, ensure_ascii=False))
    agent.agents = "\n".join(agent_info)

    return agent
