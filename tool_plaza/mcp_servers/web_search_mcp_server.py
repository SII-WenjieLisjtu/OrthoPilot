# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from orthopilot_agent.miroflow_core.logging.logger import setup_mcp_logging

SANDBOX_URL = os.environ.get("FATHOM_SANDBOX_URL", "http://localhost:8904")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("web-search-mcp-server")

# fathom search_api
_SEARCH_ENV = """
from search_api import web_search, search_urls, open_url, search_and_parse_query, query_url
"""


async def _call_sandbox(env: str, call: str, timeout: int = 120) -> str:
    """Call fathom sandbox /execute endpoint."""
    url = f"{SANDBOX_URL}/execute"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"env": env, "call": call, "timeout": timeout},
                timeout=aiohttp.ClientTimeout(total=timeout + 30),
            ) as resp:
                if resp.status != 200:
                    return f"[ERROR]: Sandbox returned status {resp.status}: {await resp.text()}"
                data = await resp.json()
                if data.get("error"):
                    return f"[ERROR]: {data['error']}"
                result = data.get("result", "")
                return str(result) if result else "[ERROR]: Empty result"
    except aiohttp.ClientError as e:
        return f"[ERROR]: Failed to connect to search sandbox: {str(e)}"
    except Exception as e:
        return f"[ERROR]: Unexpected error: {str(e)}"


@mcp.tool()
async def google_search(query: str, top_k: int = 10) -> str:
    """Google.result, URL.
, resultAPI.

 Args:
 query:
 top_k: result, default10

 Returns:
 result(Markdown)
 """
    call = f'search_urls(query={json.dumps(query, ensure_ascii=False)}, top_k={top_k})'
    return await _call_sandbox(_SEARCH_ENV, call)


@mcp.tool()
async def fetch_webpage(url: str) -> str:
    """specified content.resultURL.

 Args:
 url: URL

 Returns:
 content
 """
    call = f'open_url(url={json.dumps(url)}, compress=False)'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=60)


@mcp.tool()
async def search_and_extract(query: str, top_k: int = 3) -> str:
    """.Google,,
 content..

 Args:
 query:
 top_k:, default3

 Returns:
 result
 """
    call = f'search_and_parse_query(query={json.dumps(query, ensure_ascii=False)}, top_k={top_k})'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=180)


@mcp.tool()
async def query_webpage(url: str, goal: str) -> str:
    """.LLM content,
.

 Args:
 url: URL
 goal:

 Returns:

 """
    call = f'query_url(url={json.dumps(url)}, goal={json.dumps(goal, ensure_ascii=False)})'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=120)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
