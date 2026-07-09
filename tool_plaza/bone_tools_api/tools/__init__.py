import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    """
    用于解析 <tool_call> 标签内容的基类
    它代表一个工具调用请求。
    """
    name: str = Field(..., description="要调用的工具名称")
    args: Dict[str, Any] = Field(default_factory=dict, description="传递给工具的参数字典")

class ToolResponse(BaseModel):
    """
    用于解析 <tool_response> 标签内容的基类
    它代表一个工具的执行结果。
    """
    tool: str = Field(..., description="执行的工具名称")
    args: Dict[str, Any] = Field(..., description="执行时使用的参数")
    data: Any = Field(..., description="工具执行返回的原始数据")