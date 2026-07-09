# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from src.logging.logger import setup_mcp_logging

EHR_BASE_URL = os.environ.get("EHR_BASE_URL", "http://YOUR_HOST:YOUR_PORT")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("ehr-mcp-server")


async def _call_ehr(endpoint: str, payload: dict) -> str:
    """Call EHR FastAPI backend and return text result."""
    url = f"{EHR_BASE_URL}/tools/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return f"[ERROR]: EHR service returned status {resp.status}: {await resp.text()}"
                data = await resp.json()
                return data.get("text", json.dumps(data, ensure_ascii=False))
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to EHR service at {url}: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error calling EHR service: {str(e)}"


@mcp.tool()
async def query_imaging_results(
    patient_id: str,
    stage: str = "preop",
    group_index: int = 0,
    max_items: int = 50,
    max_chars: int = 8000,
) -> str:
    """查询患者影像检查结果（如X光、CT、MRI等）。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        stage: 阶段，"preop"（术前）或 "postop"（术后）
        group_index: 分组索引，默认0
        max_items: 最大返回条目数，默认50
        max_chars: 最大返回字符数，默认8000

    Returns:
        影像检查结果文本
    """
    return await _call_ehr("query_imaging_results", {
        "patient_id": patient_id, "stage": stage,
        "group_index": group_index, "max_items": max_items, "max_chars": max_chars,
    })


@mcp.tool()
async def query_lab_results(
    patient_id: str,
    stage: str = "preop",
    group_index: int = 0,
    max_items: int = 50,
    max_chars: int = 8000,
) -> str:
    """查询患者检验检查结果（如血常规、生化、凝血等）。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        stage: 阶段，"preop"（术前）或 "postop"（术后）
        group_index: 分组索引，默认0
        max_items: 最大返回条目数，默认50
        max_chars: 最大返回字符数，默认8000

    Returns:
        检验检查结果文本
    """
    return await _call_ehr("query_lab_results", {
        "patient_id": patient_id, "stage": stage,
        "group_index": group_index, "max_items": max_items, "max_chars": max_chars,
    })


@mcp.tool()
async def query_pathology_results(
    patient_id: str,
    stage: str = "preop",
    group_index: int = 0,
    max_items: int = 50,
    max_chars: int = 8000,
) -> str:
    """查询患者病理检查结果。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        stage: 阶段，"preop"（术前）或 "postop"（术后）
        group_index: 分组索引，默认0
        max_items: 最大返回条目数，默认50
        max_chars: 最大返回字符数，默认8000

    Returns:
        病理检查结果文本
    """
    return await _call_ehr("query_pathology_results", {
        "patient_id": patient_id, "stage": stage,
        "group_index": group_index, "max_items": max_items, "max_chars": max_chars,
    })


@mcp.tool()
async def query_consult_notes(
    patient_id: str,
    stage: str = "preop",
    group_index: int = 0,
    max_items: int = 50,
    max_chars: int = 8000,
) -> str:
    """查询患者科室会诊记录。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        stage: 阶段，"preop"（术前）或 "postop"（术后）
        group_index: 分组索引，默认0
        max_items: 最大返回条目数，默认50
        max_chars: 最大返回字符数，默认8000

    Returns:
        会诊记录文本
    """
    return await _call_ehr("query_consult_notes", {
        "patient_id": patient_id, "stage": stage,
        "group_index": group_index, "max_items": max_items, "max_chars": max_chars,
    })


@mcp.tool()
async def get_admission_basic(patient_id: str, max_chars: int = 8000) -> str:
    """获取患者入院基本信息（性别、年龄、入院时间、科室等）。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        max_chars: 最大返回字符数，默认8000

    Returns:
        入院基本信息文本
    """
    return await _call_ehr("get_admission_basic", {
        "patient_id": patient_id, "max_chars": max_chars,
    })


@mcp.tool()
async def get_admission_note(patient_id: str, max_chars: int = 8000) -> str:
    """获取患者入院记录（主诉、现病史、既往史、体格检查等完整入院记录）。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        max_chars: 最大返回字符数，默认8000

    Returns:
        入院记录文本
    """
    return await _call_ehr("get_admission_note", {
        "patient_id": patient_id, "max_chars": max_chars,
    })


@mcp.tool()
async def get_surgery_record(
    patient_id: str, max_items: int = 20, max_chars: int = 8000
) -> str:
    """获取患者手术记录。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        max_items: 最大返回手术记录数，默认20
        max_chars: 最大返回字符数，默认8000

    Returns:
        手术记录文本
    """
    return await _call_ehr("get_surgery_record", {
        "patient_id": patient_id, "max_items": max_items, "max_chars": max_chars,
    })


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
