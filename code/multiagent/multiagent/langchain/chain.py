from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

load_dotenv("../../.env")

model = init_chat_model(model="deepseek-chat", model_provider="deepseek")

# 最基础的使用方法
# chain = model | StrOutputParser()
# result = chain.invoke("你好")
# print(result)

# 使用上提示词模版
# prompt_template = ChatPromptTemplate([
#     {"role": "system", "content": "you are a helpful assistant"},
#     {"role": "user", "content": "这是用户的问题： {question}，请进行回答:"}
# ])
# chain = prompt_template | model | StrOutputParser()
# result = chain.invoke({"question": "1+1是多少"})
# print(result)

# 加上自定义结果解析器
# schemas = [
#     ResponseSchema(name="name", description="姓名", type="string"),
#     ResponseSchema(name="age", description="年龄", type="int"),
# ]
# parser = StructuredOutputParser.from_response_schemas(schemas)
# prompt_template = PromptTemplate.from_template("""\
# 根据下面的内容提取用户的信息:
# {content}
# 以 JSON 格式返回:
# {output_format}\
# """)
# print(parser.get_format_instructions())
# chain = prompt_template.partial(output_format=parser.get_format_instructions()) | model | parser
# result = chain.invoke({"content": "我叫张三来自于江西，2002年11月8号出生的"})
# print(result)


