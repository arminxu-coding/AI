import json
from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv("../../../.env")


class State(TypedDict):
    # 定义一个langgraph中传输的消息列表messages（先别管为啥这么定义）
    messages: Annotated[list, add_messages]


"""
其实下面这个不能完全算是一个agent，更像是一个chain
但是也具有agent灵活的表现了，没事：一步一步的来 会更加深入的
https://docs.langchain.com/langgraph-platform/langgraph-basics/2-add-tools
"""
graph_builder = StateGraph(State)

llm = init_chat_model(model="deepseek-chat", model_provider="deepseek")


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
    TavilySearchResults(max_results=2),  # langchain 实现的网络搜索工具
    get_weather  # 自定义的工具
]

llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):
    """
    非流式的对话消息
    """
    message_str = "\n".join([message.model_dump_json(exclude_none=True) for message in state["messages"]])
    print(f"receive user input : {message_str}")

    result = llm_with_tools.invoke(state["messages"])
    print(f"llm invoke result : {result.model_dump_json()}")

    return {
        "messages": [result]
    }


graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")

"""
到目前为止，其实和之前的 basic agent 没啥大区别，因为我们创建的tools其实并没有完全应用上
仅仅是llm会根据query返回 tool call，但是实际上tool并没有执行
"""


class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}


# 创建执行工具节点
tool_node = BasicToolNode(tools=tools)
# 添加工具节点
graph_builder.add_node("tools", tool_node)


def route_rule(state: State) -> str:
    """
    定义节点路由函数，每次llm执行完之后，会调用当前函数 决策现在应该执行哪一个节点
    也就是边路由规则，返回啥 就执行哪一个节点
    Args:
        state: 当前llm执行返回的消息列表

    Returns:
        str: 返回当前应该执行的节点name
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END


graph_builder.add_conditional_edges(
    "chatbot",  # 起点入口
    route_rule,  # 路由规则
    {  # 匹配规则，key代表 route_rule返回的值，value代表 节点name
        "tools": "tools",
        END: END
    },
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile()


def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


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
