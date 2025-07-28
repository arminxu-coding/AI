import requests


def get(url, params=None, headers=None, timeout=5) -> dict:
    """
    发送 GET 请求
    :param url: 完整的请求 URL
    :param params: 请求参数
    :param headers: 请求头
    :param timeout: 请求超时时间
    :return: 响应对象，如果请求失败则返回 None
    """
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        else:
            print(f"get request to {url} 执行失败，状态码: {response.status_code}，响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"GET request to {url} failed: {e}")
        return None


def post(url, json=None, headers=None, timeout=5) -> dict | None:
    """
    发送 POST 请求
    :param url: 完整的请求 URL
    :param json: JSON 数据
    :param headers: 请求头
    :param timeout: 请求超时时间
    :return: 响应对象，如果请求失败则返回 None
    """
    try:
        response = requests.post(url, json=json, headers=headers, timeout=timeout)
        response.raise_for_status()
        if response.status_code == 200:
            response_body = response.json()
            print(f"post request to {url} 执行成功，响应内容: {response.json()}")
            return response_body
        else:
            print(f"post request to {url} 执行失败，状态码: {response.status_code}，响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"POST request to {url} failed: {e}")
        return None


def put(url, data=None, json=None, headers=None, timeout=5):
    """
    发送 PUT 请求
    :param url: 完整的请求 URL
    :param data: 表单数据
    :param json: JSON 数据
    :param headers: 请求头
    :param timeout: 请求超时时间
    :return: 响应对象，如果请求失败则返回 None
    """
    try:
        response = requests.put(url, data=data, json=json, headers=headers, timeout=timeout)
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        else:
            print(f"put request to {url} 执行失败，状态码: {response.status_code}，响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"PUT request to {url} failed: {e}")
        return None


def delete(url, headers=None, timeout=5):
    """
    发送 DELETE 请求
    :param url: 完整的请求 URL
    :param headers: 请求头
    :param timeout: 请求超时时间
    :return: 响应对象，如果请求失败则返回 None
    """
    try:
        response = requests.delete(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        else:
            print(f"delete request to {url} 执行失败，状态码: {response.status_code}，响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"DELETE request to {url} failed: {e}")
        return None


if __name__ == '__main__':
    # 定义基础的请求数据
    base_data = {
        "unique_id": "test1",
        "channel_id": "009000",
        "preference": {
            "product": "爱喝柠檬茶",
            "sugar_level": "喜欢甜的"
        },
        "query": "给我点个热的小杯拿铁"
    }
    print(get(url="http://127.0.0.1:8090/heart"))
    headers = {
        'Content-Type': 'application/json'
    }
    print(post(url="http://127.0.0.1:8090/v1/api/voice", headers=headers, json=base_data, timeout=1000))
