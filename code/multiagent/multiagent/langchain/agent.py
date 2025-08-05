import asyncio
from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chat_models import init_chat_model
from langchain_community.tools import TavilySearchResults
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.tools import tool

load_dotenv("../../.env")

model = init_chat_model(model="deepseek-chat", model_provider="deepseek")

"""
langchain实现agent chain功能
"""

@tool
def get_weather(location: str) -> str:
    """
    获取指定城市的当前时刻天气
    Args:
        location: 字符串类型，城市名称

    Returns:
         str: 当前城市的天气详情
    """
    return "The weather in " + location + " is clear and sunny，temperature is 25摄氏度"


# 定义工具
search = TavilySearchResults(max_results=2)

tools = [search, get_weather]


def model_test():
    # 为模型绑定工具，单步测试model的工具调用能力
    model.bind_tools(tools)
    response = model.invoke([HumanMessage(content="Hi!")])
    print(f"ContentString: {response.content}")
    print(f"ToolCalls: {response.tool_calls}")

    response = model.invoke([HumanMessage(content="What's the weather in SF?")])
    print(f"ContentString: {response.content}")
    print(f"ToolCalls: {response.tool_calls}")


# 获取prompt模板
# [
#   prompt=PromptTemplate(template='You are a helpful assistant')
#   variable_name='chat_history' optional=True
#   prompt=PromptTemplate(template='{input}')
#   variable_name='agent_scratchpad'
# ]
prompt = hub.pull("hwchase17/openai-functions-agent")

# 创建agent & 代理执行器
agent = create_tool_calling_agent(model, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, tools=tools
    # ,verbose=True
)

# 手动维护对话历史
chat_history = []


def invoke():
    # 非流式执行，只要最后的结果
    query = "hi! I'm bob"
    response = agent_executor.invoke(
        {
            "chat_history": chat_history,
            "input": query
        }
    )
    print(response)

    chat_history.append(HumanMessage(content=query))
    chat_history.append(AIMessage(content=response.get("output")))
    response = agent_executor.invoke(
        {
            "chat_history": chat_history,
            "input": "What's the weather in SF?"
        }
    )
    print(response)


def stream():
    # 执行agent 使用流式返回 每一个关键步骤
    for chunk in agent_executor.stream(
            {
                "chat_history": chat_history,
                "input": "What's the weather in SF?",
            }
    ):
        print(chunk)
        print("----")


async def astream_events():
    # 流式返回令牌
    async for event in agent_executor.astream_events(
            {
                "chat_history": chat_history,
                "input": "What's the weather in SF?",
            },
            version="v1"
    ):
        kind = event["event"]
        if kind == "on_chain_start":
            # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
            # print(f"Starting agent: {event['name']} with input: {event['data'].get('input')}")
            pass
        elif kind == "on_chain_end":
            # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
            # print()
            # print("--")
            # print(f"Done agent: {event['name']} with output: {event['data'].get('output')}")
            pass
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means
                # that the model is asking for a tool to be invoked.
                # So we only print non-empty content
                print(content, end="")
        elif kind == "on_tool_start":
            print("--")
            print(f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}")
        elif kind == "on_tool_end":
            print(f"Done tool: {event['name']}")
            print(f"Tool output was: {event['data'].get('output')}")
            print("--")


store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    # 自定义的会话管理方法，可自定义为任意存储方式：memory、redis、mysql...
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def auto_with_history():
    # 自动回复对话历史 agent
    config = {"configurable": {"session_id": "<foo>"}},
    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    response = agent_with_chat_history.invoke(
        {"input": "hi! I'm bob"},
        config=config
    )
    print(response)
    response = agent_with_chat_history.invoke(
        {"input": "what's my name?"},
        config=config
    )
    print(response)


if __name__ == '__main__':
    asyncio.run(astream_events())
