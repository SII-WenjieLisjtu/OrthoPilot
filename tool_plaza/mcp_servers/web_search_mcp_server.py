# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from src.logging.logger import setup_mcp_logging

SANDBOX_URL = os.environ.get("FATHOM_SANDBOX_URL", "http://YOUR_HOST:YOUR_PORT")

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("web-search-mcp-server")

# fathom 沙盒的 search_api 工具导入代码
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
    """通过Google搜索引擎检索信息。返回搜索结果的标题、URL和摘要。
    支持中英文查询，结果带缓存以节省API调用。

    Args:
        query: 搜索查询关键词
        top_k: 返回结果数量，默认10

    Returns:
        搜索结果列表（Markdown格式）
    """
    call = f'search_urls(query={json.dumps(query, ensure_ascii=False)}, top_k={top_k})'
    return await _call_sandbox(_SEARCH_ENV, call)


@mcp.tool()
async def fetch_webpage(url: str) -> str:
    """抓取并返回指定网页的完整内容。用于获取搜索结果中某个URL的详细信息。

    Args:
        url: 要抓取的网页URL

    Returns:
        网页内容文本
    """
    call = f'open_url(url={json.dumps(url)}, compress=False)'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=60)


@mcp.tool()
async def search_and_extract(query: str, top_k: int = 3) -> str:
    """搜索并自动提取关键信息。先执行Google搜索，然后自动访问排名靠前的网页，
    提取并压缩关键内容。适合需要深入了解某个话题时使用。

    Args:
        query: 搜索查询
        top_k: 访问并提取的网页数量，默认3

    Returns:
        搜索结果及提取的关键信息
    """
    call = f'search_and_parse_query(query={json.dumps(query, ensure_ascii=False)}, top_k={top_k})'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=180)


@mcp.tool()
async def query_webpage(url: str, goal: str) -> str:
    """带目标地访问网页并提取特定信息。使用LLM智能抽取网页中与目标相关的内容，
    比直接抓取网页更精准高效。

    Args:
        url: 目标网页URL
        goal: 你想从这个网页中获取什么信息

    Returns:
        从网页中提取的与目标相关的信息
    """
    call = f'query_url(url={json.dumps(url)}, goal={json.dumps(goal, ensure_ascii=False)})'
    return await _call_sandbox(_SEARCH_ENV, call, timeout=120)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
