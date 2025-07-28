import time
import traceback
from typing import Callable, AsyncGenerator
from sse_starlette.sse import ServerSentEvent

from multiagent.agents.models.request.base import BaseRequest
from multiagent.agents.models.response.base import BaseResponse


def base_sse_wrapper(
        generator_func: Callable[[BaseRequest], AsyncGenerator[BaseResponse, None]],
        request: BaseRequest,
        access_log: bool = True,
        report_monitor: bool = True
) -> Callable[[], AsyncGenerator[ServerSentEvent, None]]:
    """
    基础的流式请求响应包装方法
    Args:
        generator_func: 被调用的方法，是一个Callable异步方法，参数是BaseRequest, 返回值是一个AsyncGenerator，响应内容是BaseResponse
        request: 请求参数
        access_log: 是否开启记录日志
        report_monitor: 是否上报埋点数据

    Returns: 流式sse响应体
    """

    async def wrapper():
        # 请求开始时间戳
        start_time = time.time()
        # 首包响应时间戳
        first_time = 0

        try:
            async for response in generator_func(request):
                if first_time == 0:
                    first_time = time.time()
                yield ServerSentEvent(**{"data": response})

        except Exception as e:
            print(str(e))
            traceback.print_exc()
        finally:
            process_time = time.time() - start_time
            print(f"sse request end duration: {process_time * 1000:.4f} ms")

    return wrapper


async def base_req_wrapper(
        generator_func: Callable[[BaseRequest], BaseResponse],
        request: BaseRequest,
        access_log: bool = True,
        report_monitor: bool = True
) -> BaseResponse:
    """
    基础的非流式请求响应包装方法
    Args:
        generator_func: 被调用的方法
        request: 请求参数
        access_log: 是否记录日志
        report_monitor: 是否上报监控

    Returns: 非流式标准响应体
    """
    start_time = time.time()
    try:
        return await generator_func(request)
    except Exception as e:
        print(str(e))
        traceback.print_exc()
    finally:
        process_time = time.time() - start_time
        print(f"base request end duration: {process_time:.4f}")
