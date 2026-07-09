import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Parsed tool-call payload emitted by an agent."""

    name: str = Field(..., description="Tool name")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResponse(BaseModel):
    """Structured response returned by a tool execution."""

    tool: str = Field(..., description="Tool name")
    args: Dict[str, Any] = Field(..., description="Tool arguments")
    data: Any = Field(..., description="Tool result payload")
