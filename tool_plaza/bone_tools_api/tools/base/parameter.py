from typing import Any, Optional, List
from dataclasses import dataclass


@dataclass
class ToolParameter:
    """工具参数定义

    type支持: string, number, integer, boolean, array, object
    """

    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    items: Optional[dict] = None
    properties: Optional[dict] = None

    def to_schema(self) -> dict[str, Any]:
        """转换为OpenAI function calling schema"""
        schema = {
            "type": self.type,
            "description": self.description,
        }

        if self.enum is not None:
            schema["enum"] = self.enum

        if self.default is not None:
            schema["default"] = self.default

        if self.type == "array" and self.items is not None:
            schema["items"] = self.items

        if self.type == "object" and self.properties is not None:
            schema["properties"] = self.properties

        return schema
