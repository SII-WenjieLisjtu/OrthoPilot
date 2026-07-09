from __future__ import annotations
import asyncio
from typing import Dict, List
import json
import requests
# Execute a tool


'''
from kg_api import kg_search, kg_get_relations, kg_get_entity_type, kg_fuzzy_search, medibook_search, semanticscholar_search

def search_kg(query, domain=None, top_k=5, _search=_search_urls):
    if domain:
        q = (str(domain) + " " + str(query)).strip()
    else:
        q = query
    return _search(query=q, top_k=top_k)
'''

# def kg_search():
def kg_search(entity, relation=None, limit=5):
    if relation:
        response = requests.post(
        "http://YOUR_HOST:YOUR_PORT",
        json={
            "tool_name": "cpubmed.search",
            "parameters": {
                "entity": str(entity),
                "relation": str(relation),
                "limit": limit
            }
        }
        )
    else:
        response = requests.post(
        "http://YOUR_HOST:YOUR_PORT",
        json={
            "tool_name": "cpubmed.search",
            "parameters": {
                "entity": str(entity),
                # "relation": str(relation),
                "limit": 5
            }
        }
        )
    result = response.json()
    # breakpoint()
    final_result = json.loads(result['data'])['summary']
    return str(final_result)

# def kg_get_relations():
def kg_get_relations(entity, limit_per_relation=1):
    response = requests.post(
    "http://YOUR_HOST:YOUR_PORT",
    json={
        "tool_name": "cpubmed.get_relations",
        "parameters": {
            "entity": str(entity),
            "limit_per_relation": limit_per_relation
        }
    }
    )
    result = response.json()
    # breakpoint()
    # print(result)
    payload = json.loads(result["data"])  # result['data'] 是 JSON 字符串
    relation_names = list((payload.get("relation_stats") or {}).keys())

    final_result = f"实体'{entity}'可用关系类型（{len(relation_names)}类）：{'、'.join(relation_names)}"
    return final_result

# # def kg_search():
# def kg_get_entity_type(entity):
#     response = requests.post(
#     "http://YOUR_HOST:YOUR_PORT",
#     json={
#         "tool_name": "cpubmed.get_entity_type",
#         "parameters": {
#             "entity": str(entity),
#         }
#     }
#     )
#     result = response.json()
#     # print(result)
#     # breakpoint()
#     # final_result = json.loads(result['data'])['summary']
#     return str(result)

# kg_fuzzy_search：在医学知识图谱中执行模糊搜索
def kg_fuzzy_search(keyword, threshold=0.6, limit=5):
    """
    在医学知识图谱中执行模糊搜索：
    - keyword: 用于检索的关键词（支持不完整、口语化、轻微拼写错误）
    - threshold: 相似度阈值 0-1，越高越严格
    - limit: 最多返回的候选实体数量
    """
    response = requests.post(
        "http://YOUR_HOST:YOUR_PORT",
        json={
            "tool_name": "cpubmed.fuzzy_search",
            "parameters": {
                "keyword": str(keyword),
                "threshold": float(threshold),
                "limit": int(limit),
            }
        }
    )
    response=response.json()
    payload = json.loads(response["data"])  # result['data'] 是 JSON 字符串
    keyword = payload.get("keyword", "")
    threshold = payload.get("threshold", None)
    matches = payload.get("matches") or []

    # 排序并截断
    matches = sorted(matches, key=lambda x: x.get("similarity", 0.0), reverse=True)[:limit]

    if not matches:
        th = f"{threshold:.2f}" if isinstance(threshold, (int, float)) else str(threshold)
        return f"未找到与「{keyword}」相似度≥{th}的候选实体。"

    lines = []
    header_th = f"{threshold:.2f}" if isinstance(threshold, (int, float)) else str(threshold)
    lines.append(f"模糊搜索结果：关键词「{keyword}」，阈值 {header_th}，返回Top {len(matches)}候选：")

    for i, m in enumerate(matches, 1):
        ent = (m.get("entity") or "").strip()
        sim = m.get("similarity", 0.0)
        typ = (m.get("type") or "未知").strip()

        note = ""
        if typ in {"未知", "社会学"}:
            note = "（类型可能不可靠）"

        lines.append(f"{i}. {ent} ｜相似度 {sim:.3f} ｜类型 {typ}{note}")

    # lines.append("请从上述候选中选择最符合语境的实体名称，用于后续查询。")
    return "\n".join(lines)


