# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from orthopilot_agent.miroflow_core.logging.logger import setup_mcp_logging

HOSPITAL_SIMILAR_URL = os.environ.get("HOSPITAL_SIMILAR_URL", "http://localhost:8000")
PMC_PATIENTS_URL = os.environ.get("PMC_PATIENTS_URL", "http://localhost:8000")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("similar-case-mcp-server")


@mcp.tool()
async def similar_case_search(patient_id: str, top_k: int = 10) -> str:
    """.patient,,
,.

 Args:
 patient_id: patientID, "patient_xxx"
 top_k: maximum number of results, default 10

 Returns:
 result
 """
    url = f"{HOSPITAL_SIMILAR_URL}/tools/similar_case_search"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"patient_id": patient_id, "top_k": top_k},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: Similar case service returned status {resp.status}: {await resp.text()}"
                data = await resp.json()
                return data.get("text", json.dumps(data, ensure_ascii=False))
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to similar case service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


@mcp.tool()
async def pmc_similar_case_search(
    text: str, top_k: int = 10, task: str = "PPR", max_chars: int = 600
) -> str:
    """Search PMC-Patients for similar patient cases.
,.

 task:
 - PPR: Patient-to-Patient Retrieval(patientpatient)
 - PAR: Patient-to-Article Retrieval(patient)
 - RARE_RDS:
 - RARE_RDC:

 Args:
: patient(,)
 top_k: maximum number of results, default 10
 task: retrieval task, default "PPR"
 max_chars: maximum characters per result, default 600

 Returns:
 PMC results
 """
    url = f"{PMC_PATIENTS_URL}/retrieve"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "task": task, "question": text,
                    "top_k": top_k, "return_text": True, "max_chars": max_chars,
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: PMC-Patients service returned status {resp.status}: {await resp.text()}"
                results = await resp.json()
                if not results:
                    return "No PMC-Patients results found."
                parts = []
                for i, r in enumerate(results, 1):
                    score = r.get("score", "N/A")
                    doc_id = r.get("doc_id", "unknown")
                    txt = r.get("text", "")
                    parts.append(f"[{i}] (similarity: {score}, ID: {doc_id})\n{txt}")
                return "\n\n".join(parts)
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to PMC-Patients service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
