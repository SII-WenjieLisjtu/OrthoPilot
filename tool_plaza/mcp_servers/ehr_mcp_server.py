# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from orthopilot_agent.miroflow_core.logging.logger import setup_mcp_logging

EHR_BASE_URL = os.environ.get("EHR_BASE_URL", "http://localhost:8000")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("ehr-mcp-server")


async def _call_ehr(endpoint: str, payload: dict) -> str:
    """Call EHR FastAPI backend and return result."""
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
    """patient result(X-ray, CT, MRI).

 Args:
 patient_id: patientID, "patient_xxx"
 stage:, "preop"() "postop"()
 group_index:, default0
 max_items:, default50
 max_chars:, default8000

 Returns:
 result
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
    """patient result(,,).

 Args:
 patient_id: patientID, "patient_xxx"
 stage:, "preop"() "postop"()
 group_index:, default0
 max_items:, default50
 max_chars:, default8000

 Returns:
 result
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
    """patient result.

 Args:
 patient_id: patientID, "patient_xxx"
 stage:, "preop"() "postop"()
 group_index:, default0
 max_items:, default50
 max_chars:, default8000

 Returns:
 result
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
    """patient.

 Args:
 patient_id: patientID, "patient_xxx"
 stage:, "preop"() "postop"()
 group_index:, default0
 max_items:, default50
 max_chars:, default8000

 Returns:

 """
    return await _call_ehr("query_consult_notes", {
        "patient_id": patient_id, "stage": stage,
        "group_index": group_index, "max_items": max_items, "max_chars": max_chars,
    })


@mcp.tool()
async def get_admission_basic(patient_id: str, max_chars: int = 8000) -> str:
    """patient(,,,).

 Args:
 patient_id: patientID, "patient_xxx"
 max_chars:, default8000

 Returns:

 """
    return await _call_ehr("get_admission_basic", {
        "patient_id": patient_id, "max_chars": max_chars,
    })


@mcp.tool()
async def get_admission_note(patient_id: str, max_chars: int = 8000) -> str:
    """patient(,,,).

 Args:
 patient_id: patientID, "patient_xxx"
 max_chars:, default8000

 Returns:

 """
    return await _call_ehr("get_admission_note", {
        "patient_id": patient_id, "max_chars": max_chars,
    })


@mcp.tool()
async def get_surgery_record(
    patient_id: str, max_items: int = 20, max_chars: int = 8000
) -> str:
    """patient.

 Args:
 patient_id: patientID, "patient_xxx"
 max_items:, default20
 max_chars:, default8000

 Returns:

 """
    return await _call_ehr("get_surgery_record", {
        "patient_id": patient_id, "max_items": max_items, "max_chars": max_chars,
    })


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
