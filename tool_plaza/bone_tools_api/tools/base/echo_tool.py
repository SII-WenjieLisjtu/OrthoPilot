from typing import Any, Dict, List
from .tool import Tool
from .parameter import ToolParameter


class EchoTool(Tool):
    """Echo工具示例"""

    def __init__(self):
        super().__init__(
            name="echo",
            description="回显工具，返回输入的消息内容"
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="message",
                type="string",
                description="要回显的消息内容",
                required=True
            ),
            ToolParameter(
                name="repeat",
                type="integer",
                description="重复次数，默认为1",
                required=False,
                default=1
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        message = parameters.get("message", "")
        repeat = parameters.get("repeat", 1)

        try:
            repeat = int(repeat)
            if repeat < 1:
                repeat = 1
        except (ValueError, TypeError):
            repeat = 1

        if repeat == 1:
            return message
        else:
            return " ".join([message] * repeat)