# medibook_search：在本地/预先索引的医学书籍知识库中搜索
def medibook_search(query, search_mode="embedding"):
    """
    在本地或预先索引好的医学书籍与教材知识库中进行语义检索：
    - query: 检索请求内容（问题/描述/关键术语）
    - search_mode: 检索模式，默认 'embedding'
    """
    response = requests.post(
        "http://YOUR_HOST:YOUR_PORT",
        json={
            "tool_name": "medibook.search",
            "parameters": {
                "search_mode": str(search_mode),
                "query": str(query),
            }
        }
    )
    result = response.json()
    
    if not result.get("success", False):
        return f"medibook.search 调用失败：{result.get('error')}"

    final_result = result.get("data", "")
    return str(final_result)



# semanticscholar_search：基于 Semantic Scholar 的在线学术文献检索（返回“内容型”信息：TLDR/摘要）
def semanticscholar_search(query, limit=10, max_abs_chars=500, max_authors=3):
    """
    - query: 检索查询
    - limit: 返回数量
    - 返回：给LLM直接读的文本（包含 TLDR/Abstract + 溯源URL + 可用PDF链接）
    """
    resp = requests.post(
        "http://YOUR_HOST:YOUR_PORT",
        json={
            "tool_name": "semanticscholar.search",
            "parameters": {
                "query": str(query),
                "limit": int(limit),
                # 如果你的 tool 端支持 fields，就加上；不支持也不影响（会忽略）
                "fields": "title,year,authors,url,abstract,tldr,openAccessPdf"
            }
        },
        timeout=60
    )
    result = resp.json()
    if not result.get("success"):
        return f"Semantic Scholar 检索失败：{result.get('error') or 'unknown error'}"

    data = result.get("data", "")
    obj = json.loads(data) if isinstance(data, str) else data

    papers = (obj.get("papers") or [])[: int(limit)]
    total = obj.get("total_results", None)

    lines = []
    head = f"Semantic Scholar 检索：{query}；返回 {len(papers)} 条" + (f" / 共 {total} 条" if total is not None else "")
    lines.append(head)

    def _authors_str(auths):
        if not auths:
            return "作者未知"
        if len(auths) <= max_authors:
            return "、".join(auths)
        return "、".join(auths[:max_authors]) + " 等"

    for i, p in enumerate(papers, 1):
        title = (p.get("title") or "").strip() or "（无标题）"
        year = p.get("year")
        url = (p.get("url") or "").strip()

        authors = p.get("authors") or []
        a_str = _authors_str(authors)

        # tldr 可能是 dict 或 str
        tldr = p.get("tldr")
        if isinstance(tldr, dict):
            tldr = tldr.get("text") or ""
        tldr = (tldr or "").strip()

        abstract = (p.get("abstract") or "").strip()
        if abstract and len(abstract) > max_abs_chars:
            abstract = abstract[:max_abs_chars].rstrip() + "…"

        oap = p.get("openAccessPdf") or {}
        pdf_url = (oap.get("url") or "").strip()

        block = [f"[S{i}] {title}（{year if year else '未知年份'}）— {a_str}"]
        if tldr:
            block.append(f"要点：{tldr}")
        if abstract:
            block.append(f"摘要：{abstract}")
        if url:
            block.append(f"链接：{url}")
        if pdf_url:
            block.append(f"开放获取PDF：{pdf_url}")

        lines.append("\n".join(block))

    return "\n\n".join(lines)



if __name__ == "__main__":
    # breakpoint()
    # ceshi = kg_get_relations(entity='糖尿病')
    # print(ceshi)
    # print('==='*10)
    # ceshi = kg_search("髋关节退行性变")
    # print(ceshi)
    # print('==='*10)
    # ceshi = kg_fuzzy_search(keyword='髋关节退行性变')
    # print(ceshi)
    # print('==='*10)
    # ceshi = medibook_search(query='傻瓜病')
    # print(ceshi)
    # print('==='*10)
    ceshi = semanticscholar_search(query='髋关节退行性变')
    print(ceshi)
    print('==='*10)