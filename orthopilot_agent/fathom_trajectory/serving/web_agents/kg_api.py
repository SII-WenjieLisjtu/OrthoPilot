from __future__ import annotations
import asyncio
from typing import Dict, List
import json
import requests
# Execute a tool


'''
from kg_api import kg_search, kg_get_relations, kg_fuzzy_search, medibook_search, semanticscholar_search

def search_kg(query, domain=None, top_k=5, _search=_search_urls):
 if domain:
 q = (str(domain) + " " + str(query)).strip()
 else:
 q = query
 return _search(query=q, top_k=top_k)
'''

def check_entity_exit(entity, limit_per_relation=1):
    response = requests.post(
    "http://localhost:8000",
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
    payload = json.loads(result["data"])  # result['data'] yes JSON
    relation_names = list((payload.get("relation_stats") or {}).keys())

    # relation_names, True; no False
    final_result = bool(relation_names)

    return final_result


# def kg_search():
def kg_search(entity, relation=None, limit=5):

    if relation:
        try:
            response = requests.post(
                "http://localhost:8000",
                json={
                    "tool_name": "cpubmed.search",
                    "parameters": {
                        "entity": str(entity),
                        "relation": str(relation),
                        "limit": int(limit),
                    },
                },
            )
            result = response.json()
            final_result = json.loads(result["data"])["summary"]
            return str(final_result)
        except Exception as e:
            # yes or no
            try:
                entity_exists = check_entity_exit(entity)
            except Exception as ce:
                #, does not exist,
                print(f"check_entity_exit: {ce}")
                entity_exists = False

            if entity_exists:
                #, relation does not exist
                relations_info = kg_get_relations(entity)
                final_result = (
                    f"'{entity}', '{relation}'.\n"
                    f" kg_get_relations,: \n"
                    f"{relations_info}"
                )
                return str(final_result)
            else:
                # does not exist,
                print(f"{entity}does not exist, ")
                fuzzy_result = kg_fuzzy_search(entity)
                final_result = (
                    f"'{entity}'. kg_fuzzy_search, "
                    f"Fuzzy search result:\n{fuzzy_result}"
                )
                return str(final_result)

    else:
        try:
            response = requests.post(
                "http://localhost:8000",
                json={
                    "tool_name": "cpubmed.search",
                    "parameters": {
                        "entity": str(entity),
                        "limit": int(limit),
                    },
                },
            )
            result = response.json()
            final_result = json.loads(result["data"])["summary"]
            return str(final_result)
        except Exception as e:
            #,
            print(f"{entity}does not exist, ")
            fuzzy_result = kg_fuzzy_search(entity)
            final_result = (
                f"'{entity}'."
                f"Please call kg_fuzzy_search first. Fuzzy search result:\n{fuzzy_result}"
            )
            return str(final_result)


# def kg_get_relations():
def kg_get_relations(entity, limit_per_relation=1):
    # check_entity_exit judgement as yes or no
    try:
        entity_exists = check_entity_exit(entity, limit_per_relation=limit_per_relation)
    except Exception as e:
        #, does not exist,
        print(f"check_entity_exit: {e}")
        entity_exists = False

    if not entity_exists:
        # does not exist,
        print(f"{entity}does not exist, ")
        fuzzy_result = kg_fuzzy_search(entity)
        final_result = (
            f"'{entity}'."
            f"Please call kg_fuzzy_search first. Fuzzy search result:\n{fuzzy_result}"
        )
        return str(final_result)

    #,
    response = requests.post(
        "http://localhost:8000",
        json={
            "tool_name": "cpubmed.get_relations",
            "parameters": {
                "entity": str(entity),
                "limit_per_relation": limit_per_relation,
            },
        },
    )

    result = response.json()
    payload = json.loads(result["data"])  # result['data'] yes JSON
    relation_names = list((payload.get("relation_stats") or {}).keys())

    # relation_names (judgement), yes
    if not relation_names:
        return f"'{entity}',."

    final_result = f"'{entity}'({len(relation_names)}): {', '.join(relation_names)}"
    return final_result


# kg_fuzzy_search:
def kg_fuzzy_search(keyword, threshold=0.6, limit=5):
    """
:
 - keyword: (,, error)
 - threshold: 0-1,
 - limit:
 """
    response = requests.post(
        "http://localhost:8000",
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
    payload = json.loads(response["data"])  # result['data'] yes JSON
    keyword = payload.get("keyword", "")
    threshold = payload.get("threshold", None)
    matches = payload.get("matches") or []

    #
    matches = sorted(matches, key=lambda x: x.get("similarity", 0.0), reverse=True)[:limit]

    if not matches:
        th = f"{threshold:.2f}" if isinstance(threshold, (int, float)) else str(threshold)
        return f"'{keyword}'>={th}."

    lines = []
    header_th = f"{threshold:.2f}" if isinstance(threshold, (int, float)) else str(threshold)
    lines.append(f"Search result for '{keyword}', threshold {header_th}, top {len(matches)}:")

    for i, m in enumerate(matches, 1):
        ent = (m.get("entity") or "").strip()
        sim = m.get("similarity", 0.0)
        typ = (m.get("type") or "").strip()

        note = ""
        if typ in {"unknown", "other"}:
            note = " (low-specificity type)"

        lines.append(f"{i}. {ent} | {sim:.3f} | {typ}{note}")

    # lines.append("choice,.")
    return "\n".join(lines)


# medibook_search: /
def medibook_search(query, search_mode="embedding"):
    """
:
 - query: content(//)
 - search_mode:, default 'embedding'
 """
    response = requests.post(
        "http://localhost:8000",
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
        return f"medibook.search: {result.get('error')}"

    final_result = result.get("data", "")
    return str(final_result)



# semanticscholar_search: Semantic Scholar ("content": TLDR/)
def semanticscholar_search(query, limit=10, max_abs_chars=500, max_authors=3):
    """
 - query:
 - limit:
 -: LLM(TLDR/Abstract + URL + PDF)
 """
    resp = requests.post(
        "http://localhost:8000",
        json={
            "tool_name": "semanticscholar.search",
            "parameters": {
                "query": str(query),
                "limit": int(limit),
                # tool fields,; ()
                "fields": "title,year,authors,url,abstract,tldr,openAccessPdf"
            }
        },
        timeout=60
    )
    result = resp.json()
    if not result.get("success"):
        return f"Semantic Scholar: {result.get('error') or 'unknown error'}"

    data = result.get("data", "")
    obj = json.loads(data) if isinstance(data, str) else data

    papers = (obj.get("papers") or [])[: int(limit)]
    total = obj.get("total_results", None)

    lines = []
    head = f"Semantic Scholar: {query}; {len(papers)} " + (f" / {total} " if total is not None else "")
    lines.append(head)

    def _authors_str(auths):
        if not auths:
            return ""
        if len(auths) <= max_authors:
            return ", ".join(auths)
        return ", ".join(auths[:max_authors]) + " "

    for i, p in enumerate(papers, 1):
        title = (p.get("title") or "").strip() or "()"
        year = p.get("year")
        url = (p.get("url") or "").strip()

        authors = p.get("authors") or []
        a_str = _authors_str(authors)

        # tldr yes dict str
        tldr = p.get("tldr")
        if isinstance(tldr, dict):
            tldr = tldr.get("text") or ""
        tldr = (tldr or "").strip()

        abstract = (p.get("abstract") or "").strip()
        if abstract and len(abstract) > max_abs_chars:
            abstract = abstract[:max_abs_chars].rstrip() + "..."

        oap = p.get("openAccessPdf") or {}
        pdf_url = (oap.get("url") or "").strip()

        block = [f"[S{i}] {title}({year if year else ''})- {a_str}"]
        if tldr:
            block.append(f": {tldr}")
        if abstract:
            block.append(f": {abstract}")
        if url:
            block.append(f": {url}")
        if pdf_url:
            block.append(f"openPDF: {pdf_url}")

        lines.append("\n".join(block))

    return "\n\n".join(lines)


if __name__ == "__main__":
    # breakpoint()
    # ceshi = check_entity_exit(entity='')
    # print(ceshi)
    # print('==='*10)
    ceshi = kg_search("","")
    print(ceshi)
    print('==='*10)
    # ceshi = kg_fuzzy_search(keyword='')
    # print(ceshi)
    # print('==='*10)
    # ceshi = medibook_search(query='')
    # print(ceshi)
    # print('==='*10)
    # ceshi = semanticscholar_search(query='')
    # print(ceshi)
    # print('==='*10)