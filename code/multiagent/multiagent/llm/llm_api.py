import json
import uuid
from typing import Dict, List, AsyncGenerator

import requests
import sseclient
from openai import OpenAI

from multiagent.utils.common_util import ObjectUtil

with open("example.txt", "r", encoding="utf-8") as file:
    model_providers = json.loads(file.read())

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
