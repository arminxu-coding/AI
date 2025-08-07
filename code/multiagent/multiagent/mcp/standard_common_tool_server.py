import datetime
from typing import Literal

from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("CommonToolServer")


async def fetch_weather(city: str) -> str:
    """
    从 OpenWeather API 获取天气信息。
    :param city: 城市名称（需使用英文，如 Beijing）
    :return: 天气数据字典；若出错返回包含 error 信息的字典
    """
    return (
        f"🌍 {city}\n"
        f"🌡 温度: 25°C\n"
        f"💧 湿度: 60%\n"
        f"🌬 风速: 120 m/s\n"
        f"🌤 天气: 阴\n"
    )


@mcp.tool()
async def query_weather(city: str) -> str:
    """
    输入指定城市的英文名称，返回今日天气查询结果。
    :param city: 城市名称（需使用英文）
    :return: 格式化后的天气信息
    """
    return await fetch_weather(city)


@mcp.tool()
def get_current_time(
        format: Literal["iso", "readable", "timestamp"] = "readable",
        timezone: str = "UTC"
) -> str:
    """
    获取当前时间信息，支持多种格式和时区。

    参数:
    format: 时间格式，可选值：
        - "iso": ISO 8601 格式 (例如 "2025-05-04T14:30:45+00:00")
        - "readable": 人类可读格式 (例如 "2025年05月04日 14:30:45")
        - "timestamp": Unix 时间戳 (例如 "1746398445")
    timezone: 时区名称，如 "UTC", "Asia/Shanghai", "America/New_York" 等

    返回:
    格式化的时间字符串
    """
    # 获取当前时间（默认 UTC）
    now = datetime.datetime.now(datetime.timezone.utc)

    # 转换为指定时区（简化版，实际应用中应使用 pytz 或 zoneinfo）
    if timezone != "UTC":
        # 简化的时区处理（实际应用应使用更完整的时区处理）
        if timezone == "Asia/Shanghai":
            offset = datetime.timedelta(hours=8)
            now = now.astimezone(datetime.timezone(offset, "CST"))
        elif timezone == "America/New_York":
            offset = datetime.timedelta(hours=-4)
            now = now.astimezone(datetime.timezone(offset, "EDT"))
        # 可以添加更多时区处理...

    # 按指定格式返回时间
    if format == "iso":
        return now.isoformat()
    elif format == "readable":
        return now.strftime("%Y年%m月%d日 %H:%M:%S")
    elif format == "timestamp":
        return str(int(now.timestamp()))
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    # 以标准 I/O 方式运行 MCP 服务器
    mcp.run(transport='stdio')
