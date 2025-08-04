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

# 定义工具
search = TavilySearchResults(max_results=2)


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


tools = [search, get_weather]

# 为模型绑定工具，单步测试model的工具调用能力
# model.bind_tools(tools)
# response = model.invoke([HumanMessage(content="Hi!")])
# print(f"ContentString: {response.content}")
# print(f"ToolCalls: {response.tool_calls}")
#
# response = model.invoke([HumanMessage(content="What's the weather in SF?")])
# print(f"ContentString: {response.content}")
# print(f"ToolCalls: {response.tool_calls}")


# 获取prompt模板
prompt = hub.pull("hwchase17/openai-functions-agent")

# 创建agent & 代理执行器
agent = create_tool_calling_agent(model, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 手动回复对话历史
chat_history = []
response = agent_executor.invoke(
    {
        "chat_history": chat_history,
        "input": "hi!"
    }
)
print(response)
chat_history.append(HumanMessage(content="hi!"))
chat_history.append(AIMessage(content=response.get("output")))

response = agent_executor.invoke(
    {
        "chat_history": chat_history,
        "input": "What's the weather in SF?"
    }
)
print(response)


store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# 自动回复对话历史
agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)
response = agent_with_chat_history.invoke(
    {"input": "hi! I'm bob"},
    config={"configurable": {"session_id": "<foo>"}},
)
print(response)

response = agent_with_chat_history.invoke(
    {"input": "what's my name?"},
    config={"configurable": {"session_id": "<foo>"}},
)
print(response)
