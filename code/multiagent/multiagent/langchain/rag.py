"""
langchain 实现本地rag，需要开墙拉去 embedding—model
"""
import os
from langchain.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import DirectoryLoader


def initialize_embeddings(model_name="all-MiniLM-L6-v2"):
    """初始化本地嵌入模型"""
    # 使用HuggingFace的嵌入模型，会自动下载并本地运行
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return embeddings


def create_vector_db(documents, embeddings, db_path="./faiss_index"):
    """创建向量数据库"""
    # 分割文档
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    # 创建向量存储
    db = FAISS.from_documents(texts, embeddings)

    # 保存数据库到本地
    db.save_local(db_path)
    print(f"向量数据库已保存到 {db_path}")
    return db


def load_vector_db(embeddings, db_path="./faiss_index"):
    """从本地加载向量数据库"""
    if os.path.exists(db_path):
        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)  # 添加安全参数
        print(f"已从 {db_path} 加载向量数据库")
        return db
    else:
        print(f"未找到向量数据库 {db_path}")
        return None


def search_documents(db, query, top_k=3):
    """检索相关文档"""
    if not db:
        print("向量数据库未初始化")
        return []

    # 相似度搜索
    docs = db.similarity_search_with_score(query, k=top_k)

    # 返回结果
    return docs


def main():
    # 初始化嵌入模型 - 这会下载模型（首次运行）并在本地运行
    print("初始化嵌入模型...")
    embeddings = initialize_embeddings()

    # 尝试加载已存在的向量数据库
    db = load_vector_db(embeddings)

    # 如果数据库不存在，则创建
    if not db:
        print("创建新的向量数据库...")
        # 加载文档 - 这里可以替换为你的文档路径
        # 示例：加载当前目录下的所有txt文件
        loader = DirectoryLoader('./', glob="**/*.txt", loader_cls=TextLoader)
        documents = loader.load()

        # 如果没有找到文档，使用示例文档
        if not documents:
            print("未找到文档，使用示例数据创建数据库")
            sample_docs = [
                "Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。",
                "LangChain是一个用于构建基于语言模型的应用程序的框架。",
                "FAISS是Facebook AI Research开发的高效相似度搜索库。",
                "SentenceTransformers是一个用于生成文本嵌入的Python库。",
                "向量数据库用于存储和检索高维向量数据，常用于AI应用。"
            ]
            # 将示例文本转换为Document对象
            from langchain_community.docstore.document import Document  # 更新Document导入
            documents = [Document(page_content=doc) for doc in sample_docs]

        # 创建向量数据库
        db = create_vector_db(documents, embeddings)

    # 测试检索
    while True:
        query = input("\n请输入查询（输入'q'退出）: ")
        if query.lower() == 'q':
            break

        results = search_documents(db, query)

        print(f"\n与'{query}'相关的结果：")
        for i, result in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"内容: {result}")


if __name__ == "__main__":
    main()
