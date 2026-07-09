import json
import re
from typing import Any, Dict, List, Optional


def parse_tool_call(tool_call_str: str) -> Dict[str, Any]:
    """<tool_call>{...}</tool_call>JSON"""
    match = re.search(r'<tool_call>(.*?)</tool_call>', tool_call_str, re.DOTALL)
    if not match:
        raise ValueError(" <tool_call> ")

    json_str = match.group(1).strip()
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON: {e}")


def parse_function_call_arguments(args_str: str) -> Dict[str, Any]:
    """function-call JSON"""
    if not args_str:
        return {}

    try:
        return json.loads(args_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"function call: {e}")


def convert_parameter_types(parameters: Dict[str, Any],
                            param_definitions: List[Any]) -> Dict[str, Any]:
    """"""
    converted = {}
    param_def_map = {p.name: p for p in param_definitions}

    for key, value in parameters.items():
        if key not in param_def_map:
            converted[key] = value
            continue

        param_def = param_def_map[key]
        param_type = param_def.type

        if param_type == "string" and isinstance(value, str):
            converted[key] = value
        elif param_type == "integer" and isinstance(value, int):
            converted[key] = value
        elif param_type == "number" and isinstance(value, (int, float)):
            converted[key] = value
        elif param_type == "boolean" and isinstance(value, bool):
            converted[key] = value
        elif param_type == "array" and isinstance(value, list):
            converted[key] = value
        elif param_type == "object" and isinstance(value, dict):
            converted[key] = value
        elif isinstance(value, str):
            try:
                if param_type == "integer":
                    converted[key] = int(value)
                elif param_type == "number":
                    converted[key] = float(value)
                elif param_type == "boolean":
                    converted[key] = value.lower() in ("true", "1", "yes")
                elif param_type in ("array", "object"):
                    converted[key] = json.loads(value)
                else:
                    converted[key] = value
            except (ValueError, json.JSONDecodeError):
                converted[key] = value
        else:
            converted[key] = value

    return converted


def extract_message_content(response: Any) -> str:
    """OpenAIcontent"""
    if hasattr(response, 'choices') and len(response.choices) > 0:
        choice = response.choices[0]
        if hasattr(choice, 'message'):
            message = choice.message
            if hasattr(message, 'content') and message.content:
                return message.content
    return ""


def build_tool_schemas(tools: List[Any]) -> List[Dict[str, Any]]:
    """OpenAI function calling schemas"""
    return [tool.to_openai_schema() for tool in tools]


def format_tool_response(response: Any) -> str:
    """XML"""
    if hasattr(response, 'to_xml_string'):
        return response.to_xml_string()
    elif isinstance(response, dict):
        return f"<tool_response>{json.dumps(response, ensure_ascii=False)}</tool_response>"
    else:
        return f"<tool_response>{json.dumps({'data': str(response)}, ensure_ascii=False)}</tool_response>"
