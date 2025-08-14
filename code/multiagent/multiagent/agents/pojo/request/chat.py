from pydantic import Field

from multiagent.agents.pojo.request.base import BaseRequest


class ChatRequest(BaseRequest):
    query: str = Field(default=None, description="query")
