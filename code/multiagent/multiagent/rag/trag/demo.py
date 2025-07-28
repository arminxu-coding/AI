from typing import List

import httpx
import requests
from trag import Namespace, TRAG

base_url = "https://api.trag.woa.com"


def get_graph_list():
    params = {
        "ragCode": "is-53619f29",
        "namespaceCode": "ns-e111c03f"
    }
    headers = {
        "accept": "*/*",
        "Authorization": "Bearer b39592ad-0134-481b-8e56-956694dbc06f"
    }
    url = base_url + "/v1/trag/graph/list"
    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers, )

    print("Status Code:", response.status_code)
    print("Response Body:", response.text)


def create_graph():
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json",
        "Authorization": "Bearer b39592ad-0134-481b-8e56-956694dbc06f"
    }

    data = {
        "ragCode": "is-53619f29",
        "namespaceCode": "ns-e111c03f",
        "name": "test",
        "description": "测试graphrag"
    }

    # 同步请求
    with httpx.Client() as client:
        response = client.post(base_url + "/v1/trag/graph/save", headers=headers, json=data)

    print("Status Code:", response.status_code)
    print("Response Body:", response.text)


trag_token = "b39592ad-0134-481b-8e56-956694dbc06f"
rag_client = TRAG.from_api_key(api_key=trag_token)


def init_test_graph(ns: Namespace):
    # 在本namespace下创建 grapg
    graph = ns.create_graph("test1", "测试graphrag,默认的测试检索文章", dimension=1024, embedding_model="bge-large-zh")
    # 创建索引
    index_test1 = graph.create_graph_index("index_test1")
    # 倒入知识库内容，并生成图
    index_test1.import_files("/Users/xuchen/work_space/AI/projects/multiagent/multiagent/rag/input/book.txt",
                             policy="public-graphrag-policy", wait_for_finish=True)


def search_test_graph(ns: Namespace, query: str):
    graph = ns.graph("gra-9be3f97c")
    graph_index = graph.graph_index("index_test1")
    entity_documents = graph_index.list_entity_documents()
    print(entity_documents)
    resp = graph_index.search_graph(query)
    print(resp)


if __name__ == '__main__':
    # get_graph_list()
    # create_graph()

    # 获取当前示例的所有 namespace
    ns_list = rag_client.list_namespaces()
    ns = ns_list[0]

    search_test_graph(ns, "你好")
