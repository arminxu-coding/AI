import asyncio
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from openai import OpenAI


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # self.BASE_URL = "http://127.0.0.1:11434/v1/"
        # self.MODEL = "qwen2.5:1.5b "
        # self.OPENAI_API_KEY = "ollama"
        self.BASE_URL = "https://api.deepseek.com"
        self.MODEL = "deepseek-chat"
        self.OPENAI_API_KEY = "sk-17eba7d01e174e4c8712d3df62549101"

        # 这里我希望用ollama代替openai
        self.client = OpenAI(
            base_url=self.BASE_URL,
            # required but ignored
            api_key=self.OPENAI_API_KEY,
        )

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]

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
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        server_script_path = "./stdio_server.py"
    else:
        server_script_path = sys.argv[1]

    client = MCPClient()
    try:
        await client.connect_to_server(server_script_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
