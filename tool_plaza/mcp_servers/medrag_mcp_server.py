# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from src.logging.logger import setup_mcp_logging

MEDRAG_BASE_URL = os.environ.get("MEDRAG_BASE_URL", "http://YOUR_HOST:YOUR_PORT")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("medrag-mcp-server")


async def _call_medrag(tool_name: str, question: str, k: int = 5) -> str:
    """Call MedRAG retrieval backend."""
    url = f"{MEDRAG_BASE_URL}/tool"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "tool_name": tool_name,
                    "question": question,
                    "k": k,
                    "cite": True,
                    "translate_output": True,
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: MedRAG service returned status {resp.status}: {await resp.text()}"
                data = await resp.json()
                context = data.get("context", "")
                if context:
                    return context
                return json.dumps(data, ensure_ascii=False)
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to MedRAG service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


@mcp.tool()
async def pubmed_search(question: str, k: int = 5) -> str:
    """在PubMed医学文献数据库中检索相关研究论文。
    支持中英文查询，中文查询会自动翻译为英文进行检索，结果自动翻译回中文。

    Args:
        question: 医学问题或检索查询
        k: 返回文献数量，默认5

    Returns:
        PubMed文献检索结果（含引用信息）
    """
    return await _call_medrag("pubmed", question, k)


@mcp.tool()
async def textbooks_search(question: str, k: int = 5) -> str:
    """在医学教材数据库中检索相关内容。覆盖多本权威医学教材，
    适合查询基础医学知识和标准诊疗方案。

    Args:
        question: 医学问题或检索查询
        k: 返回结果数量，默认5

    Returns:
        医学教材检索结果
    """
    return await _call_medrag("textbooks", question, k)


@mcp.tool()
async def statpearls_search(question: str, k: int = 5) -> str:
    """在StatPearls临床指南数据库中检索。StatPearls是持续更新的临床医学参考资源，
    提供疾病的病因、流行病学、诊断和治疗等循证医学信息。

    Args:
        question: 医学问题或检索查询
        k: 返回结果数量，默认5

    Returns:
        StatPearls临床指南检索结果
    """
    return await _call_medrag("statpearls", question, k)


@mcp.tool()
async def wikipedia_medical_search(question: str, k: int = 5) -> str:
    """在Wikipedia医学相关条目中检索。适合获取医学概念的概述性信息和背景知识。

    Args:
        question: 医学问题或检索查询
        k: 返回结果数量，默认5

    Returns:
        Wikipedia医学检索结果
    """
    return await _call_medrag("wikipedia", question, k)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
