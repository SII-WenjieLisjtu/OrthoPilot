# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from src.logging.logger import setup_mcp_logging

HOSPITAL_SIMILAR_URL = os.environ.get("HOSPITAL_SIMILAR_URL", "http://YOUR_HOST:YOUR_PORT")
PMC_PATIENTS_URL = os.environ.get("PMC_PATIENTS_URL", "http://YOUR_HOST:YOUR_PORT")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("similar-case-mcp-server")


@mcp.tool()
async def similar_case_search(patient_id: str, top_k: int = 10) -> str:
    """检索院内相似病例。根据患者的诊断编码、诊断名称和病历文本，
    在院内病例库中检索最相似的历史病例，用于辅助临床决策。

    Args:
        patient_id: 患者ID，格式如 "patient_xxx"
        top_k: 返回最相似病例数量，默认10

    Returns:
        相似病例检索结果文本
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
    """检索PMC外部相似病例。基于患者描述文本，在PMC-Patients数据库中
    检索相似的已发表病例报告，获取国际文献中的类似病例参考。

    支持的检索任务类型：
    - PPR: Patient-to-Patient Retrieval（患者到患者检索）
    - PAR: Patient-to-Article Retrieval（患者到文献检索）
    - RARE_RDS: 罕见病症状检索
    - RARE_RDC: 罕见病病例检索

    Args:
        text: 患者病情描述文本（中文或英文均可，系统自动翻译）
        top_k: 返回最相似病例数量，默认10
        task: 检索任务类型，默认"PPR"
        max_chars: 每条结果最大字符数，默认600

    Returns:
        PMC相似病例检索结果
    """
    url = f"{PMC_PATIENTS_URL}/retrieve"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "task": task, "text": text,
                    "top_k": top_k, "return_text": True, "max_chars": max_chars,
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: PMC-Patients service returned status {resp.status}: {await resp.text()}"
                results = await resp.json()
                if not results:
                    return "未找到相似的PMC病例。"
                parts = []
                for i, r in enumerate(results, 1):
                    score = r.get("score", "N/A")
                    doc_id = r.get("doc_id", "unknown")
                    txt = r.get("text", "")
                    parts.append(f"[{i}] (相似度: {score}, ID: {doc_id})\n{txt}")
                return "\n\n".join(parts)
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to PMC-Patients service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
