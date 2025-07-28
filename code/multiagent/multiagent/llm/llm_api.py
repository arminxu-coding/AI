import json
import uuid
import requests
import sseclient
from openai import OpenAI
from typing import Dict, List, AsyncGenerator

from multiagent.utils.common_util import ObjectUtil

model_providers = {
    "hunyuan-openapi": {
        "url": "http://hunyuanapi.woa.com/openapi/v1/chat/completions",
        "api_key": "Bearer Doc51WblCovlzJB5t5mgDH8Os29MubWA",
        "call_method": "http"
    },
    "hunyuan": {
        "url": "http://stream-server-online-openapi.turbotke.production.polaris:8080/openapi/chat/completions",
        "api_key": "26785bfe-68a4-438a-9875-2f8bf2f49110",
        "call_method": "http",
        "headers": {
            "Wsid": "10697",
            "Accept": "application/json"
        }
    },
    "siliconflow": {
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "api_key": "Bearer sk-oauyqdudcpitlpwsdhlwtxlhvbktnbcrkqvredwhqfkweugw",
        "call_method": "http"
    },
    "deepseek": {
        "url": "https://api.deepseek.com",
        "api_key": "sk-114cb5d9b3364649bd7ab553c3c06ea1",
        "call_method": "openai"
    },
    "alibaba": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-d5fac075883e4238b834003678d1faf1",
        "call_method": "openai"
    },
    "ollama": {
        "url": "http://localhost:11434/v1",
        "api_key": "empty token",
        "call_method": "openai"
    }
}

openai_llm_mapping: Dict[str, OpenAI] = {}


async def generate_content_async(
        messages: List[dict],
        model: str,
        enable_thinking: bool = False,
        temperature: float = 0,
        stream: bool = False
) -> AsyncGenerator[str, None]:
    """ 流式调用llm """

    provider, model_name = model.split("_", 1)

    config = model_providers[provider]
    call_method = config['call_method']
    url = config.get('url')
    api_key = config.get('api_key')

    if call_method == 'openai':
        if model_name not in openai_llm_mapping:
            llm = OpenAI(base_url=url, api_key=api_key)
            openai_llm_mapping[model_name] = llm
        else:
            llm = openai_llm_mapping[model_name]
        response = llm.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=stream
        )
        if stream:
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        else:
            yield response.choices[0].message.content


    elif call_method == 'http':
        data = {
            "model": model_name,
            "query_id": str(uuid.uuid4()),
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "enable_thinking": enable_thinking
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": api_key
        }

        headers = _model_request_header_adapter(provider, headers)
        response = requests.post(url, headers=headers, json=data, stream=stream)
        if response.status_code != 200:
            print(
                f"llm_api request error model: {model}, code: {response.status_code}, text: {response.text}, reason: {response.reason}")
            return
        if not stream:
            yield _model_response_to_content(provider, response.json())
        else:
            client = sseclient.SSEClient(response)
            for event in client.events():
                if event and event.data != '':
                    if event.data == '[DONE]':
                        return
                    data_dict = json.loads(event.data)
                    content = _model_stream_response_to_content(provider, data_dict)
                    if content:
                        yield content


def _model_request_header_adapter(provider: str, headers: dict):
    """
    不同模型厂商适配不同的请求头
    :param provider: 模型厂商
    :param headers: 基础请求头
    :return: 适配过户的请求头，会新增一些参数，例如 hunyuan 就会新增 Wsid
    """
    config = model_providers[provider]
    if ObjectUtil.is_empty(headers):
        headers = config.get("headers", {})
    else:
        headers.update(config.get("headers", {}))
    return headers


def _model_response_to_content(provider: str, response: dict) -> str | None:
    return response['choices'][0]['message'].get('content')


def _model_stream_response_to_content(provider: str, response: dict) -> str | None:
    if "finish_reason" in response['choices'][0] and response['choices'][0]['finish_reason'] == 'stop':
        return None
    return response['choices'][0]['delta'].get('content')
