# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from orthopilot_agent.miroflow_core.logging.logger import setup_mcp_logging

MEDRAG_BASE_URL = os.environ.get("MEDRAG_BASE_URL", "http://localhost:8000")

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
                context = data.get("con", "")
                if context:
                    return context
                return json.dumps(data, ensure_ascii=False)
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to MedRAG service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


@mcp.tool()
async def pubmed_search(question: str, k: int = 5) -> str:
    """PubMed.
,, result.

 Args:
 question:
 k:, default5

 Returns:
 PubMedresult()
 """
    return await _call_medrag("pubmed", question, k)


@mcp.tool()
async def textbooks_search(question: str, k: int = 5) -> str:
    """content.,
.

 Args:
 question:
 k: result, default5

 Returns:
 result
 """
    return await _call_medrag("books", question, k)


@mcp.tool()
async def statpearls_search(question: str, k: int = 5) -> str:
    """StatPearls.StatPearlsyes,
,,.

 Args:
 question:
 k: result, default5

 Returns:
 StatPearlsresult
 """
    return await _call_medrag("statpearls", question, k)


@mcp.tool()
async def wikipedia_medical_search(question: str, k: int = 5) -> str:
    """Wikipedia..

 Args:
 question:
 k: result, default5

 Returns:
 Wikipediaresult
 """
    return await _call_medrag("wikipedia", question, k)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
