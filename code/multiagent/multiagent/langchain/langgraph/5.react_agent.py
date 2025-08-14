"""
基于react模式使用的agent，采用的是官方标准预构建的agent结构
使用非常简单，也是我们平时最常用的一种agent模式，建议深度debug一下，学习原理、设计思路
"""
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

load_dotenv("../../../.env")


class WeatherQuery(BaseModel):
    location: str = Field(description="需要查询添加的城市名称")


@tool(args_schema=WeatherQuery)
def get_weather(location: str) -> str:
    """
    获取指定城市的当前时刻天气
    Args:
        location: 字符串类型，需要查询添加的城市名称
    Returns:
         str: 当前城市的天气详情
    """
    print(f"执行了 get weather tool，其中参数 location：{location}")
    return "当前 " + location + " 天气是非常清爽和舒服的，阳光正好、气温为25摄氏度"


@tool
def write_to_file(content: str) -> str:
    """
    将对应的内容写入文件
    Args:
        content: 需要写入文件的具体内容
    Returns:
        str: 内容写入文件的结果
    """
    print("正在将内容写入文件中.....")
    print(f"内容为：{content}")
    print("已经完成将内容写入文件")
    return "内容写入文件成功"


tools = [
    TavilySearchResults(max_results=2),
    get_weather,
    write_to_file
]

llm = init_chat_model(model="deepseek-chat", model_provider="deepseek")
agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=InMemorySaver()  # 创建会话内存自动管理模块
)

config = {"configurable": {"thread_id": "1"}}


def chat_bot(query: str):
    for chunk in agent.stream(
            {
                "messages": [
                    {"role": "user", "content": query}
                ]
            },
            config
    ):
        print(chunk)


if __name__ == '__main__':
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            chat_bot(user_input)
        except:
            print("报错了，自动退出 bye")
            break
