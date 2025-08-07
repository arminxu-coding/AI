"""
多服务器 MCP + LangChain Agent 示例
---------------------------------
1. 读取 .env 中的 OPENAI_API_KEY / OPENAI_BASE_URL / MODEL
2. 读取 servers_config.json 中的 MCP 服务器信息
3. 启动 MCP 服务器（支持多个）
4. 将所有工具注入 LangChain Agent，由大模型自动选择并调用
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.chat_models import init_chat_model
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_mcp_adapters.client import MultiServerMCPClient


# ────────────────────────────
# 环境配置
# ────────────────────────────

class Configuration:
    """读取 .env 与 servers_config.json"""

    def __init__(self) -> None:
        load_dotenv()
        self.api_key: str = os.getenv("OPENAI_API_KEY") or ""
        self.base_url: str | None = os.getenv("OPENAI_BASE_URL")  # DeepSeek 用 https://api.deepseek.com
        self.model: str = os.getenv("MODEL") or "deepseek-chat"
        if not self.api_key:
            raise ValueError("❌ 未找到 OPENAI_API_KEY，请在 .env 中配置")

    @staticmethod
    def load_servers(file_path: str = "servers_config.json") -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f).get("mcpServers", {})
        except Exception as exc:
            logging.error(f"❌ 读取 {file_path} 失败：{exc}")
        return {
            "CommonToolServer": {
                "command": "python",
                "args": [
                    "../mcp/standard_common_tool_server.py"
                ],
                "transport": "stdio"
            },
            "WriteServer": {
                "command": "python",
                "args": [
                    "../mcp/standard_write_server.py"
                ],
                "transport": "stdio"
            }
        }


store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    # 自定义的会话管理方法，可自定义为任意存储方式：memory、redis、mysql...
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# ────────────────────────────
# 主逻辑
# ────────────────────────────
async def run_chat_loop() -> None:
    """启动 MCP-Agent 聊天循环"""
    cfg = Configuration()
    servers_cfg = Configuration.load_servers()

    # 1️⃣ 连接多台 MCP 服务器
    mcp_client = MultiServerMCPClient(servers_cfg)

    tools = await mcp_client.get_tools()  # LangChain Tool 对象列表

    logging.info(f"✅ 已加载 {len(tools)} 个 MCP 工具： {[t.name for t in tools]}")

    # 2️⃣ 初始化大模型（DeepSeek / OpenAI / 任意兼容 OpenAI 协议的模型）
    llm = init_chat_model(
        model=cfg.model,
        model_provider="deepseek" if "deepseek" in cfg.model else "openai",
    )

    # 3️⃣ 构造 LangChain Agent（用通用 prompt）
    prompt = hub.pull("hwchase17/openai-tools-agent")
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # 自动回复对话历史 agent
    config = {"configurable": {"session_id": "<foo>"}}
    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    # 4️⃣ CLI 聊天
    print("\n🤖 MCP Agent 已启动，输入 'quit' 退出")
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() == "quit":
            break
        try:
            result = await agent_with_chat_history.ainvoke(
                {"input": user_input},
                config=config
            )
            print(f"\nAI: {result['output']}")
        except Exception as exc:
            print(f"\n⚠️  出错: {exc}")

    # 5️⃣ 清理
    await mcp_client.cleanup()
    print("🧹 资源已清理，Bye!")


# ────────────────────────────
# 入口
# ────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(run_chat_loop())
