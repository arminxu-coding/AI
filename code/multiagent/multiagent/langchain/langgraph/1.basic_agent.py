from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
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
https://docs.langchain.com/langgraph-platform/langgraph-basics/1-build-basic-chatbot
"""
graph_builder = StateGraph(State)

llm = init_chat_model(model="deepseek-chat", model_provider="deepseek")


def chatbot(state: State):
    """
    非流式的对话消息
    """
    print(f"receive user input : {state}")
    result = llm.invoke(state["messages"])
    print(f"llm invoke result : {result.model_dump_json()}")
    return {
        "messages": [result]
    }


# 为当前 graph agent 添加一个节点
graph_builder.add_node("chatbot", chatbot)
# 为图节点加上两条边
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
# 编译创建图
graph = graph_builder.compile()


# 图效果
# start -> chatbot -> end


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
            # 流式运行图
            stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break
