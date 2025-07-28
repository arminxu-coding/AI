from typing import Optional

from pydantic import BaseModel, Field


class BaseRequest(BaseModel):
    """
    基础的请求类
    """
    channel_id: str = Field(default=None, description="渠道号")
    user_id: str = Field(default=None, description="user_id")
    wecar_id: Optional[str] = Field(default=None, description="wecar_id")
    device_id: Optional[str] = Field(default=None, description="device_id")
    session_id: Optional[str] = Field(default=None, description="session_id")
    trace_id: Optional[str] = Field(default=None, description="trace_id")
