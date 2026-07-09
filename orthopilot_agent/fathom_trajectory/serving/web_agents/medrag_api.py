import json
import requests
from typing import Any, Dict, Optional,Union


MEDRAG_ENDPOINT = "http://localhost:8000"


def _post_medrag(payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    """
 MedRAG FastAPI /tool, JSON dict
 """
    r = requests.post(MEDRAG_ENDPOINT, json=payload, timeout=timeout)
    if not r.ok:
        # FastAPI erroryes {"detail": "..."}
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
 " execute":
 - tool_name: "wikipedia" / "pubmed" / "books" / "statpearls"
 - question:
 """
    payload = {
        "tool_name": tool_name,         #: yes tool_name(wikipedia/pubmed/...)
        "question": str(question),
        "k": int(k),
        "cite": bool(cite),
        "include_scores": bool(include_scores),
        "translate_output": bool(translate_output),
    }
    return _post_medrag(payload, timeout=timeout)


# -------- 4 ""(agent) --------


def wikipedia_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("wikipedia", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("con") or "")


def pubmed_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("pubmed", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("con") or "")


def textbooks_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("books", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("con") or "")


def statpearls_search(
    question: str,
    k: int = 5,
    return_meta: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    out = execute_tool("statpearls", question=question, k=k, **kwargs)
    return out if return_meta else (out.get("con") or "")

# --------: check_entity_exit yes-or-no judgement --------

def check_search_hit(tool_name: str, question: str, k: int = 3) -> bool:
    """
 snippet (check_entity_exit)
 """
    out = execute_tool(tool_name, question=question, k=k, cite=False, include_scores=False, translate_output=True)
    snippets = out.get("snippets") or []
    return len(snippets) > 0


# -------- smoke test --------

if __name__ == "__main__":
    question = "What is osteoarthritis?"
    tools = ["wikipedia", "pubmed", "books", "statpearls"]

    for t in tools:
        out = statpearls_search(question)

        # print("\n" + "=" * 80)
        # print(f"TOOL = {t}")
        # print("question_in:", out.get("question_in"))
        # print("question_used_for_retrieval:", out.get("question_used_for_retrieval"))
        # print("translated:", out.get("translated"))
        # print("timings_ms:", out.get("timings_ms"))

        # con
        print("\n--- con ---")
        print(out)

        # # top titles(sanity check)
        # print("\n--- top titles ---")
        # for i, s in enumerate((out.get("snippets") or [])[:5]):
        # title = s.get("title", "")
        # print(f"[{i}] {title}")
