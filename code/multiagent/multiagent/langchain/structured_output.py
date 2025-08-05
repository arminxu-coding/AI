"""
langchain 实现结构化化输出
"""
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

load_dotenv("../../.env")

tagging_prompt = ChatPromptTemplate.from_template(
    """
Extract the desired information from the following passage.

Only extract the properties mentioned in the 'Classification' function.

Passage:
{input}
"""
)


# 基础的定义结构化输出，也就是像我们平时定义一个数据类一样
# class Classification(BaseModel):
#     sentiment: str = Field(description="The sentiment of the text")
#     aggressiveness: int = Field(
#         description="How aggressive the text is on a scale from 1 to 10"
#     )
#     language: str = Field(description="The language the text is written in")


# 定义更加丰富的限定，描述 + 枚举限定选值范围（更细致的控制）
class Classification(BaseModel):
    sentiment: str = Field(..., enum=["happy", "neutral", "sad"])
    aggressiveness: int = Field(
        ...,
        description="describes how aggressive the statement is, the higher the number the more aggressive",
        enum=[1, 2, 3, 4, 5],
    )
    language: str = Field(
        ..., enum=["spanish", "english", "french", "german", "italian"]
    )


# llm = ChatOpenAI(temperature=0, model="deepseek-chat").with_structured_output(Classification)
llm = init_chat_model(model="deepseek-chat", model_provider="deepseek").with_structured_output(Classification)
'''
解释一下这里的原理吧，其实 with_structured_output() 我们将我们需要结构化输出结果给到llm
最后langchain底层就会反射获取到我们的 class 转换为对应的 tool 的定义，所以我们的限制只需要满足langchain支持的tool定义格式
最后调用llm还是通过function call的调用方式最后将结果转换为我们的实例对象
具体代码如下，代码具有一定删改：
langchain_openai.chat_models.base.BaseChatOpenAI._generate
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        generation_info = None
        if "response_format" in payload:
            try:
                response = self.root_client.beta.chat.completions.parse(**payload)
            except openai.BadRequestError as e:
                _handle_openai_bad_request(e)
        elif self._use_responses_api(payload):
            original_schema_obj = kwargs.get("response_format")
            if original_schema_obj and _is_pydantic_class(original_schema_obj):
                response = self.root_client.responses.parse(**payload)
            else:
                if self.include_response_headers:
                    raw_response = self.root_client.with_raw_response.responses.create(**payload)
                    response = raw_response.parse()
                    generation_info = {"headers": dict(raw_response.headers)}
                else:
                    response = self.root_client.responses.create(**payload)
            return _construct_lc_result_from_responses_api(
                response,
                schema=original_schema_obj,
                metadata=generation_info,
                output_version=self.output_version,
            )
        elif self.include_response_headers:
            raw_response = self.client.with_raw_response.create(**payload)
            response = raw_response.parse()
            generation_info = {"headers": dict(raw_response.headers)}
        else:
            response = self.client.create(**payload)
        return self._create_chat_result(response, generation_info)
'''

tagging_chain = tagging_prompt | llm

response = tagging_chain.invoke({
    "input": "Estoy increiblemente contento de haberte conocido! Creo que seremos muy buenos amigos!"
})

print(response.model_dump_json())
