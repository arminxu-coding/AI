from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
import json
import os
from bs4 import BeautifulSoup
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import aiohttp
from typing import Literal
from datetime import datetime

load_dotenv()

# 实例化有一个mcp服务器
mcp = FastMCP("docs")

USER_AGENT = "docs-multiagent/1.0"
SERPER_URL = "https://google.serper.dev/search"

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "autogen": "microsoft.github.io/autogen/stable",
    "agno": "docs.agno.com",
    "openai-agents-sdk": "openai.github.io/openai-agents-python",
    "mcp-doc": "modelcontextprotocol.io",
    "camel-ai": "docs.camel-ai.org",
    "crew-ai": "docs.crewai.com"
}


async def search_web(query: str) -> dict | None:
    """
    搜索给定查询的最新文档
    :param query: 要搜索的查询 (例如 "React Agent")
    :return: 搜索结果
    """
    # 构造搜索请求的payload，包含查询词和返回结果数量
    # q: 搜索查询词
    # num: 返回结果数量限制为2条
    payload = json.dumps({"q": query, "num": 2})

    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            # 发送POST请求到SERPER_URL，并设置请求头和超时时间
            response = await client.post(
                SERPER_URL, headers=headers, data=payload, timeout=30.0
            )
            # 确保请求成功
            response.raise_for_status()
            # 返回JSON响应
            return response.json()
        except httpx.TimeoutException:
            # 如果请求超时，返回空结果
            return {"organic": []}


async def fetch_url(url: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()
            return text
        except httpx.TimeoutException:
            return "Timeout error"


# 搜索给定查询和库的最新文档
@mcp.tool()
async def get_docs(query: str, library: str):
    """
    搜索给定查询和库的最新文档。
    支持 langchain、llama-index、autogen、agno、openai-agents-sdk、mcp-doc、camel-ai 和 crew-ai。

    参数:
    query: 要搜索的查询 (例如 "React Agent")
    library: 要搜索的库 (例如 "agno")

    返回:
    文档中的文本
    """
    if library not in docs_urls:
        raise ValueError(f"Library {library} not supported by this tool")

    query = f"site:{docs_urls[library]} {query}"
    # 搜索给定查询和库的最新文档
    results = await search_web(query)
    if len(results["organic"]) == 0:
        return "No results found"

    text = ""
    for result in results["organic"]:
        # 获取文档的URL
        text += await fetch_url(result["link"])

    return text


@mcp.tool()
async def get_weather(
        city: str,
        district: str = None,

        province: str = None,
        unit: Literal["celsius", "fahrenheit"] = "celsius"
) -> str:
    """
    获取中国城市实时天气信息（基于中国气象局数据）
    支持省/市/区三级精确查询，默认返回温度、天气状况、湿度和风力

    参数:
    city: 城市名称（如"北京"）
    district: 区/县名称（可选，如"海淀区"）
    province: 省份名称（可选，如"北京市"）
    unit: 温度单位，默认为"celsius"（摄氏度）

    返回:
    结构化天气信息字符串，例如：
    "北京市海淀区: 晴 25°C, 湿度45%, 东南风3级, 更新时间: 2023-07-15 14:00"

    异常:
    ValueError: 当城市不存在或API请求失败时抛出
    """
    # 1. 参数校验
    if unit not in ["celsius", "fahrenheit"]:
        raise ValueError("温度单位必须是'celsius'或'fahrenheit'")

    # 2. 构建查询地址（使用中国气象局API）
    base_url = "http://www.weather.com.cn/data/sk/{code}.html"

    # 获取城市代码（实际项目需接入城市代码查询服务）
    location_code = await _get_location_code(
        province=province or city,
        city=city,
        district=district
    )

    # 3. 调用API
    # mock数据
    return (f"天气：晴； 温度：25°C； 湿度：45%； 风力：东南风3级； 更新时间：2025-05-04 14:00"
            f"原始信息: {city} {district} {province} {unit}")
    # try:
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(base_url.format(code=location_code)) as resp:
    #             if resp.status != 200:
    #                 raise ValueError(f"气象局接口异常 HTTP {resp.status}")
    #
    #             data = await resp.json(content_type=None)
    #             weather_info = data["weatherinfo"]
    #
    #             # 4. 单位转换（气象局默认返回摄氏度）
    #             temp = float(weather_info["temp"])
    #             if unit == "fahrenheit":
    #                 temp = temp * 9 / 5 + 32
    #
    #             # 5. 结构化返回
    #             return (
    #                 f"{weather_info['city']}: {weather_info['weather']} {temp:.1f}°{'C' if unit == 'celsius' else 'F'}, "
    #                 f"湿度{weather_info['SD']}, {weather_info['WD']}{weather_info['WS']}, "
    #                 f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    #             )
    #
    # except (aiohttp.ClientError, KeyError) as e:
    #     raise ValueError(f"获取天气数据失败: {str(e)}")


async def _get_location_code(province: str, city: str, district: str = None) -> str:
    """模拟获取城市代码（实际项目需接入官方城市代码API）"""
    # 构建城市代码映射字典
    city_codes = {
        "北京": {
            "市辖区": {
                "海淀区": "101010200",
                "朝阳区": "101010300",
                "东城区": "101010100",
                "西城区": "101010200",
            }
        },
        "上海": {
            "市辖区": {
                "浦东新区": "101020600",
                "黄浦区": "101020100",
            }
        },
        "广州": {
            "市辖区": {
                "天河区": "101280100",
                "越秀区": "101280100",
            }
        }
    }

    try:
        # 如果提供了区县信息,优先按省市区查询
        if district:
            return city_codes[province][city][district]

        # 如果只提供省市,返回市级代码
        if city in city_codes[province]:
            # 返回该市第一个区的代码作为市级代码
            first_district = list(city_codes[province][city].keys())[0]
            return city_codes[province][city][first_district]

        # 如果只提供省份,返回省会城市代码
        if province in city_codes:
            first_city = list(city_codes[province].keys())[0]
            first_district = list(city_codes[province][first_city].keys())[0]
            return city_codes[province][first_city][first_district]

    except KeyError:
        raise ValueError(f"未找到对应的城市代码: 省={province}, 市={city}, 区={district}")
    # 这里应该是调用城市代码查询服务的逻辑
    # 示例返回北京海淀区代码（实际需要动态查询）
    return "101010200"  # 北京海淀区代码


## sse传输
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    # 创建SSE传输对象
    sse = SseServerTransport("/messages/")

    # 处理SSE请求
    async def handle_sse(request: Request) -> None:
        # 使用SSE传输对象连接SSE请求
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            # 运行MCP服务器
            await mcp_server.run(
                read_stream,  # 从客户端读取消息的流对象
                write_stream,  # 向客户端发送消息的流对象
                mcp_server.create_initialization_options(),  # 初始化选项
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),  # 处理SSE请求的路由
            Mount("/messages/", app=sse.handle_post_message),  # 挂载SSE处理的路由
        ],
    )


if __name__ == "__main__":
    # 创建MCP服务器实例
    mcp_server = mcp._mcp_server

    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8020, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    # 启动服务器
    # 使用uvicorn运行Starlette应用
    # host: 监听的主机地址,默认为0.0.0.0表示监听所有网卡
    # port: 监听的端口号,默认为8020
    uvicorn.run(starlette_app, host=args.host, port=args.port)

    # uv run sse_server.py --host 0.0.0.0 --port 8020
