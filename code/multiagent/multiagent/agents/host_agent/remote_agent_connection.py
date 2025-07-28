from typing import Callable
import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    Task,
    Message,
    MessageSendParams,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    SendMessageRequest,
    SendStreamingMessageRequest,
    JSONRPCErrorResponse,
)
from uuid import uuid4

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client: httpx.AsyncClient, agent_card: AgentCard):
        # 标准的 aca client，用于连接 agent服务端，并于其建立连接 进行agent进行通信【必须保证对方agent是满足于a2a协议的才能进行通信】
        self.agent_client = A2AClient(client, agent_card)
        self.card = agent_card
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
            self,
            request: MessageSendParams,
            task_callback: TaskUpdateCallback | None,
    ) -> Task | Message | None:
        if self.card.capabilities.streaming:  # 流式传输
            task = None
            # 流式的发送消息，其中 SendStreamingMessageRequest()就是具体的请求体
            # 虽然是流式的发送响应，但是实际只会获取一个响应体 最后进行return
            async for response in self.agent_client.send_message_streaming(
                    SendStreamingMessageRequest(id=str(uuid4()), params=request)
            ):
                if not response.root.result:
                    return response.root.error
                # In the case a message is returned, that is the end of the interaction.
                event = response.root.result
                if isinstance(event, Message):
                    return event

                # Otherwise we are in the Task + TaskUpdate cycle.
                if task_callback and event:
                    task = task_callback(event, self.card)
                if hasattr(event, 'final') and event.final:
                    break
            return task
        else:  # Non-streaming， 非流式传输
            response = await self.agent_client.send_message(
                SendMessageRequest(id=str(uuid4()), params=request)
            )
            if isinstance(response.root, JSONRPCErrorResponse):
                return response.root.error
            if isinstance(response.root.result, Message):
                return response.root.result

            if task_callback:
                task_callback(response.root.result, self.card)
            return response.root.result
