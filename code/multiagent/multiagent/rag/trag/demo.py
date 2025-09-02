import httpx
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


def init_test_graph(ns: Namespace, graph_name: str, index_name: str, file_path: str, graph_desc: str = "测试graphrag"):
    # 在本namespace下创建 grapg
    graph = ns.create_graph(graph_name, graph_desc, dimension=1024, embedding_model="bge-large-zh")
    # 创建索引
    index = graph.create_graph_index(index_name)
    # 导入知识库内容，并生成图
    index.import_files(
        file_path,
        policy="public-graphrag-policy",
        wait_for_finish=True,
        graphrag_api_key="WfJNVTigLSCPnonLKSxPmwnn@303"
    )


def search_test_graph(ns: Namespace, graph_code: str, index_name: str, query: str):
    graph = ns.graph(graph_code)
    graph_index = graph.graph_index(index_name)
    entity_documents = graph_index.list_entity_documents()
    print(entity_documents)
    resp = graph_index.search_graph(query)
    return resp


if __name__ == '__main__':
    # get_graph_list()
    # create_graph()

    # 获取当前示例的所有 namespace
    ns_list = rag_client.list_namespaces()
    ns = ns_list[0]

    init_test_graph(
        ns,
        "test_1",
        "index_test_1",
        "/Users/xuchen/work_space/AI/code/multiagent/multiagent/rag/graphrag/input/book.txt"

        # "test_mcd_excel",
        # "index_test_mcd_excel",
        # "/Users/xuchen/work_space/AI/code/multiagent/multiagent/rag/trag/麦当劳-全量商品.xlsx"
        # "麦当劳-全量商品.xlsx"
    )

    # resp = search_test_graph(ns, "gra-4b324a2f", "index_test_mcd_excel", "汉堡")
    # print(resp)
