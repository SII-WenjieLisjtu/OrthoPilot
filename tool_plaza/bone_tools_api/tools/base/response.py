from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class ToolResponse:
    """"""

    tool: str
    args: dict[str, Any]
    data: Optional[Any] = None
    error: Optional[str] = None
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "tool": self.tool,
            "args": self.args,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
            result["success"] = False
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_xml_string(self) -> str:
        """XMLmodel"""
        import json
        return f"<tool_response>{json.dumps(self.to_dict(), ensure_ascii=False)}</tool_response>"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolResponse":
        return cls(
            tool=data.get("tool", ""),
            args=data.get("args", {}),
            data=data.get("data"),
            error=data.get("error"),
            success=data.get("success", True),
            metadata=data.get("metadata", {})
        )
