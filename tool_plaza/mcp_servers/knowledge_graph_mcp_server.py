# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from orthopilot_agent.miroflow_core.logging.logger import setup_mcp_logging

KG_BASE_URL = os.environ.get("KG_BASE_URL", "http://localhost:8000")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("knowledge-graph-mcp-server")


async def _call_kg(tool_name: str, parameters: dict) -> str:
    """Call BoneTools knowledge graph backend."""
    url = f"{KG_BASE_URL}/tools/execute"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"tool_name": tool_name, "parameters": parameters},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: KG service returned status {resp.status}: {await resp.text()}"
                data = await resp.json()
                if not data.get("success", False):
                    return f"[ERROR]: KG tool execution failed: {data.get('error', 'unknown')}"
                result = data.get("data", "")
                if isinstance(result, (dict, list)):
                    return json.dumps(result, ensure_ascii=False, indent=2)
                return str(result)
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to KG service: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


@mcp.tool()
async def kg_search(entity: str, relation: str = "", limit: int = 20) -> str:
    """CPubMed.50+,
 -, -, -.

:
 - drug_treatment(), clinical_manifestation()
 - pathogenesis(), diagnosis()
 - prognosis(), complication()

 Args:
 entity:, "", ""
 relation:,. kg_get_relations
 limit: result, default20

 Returns:
 result
 """
    params = {"entity": entity, "limit": limit}
    if relation:
        return await _call_kg(f"cpubmed.query_{relation}", params)
    return await _call_kg("cpubmed.search", params)


@mcp.tool()
async def kg_get_relations(entity: str) -> str:
    """specified.
.

 Args:
 entity:

 Returns:

 """
    return await _call_kg("cpubmed.get_relations", {"entity": entity})


@mcp.tool()
async def kg_fuzzy_search(keyword: str, threshold: float = 0.6, limit: int = 10) -> str:
    """..

 Args:
 keyword:
 threshold: (0-1), default0.6
 limit: result, default10

 Returns:

 """
    return await _call_kg("cpubmed.fuzzy_search", {
        "keyword": keyword, "threshold": threshold, "limit": limit,
    })


@mcp.tool()
async def medibook_search(query: str) -> str:
    """content.,.

 Args:
 query:, ""

 Returns:
 result
 """
    return await _call_kg("medibook.search", {"query": query})


@mcp.tool()
async def semanticscholar_search(query: str, limit: int = 10) -> str:
    """Semantic Scholar..

 Args:
 query:
 limit:, default10

 Returns:
 result
 """
    return await _call_kg("semanticscholar.search", {"query": query, "limit": limit})


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
