import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# 导入新的工具函数
from .tool_utils import (
    parse_tool_call,
    parse_function_call_arguments,
    convert_parameter_types,
    extract_message_content,
    build_tool_schemas,
    format_tool_response,
)


def extract_json_from_tag(raw_string: str, tag: str) -> Optional[str]:
    """
    使用正则表达式从 <tag>...</tag> 中提取内容
    """
    match = re.search(f'<{tag}>(.*?)</{tag}>', raw_string)
    if match:
        return match.group(1)
    return None


__all__ = [
    "extract_json_from_tag",
    "parse_tool_call",
    "parse_function_call_arguments",
    "convert_parameter_types",
    "extract_message_content",
    "build_tool_schemas",
    "format_tool_response",
]


