# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
import aiohttp
from fastmcp import FastMCP
from src.logging.logger import setup_mcp_logging

KG_BASE_URL = os.environ.get("KG_BASE_URL", "http://YOUR_HOST:YOUR_PORT")

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
    """在CPubMed医学知识图谱中查询实体的关系信息。支持50+种医学关系类型，
    包括疾病-药物、疾病-症状、药物-副作用等。

    常用关系类型示例：
    - drug_treatment（药物治疗）、clinical_manifestation（临床表现）
    - pathogenesis（发病机制）、diagnosis（诊断）
    - prognosis（预后）、complication（并发症）

    Args:
        entity: 医学实体名称，如 "骨折"、"骨质疏松"
        relation: 关系类型，留空则返回该实体的所有关系。可用 kg_get_relations 查看实体支持的关系
        limit: 最大返回结果数，默认20

    Returns:
        知识图谱查询结果
    """
    params = {"entity": entity, "limit": limit}
    if relation:
        return await _call_kg(f"cpubmed.query_{relation}", params)
    return await _call_kg("cpubmed.search", params)


@mcp.tool()
async def kg_get_relations(entity: str) -> str:
    """获取指定医学实体在知识图谱中的所有可用关系类型。
    用于了解某个实体有哪些关系可以查询。

    Args:
        entity: 医学实体名称

    Returns:
        该实体支持的所有关系类型列表
    """
    return await _call_kg("cpubmed.get_relations", {"entity": entity})


@mcp.tool()
async def kg_fuzzy_search(keyword: str, threshold: float = 0.6, limit: int = 10) -> str:
    """在知识图谱中模糊搜索医学实体。当不确定实体的精确名称时使用。

    Args:
        keyword: 搜索关键词
        threshold: 相似度阈值（0-1），默认0.6
        limit: 最大返回结果数，默认10

    Returns:
        匹配的实体列表及相似度分数
    """
    return await _call_kg("cpubmed.fuzzy_search", {
        "keyword": keyword, "threshold": threshold, "limit": limit,
    })


@mcp.tool()
async def medibook_search(query: str) -> str:
    """在医学书籍数据库中检索相关内容。覆盖骨科、外科等医学教材。

    Args:
        query: 检索查询，如 "股骨颈骨折的治疗方案"

    Returns:
        医学书籍检索结果
    """
    return await _call_kg("medibook.search", {"query": query})


@mcp.tool()
async def semanticscholar_search(query: str, limit: int = 10) -> str:
    """在Semantic Scholar学术数据库中检索医学文献。获取最新的学术研究论文。

    Args:
        query: 检索查询
        limit: 最大返回文献数，默认10

    Returns:
        学术文献检索结果
    """
    return await _call_kg("semanticscholar.search", {"query": query, "limit": limit})


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
