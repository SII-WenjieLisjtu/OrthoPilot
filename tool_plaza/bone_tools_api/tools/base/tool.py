from abc import ABC, abstractmethod
from typing import Any, Dict, List
from .parameter import ToolParameter
from .response import ToolResponse


class Tool(ABC):
    """工具基类，需实现run和get_parameters方法"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具，返回结果字符串"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """返回工具参数定义列表"""
        pass

    def to_openai_schema(self) -> dict[str, Any]:
        """构建OpenAI function calling schema"""
        parameters = self.get_parameters()

        properties = {}
        required = []

        for param in parameters:
            properties[param.name] = param.to_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }

    def execute(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具并返回标准响应"""
        try:
            result = self.run(parameters)
            return ToolResponse(
                tool=self.name,
                args=parameters,
                data=result,
                success=True
            )
        except Exception as e:
            return ToolResponse(
                tool=self.name,
                args=parameters,
                error=str(e),
                success=False
            )

    def get_openai_function_schema(self) -> dict[str, Any]:
        """兼容方法，返回function部分"""
        return self.to_openai_schema()["function"]
