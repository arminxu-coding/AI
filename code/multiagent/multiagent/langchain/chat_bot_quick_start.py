from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from typing import Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

load_dotenv("../../.env")

"""
基于langchain实现一个带有记忆的chatbot
"""

model = init_chat_model(model="deepseek-chat", model_provider="deepseek")

prompt_template = ChatPromptTemplate.from_messages(  # 构建一个标准的prompt模版
    [
        (
            "system",
            "You are a helpful assistant. Answer all questions to the best of your ability in {language}.",  # 埋了一个变量
        ),
        MessagesPlaceholder(variable_name="messages"),  # 一个占位符，用于填充历史消息
    ]
)


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


workflow = StateGraph(state_schema=State)  # MessagesState


def call_model(state: State):
    prompt = prompt_template.invoke(state)
    response = model.invoke(prompt)
    return {"messages": [response]}


workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

memory = MemorySaver()  # Add memory
app = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "abc123"}}  # 定义对话线程id（类似于会话id）

output = app.invoke(
    {
        "messages": [HumanMessage("Hi! I'm Bob.")],
        "language": "English"
    },
    config
)
output["messages"][-1].pretty_print()

output = app.invoke(
    {
        "messages": [HumanMessage("What's my name?")],
        "language": "中文"
    },
    config
)
output["messages"][-1].pretty_print()
