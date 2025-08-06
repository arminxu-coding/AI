from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

load_dotenv("../../../.env")


class State(TypedDict):
    messages: Annotated[list, add_messages]


"""
基于内存保存会话历史agent
https://docs.langchain.com/langgraph-platform/langgraph-basics/3-add-memory
"""
graph_builder = StateGraph(State)


@tool
def get_weather(location: str) -> str:
    """
    获取指定城市的当前时刻天气
    Args:
        location: 字符串类型，城市名称

    Returns:
         str: 当前城市的天气详情
    """
    print(f"执行了 get weather tool，其中参数 location：{location}")
    return "The weather in " + location + " is clear and sunny，temperature is 25摄氏度"


tools = [
    TavilySearchResults(max_results=2),
    get_weather
]

llm_with_tools = init_chat_model(model="deepseek-chat", model_provider="deepseek").bind_tools(tools)


def chatbot(state: State):
    """
    非流式的对话消息
    """
    message_str = "\n".join([message.model_dump_json(exclude_none=True) for message in state["messages"]])
    print(f"receive user input:\n{message_str}")

    result = llm_with_tools.invoke(state["messages"])
    print(f"llm invoke result : {result.model_dump_json()}")

    return {
        "messages": [result]
    }


graph_builder.set_entry_point("chatbot")  # 设置初始节点
# 添加节点
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))
# 添加节点路由关系
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
# 创建会话内存自动管理模块
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "1"}}


def stream_graph_updates(user_input: str):
    for event in graph.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config,
            stream_mode="values",
    ):
        event["messages"][-1].pretty_print()


if __name__ == '__main__':
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break
