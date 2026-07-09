import json
import requests
from typing import Any, Dict, Optional,Union


MEDRAG_ENDPOINT = "http://YOUR_HOST:YOUR_PORT"


def _post_medrag(payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    """
    调 MedRAG FastAPI /tool，统一处理报错并返回 JSON dict
    """
    r = requests.post(MEDRAG_ENDPOINT, json=payload, timeout=timeout)
    if not r.ok:
        # FastAPI 的错误一般是 {"detail": "..."}
        try:
            detail = r.json()
        except Exception:
            detail = {"raw": r.text}
        raise RuntimeError(f"MedRAG HTTP {r.status_code}: {detail}")
    return r.json()


def execute_tool(tool_name: str, question: str, k: int = 5,
                 cite: bool = True, include_scores: bool = False,
                 translate_output: bool = True, timeout: int = 600) -> Dict[str, Any]:
    """
    模拟你现在工具系统的“统一 execute”入口：
    - tool_name: "wikipedia" / "pubmed" / "textbooks" / "statpearls"
    - question: 必填
    """
    payload = {
        "tool_name": tool_name,         # 注意：这里是服务端定义的 tool_name（wikipedia/pubmed/...）
        "question": str(question),
        "k": int(k),
        "cite": bool(cite),
        "include_scores": bool(include_scores),
        "translate_output": bool(translate_output),
    }
    return _post_medrag(payload, timeout=timeout)


# -------- 4 个“工具函数”封装（你可以直接在 agent 里注册） --------


def wikipedia_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("wikipedia", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("context") or "")


def pubmed_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("pubmed", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("context") or "")


def textbooks_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("textbooks", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("context") or "")


def statpearls_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("statpearls", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("context") or "")

# -------- 可选：类似 check_entity_exit 的 “是否命中”判断 --------

def check_search_hit(tool_name: str, question: str, k: int = 3) -> bool:
    """
    有 snippet 就算命中（类似你 check_entity_exit 逻辑）
    """
    out = execute_tool(tool_name, question=question, k=k, cite=False, include_scores=False, translate_output=True)
    snippets = out.get("snippets") or []
    return len(snippets) > 0


# -------- 环境实验：跑一遍四个工具，打印结果/耗时 --------

if __name__ == "__main__":
    question_cn = "面瘫与茎乳突孔有什么关系？"
    tools = ["wikipedia", "pubmed", "textbooks", "statpearls"]

    for t in tools:
        out = statpearls_search(question_cn)

        # print("\n" + "=" * 80)
        # print(f"TOOL = {t}")
        # print("question_in:", out.get("question_in"))
        # print("question_used_for_retrieval:", out.get("question_used_for_retrieval"))
        # print("translated:", out.get("translated"))
        # print("timings_ms:", out.get("timings_ms"))

        # 打印 context
        print("\n--- context ---")
        print(out)

        # # 打印 top titles（便于快速 sanity check）
        # print("\n--- top titles ---")
        # for i, s in enumerate((out.get("snippets") or [])[:5]):
        #     title = s.get("title", "")
        #     print(f"[{i}] {title}")
