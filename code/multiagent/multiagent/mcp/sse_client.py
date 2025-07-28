import asyncio
import json
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
        # self.BASE_URL = "http://127.0.0.1:11434/v1/"
        # self.MODEL = "qwen2.5:1.5b "
        # self.OPENAI_API_KEY = "ollama"
        self.BASE_URL = "https://api.deepseek.com"
        self.MODEL = "deepseek-chat"
        self.OPENAI_API_KEY = "sk-114cb5d9b3364649bd7ab553c3c06ea1"

        # 打印大模相关信息
        print("环境变量信息：")
        print(f"self.BASE_URL: {self.BASE_URL}")
        print(f"self.MODEL: {self.MODEL}")
        print(f"self.OPENAI_API_KEY: {self.OPENAI_API_KEY}")

        # 这里我希望用ollama代替openai
        self.client = OpenAI(
            base_url=self.BASE_URL,
            # required but ignored
            api_key=self.OPENAI_API_KEY,
        )

    async def connect_to_sse_server(self, server_url: str):
        """连接到使用SSE传输的MCP服务器"""
        # 保存上下文管理器以保持其存活
        self._streams_context = sse_client(url=server_url)
        # 进入SSE客户端上下文,获取数据流
        streams = await self._streams_context.__aenter__()

        # 使用数据流创建客户端会话上下文
        self._session_context = ClientSession(*streams)
        # 进入会话上下文,获取会话对象
        self.session: ClientSession = await self._session_context.__aenter__()

        # 初始化会话
        await self.session.initialize()

        # 列出可用的工具以验证连接
        print("已初始化SSE客户端...")
        print("正在列出工具...")
        # 获取服务器支持的工具列表
        response = await self.session.list_tools()
        tools = response.tools
        print("\n已连接到服务器,可用工具:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """使用OpenAI API和可用工具处理查询"""

        # 构建初始消息列表
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        # 获取可用工具列表
        response = await self.session.list_tools()
        # 将工具转换为OpenAI API需要的格式
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]

        # 调用OpenAI API进行初始对话
        # 注释掉原始的AsyncOpenAI调用
        # completion0 = await self.openai.chat.completions.create(
        #     model=os.getenv("OPENAI_MODEL"),
        #     max_tokens=1000,
        #     messages=messages,
        #     tools=available_tools
        # )
        # 使用Ollama API进行对话
        completion = self.client.chat.completions.create(
            messages=messages,
            tools=available_tools,
            model=self.MODEL,
        )

        # 处理响应并处理工具调用
        tool_results = []  # 存储工具调用结果
        final_text = []  # 存储最终输出文本

        # 获取助手的回复消息
        assistant_message = completion.choices[0].message

        # 如果助手要调用工具
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # 执行工具调用
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # 将工具调用结果添加到对话历史
                messages.extend([
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    },
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text
                    }
                ])

                # 打印工具调用结果
                print(f"Tool {tool_name} returned: {result.content[0].text}")
                print("messages", messages)

                # 使用工具调用结果继续对话
                # 注释掉原始的AsyncOpenAI调用
                # completion0 = await self.openai.chat.completions.create(
                #     model=os.getenv("OPENAI_MODEL"),
                #     max_tokens=1000,
                #     messages=messages,
                # )
                # 使用Ollama API继续对话
                completion = self.client.chat.completions.create(
                    messages=messages,
                    # tools=available_tools,  # 后续对话不需要工具列表
                    model=self.MODEL,
                )

                # 处理返回的消息内容
                if isinstance(completion.choices[0].message.content, (dict, list)):
                    final_text.append(str(completion.choices[0].message.content))
                else:
                    final_text.append(completion.choices[0].message.content)
        else:
            # 如果助手不需要调用工具,直接添加回复内容
            if isinstance(assistant_message.content, (dict, list)):
                final_text.append(str(assistant_message.content))
            else:
                final_text.append(assistant_message.content)

        # 将所有回复内容合并成一个字符串返回
        return "\n".join(final_text)

    async def chat_loop(self):
        """运行交互式聊天循环"""
        # 打印启动提示信息
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                # 获取用户输入的查询内容
                query = input("\nQuery: ").strip()

                # 如果输入quit则退出循环
                if query.lower() == 'quit':
                    break

                # 处理查询并获取响应
                response = await self.process_query(query)
                # 打印响应结果
                print("\n" + response)

            except Exception as e:
                # 捕获并打印任何异常
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """正确清理会话和数据流"""
        # 如果存在会话上下文,则退出会话上下文
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        # 如果存在数据流上下文,则退出数据流上下文
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)


async def main():
    # 检查命令行参数是否足够
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URL of SSE MCP server (i.e. http://localhost:8080/sse)>")
        sys.exit(1)

    # 创建MCP客户端实例
    client = MCPClient()
    try:
        # 连接到SSE服务器
        await client.connect_to_sse_server(server_url=sys.argv[1])
        # 启动交互式聊天循环
        await client.chat_loop()
    finally:
        # 确保在退出时清理资源
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())

    # uv run sse_client.py http://0.0.0.0:8020/sse
