from typing import Optional, Any

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    code: int = Field(default=0, description="响应码")
    message: str = Field(default='success', description="响应提示消息")
    data: Optional[Any] = Field(default=None, description="基础返回数据类型")
    trace_id: Optional[str] = Field(default=None, description="trace_id")
