from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt, Command
from typing_extensions import TypedDict

load_dotenv("../../../.env")


class State(TypedDict):
    messages: Annotated[list, add_messages]


"""
基于 human in the loop 可打断的agent
https://docs.langchain.com/langgraph-platform/langgraph-basics/4-human-in-the-loop
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


@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    # 这个工具的作用是 请求人类帮助，其实就是一个正常的工具，只不过其中实现调用了下面的 interrupt() 方法，是一个比较特殊的跳脱方法
    # 有点兜底tool的感觉，但是又不一样，因为这里是可以直接要求用户询问帮助，我认为 无非就是实现更加系统化了 更加高级了
    print(f"进入了 human_assistance 工具，用户请求为：{query}")
    # 这里即会被进行中断tool执行，卡在这里，只有等待再次接收到用户的命令才会继续执行下去
    # 如果当前agent接收到的消息不是 用户的Command 而是一个正常的query消息，那么框架层就会报错
    human_response = interrupt({"query": query})
    # 这里应该是接收到用户Command的消息之后，继续特定的处理，作为新的辅助消息，让这个工具继续执行下去最终得到一个 ToolResponse
    print(f"获取到用户的反馈，反馈内容为：{human_response}")
    return human_response["data"]


tools = [
    TavilySearchResults(max_results=2),
    get_weather,
    human_assistance
]

llm = init_chat_model(model="deepseek-chat", model_provider="deepseek")

llm_with_tools = llm.bind_tools(tools)


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
    # 打断类型的用户响应query
    if user_input.startswith("human_command:"):
        input = Command(resume={"data": user_input.replace("human_command:", "")})
    else:
        input = {"messages": [{"role": "user", "content": user_input}]}

    for event in graph.stream(input, config, stream_mode="values", ):
        event["messages"][-1].pretty_print()


if __name__ == '__main__':
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
