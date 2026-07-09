#!/usr/bin/env python3
"""
trajectory_enhancer_r1.py - Build Search-R1 style trajectory JSONL records from synthetic patient examples.

This public template accepts either --input-file or --input-dir. Input records should contain
sanitized basic_info and admission_record fields. The script builds a Search-R1 prompt with
<think>, <search>, <information> and <answer> tags, runs a local model endpoint, and writes
JSONL samples containing the question, optional reference answer, prompt and generated trajectory.

Example:
    python3 trajectory_enhancer_r1.py \
        --input-dir data/examples/T1 \
        --output-jsonl outputs/search_r1.jsonl \
        --model-url http://localhost:8000 \
        --executors http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import sys

# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
sys.path.insert(0,  "agents/inference")

from re_call_medical import ReCallMedical  # type: ignore
from medical_trajectory_generator import MEDICAL_SCHEMAS  # type: ignore

try:
    from transformers import AutoTokenizer  # type: ignore
except Exception:
    AutoTokenizer = None

import debugpy
try:
    # 5678 is the default attach port in the VS Code debug configurations. Unless a host and port are specified, host defaults to 127.0.0.1
    debugpy.listen(("localhost", 8906))
    print("Waiting for debugger attach")
    debugpy.wait_for_client()
except Exception as e:
    pass

# ------------------------------ -----------------------------------

def _is_nan(x: Any) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def _sanitize(obj: Any) -> Any:
    """ NaN/None is empty, dict/list."""
    if _is_nan(obj) or obj is None:
        return ""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def load_patient(filepath: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    basic_info = _sanitize(data.get("basic_info", {}))
    admission_list = _sanitize(data.get("admission_record", data.get("admission", [])))
    admission = admission_list[0] if isinstance(admission_list, list) and admission_list else {}
    return basic_info, admission


def patient_summary_text(basic_info: Dict[str, Any], admission: Dict[str, Any], *, admission_only: bool = False) -> str:
    """Build a compact patient summary from non-empty public example fields."""
    hidden_keys = {
        "admission_diagnosis",
        "admission_diagnosis_code",
        "patient_id",
        "empi",
        "EMPI",
    }

    def lines_from(record: Dict[str, Any]) -> List[str]:
        return [f"{k}: {v}" for k, v in record.items() if k not in hidden_keys and v]

    ad_text = "\n".join(lines_from(admission)).strip()
    if admission_only:
        return ("[Admission record]\n" + ad_text) if ad_text else ""

    bi_text = "\n".join(lines_from(basic_info)).strip()
    pieces = []
    if bi_text:
        pieces.append("[Basic information]\n" + bi_text)
    if ad_text:
        pieces.append("[Admission record]\n" + ad_text)
    return "\n\n".join(pieces)


CHINESE_R1_SYSTEM = (
    "You are a clinician using a Search-R1 trajectory format.\n"
    "- Think briefly inside <think>...</think>.\n"
    "- If external support is needed, emit a search query inside <search>...</search>.\n"
    "- Treat retrieved content inside <information>...</information> as supporting evidence.\n"
    "- Finish with the final clinical response inside <answer>...</answer>.\n"
)

def build_search_r1_prompt(short_question: str, info_text: str) -> List[Dict[str, str]]:
    """Build a Search-R1 prompt with system and user messages."""
    user_content = f"{short_question}\n\n{info_text}" if info_text else short_question
    return [
        {"role": "system", "content": CHINESE_R1_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def build_env_for_patient(patient_payload: Dict[str, Any]) -> str:
    """ + patient,."""
    def python_literal(d: Dict[str, Any]) -> str:
        return repr(d)
    # "",,.
    env = f"""
from search_api import search_urls as _search_urls, query_url as _query_url
from kg_api import kg_search, kg_get_relations, kg_fuzzy_search, medibook_search, semanticscholar_search
from medrag_api import wikipedia_search, pubmed_search, books_search, statpearls_search

def search_guidelines(query, domain=None, top_k=5, _search=_search_urls):
 if domain:
 q = (str(domain) + " " + str(query)).strip()
 else:
 q = query
 return _search(query=q, top_k=top_k)

def search_differential_diagnosis(symptoms=None, age=None, specialty=None, top_k=5, _search=_search_urls):
 keywords = []
 if symptoms:
 keywords.extend(symptoms if isinstance(symptoms, (list, tuple)) else [symptoms])
 if age:
 keywords.append(str(age))
 if specialty:
 keywords.append(str(specialty))
 q = " ".join(filter(None, keywords)) or " "
 return _search(query=q, top_k=top_k)
"""
    return env.strip()


def sanitize_gpt_content(content: str, banned_terms: Optional[List[str]] = None) -> str:
    """Remove search-budget hints and mask reference terms outside final answers."""
    if not content:
        return content

    patterns = [
        r"\bsearch(?:es)?\s*(?:left|remaining)\b",
        r"\bmax(?:imum)?\s*search(?:es)?\b",
        r"\blimit(?:ed)?\s+to\s+\d+\s+search(?:es)?\b",
        r"\b(?:MRI|CT|X[-\s]?ray|radiograph|imaging|lab(?:oratory)? results?)\b",
        r"\bget_(?:imaging|lab_results)\b",
    ]
    cleaned = content
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # (<answer>)
    if banned_terms:
        tokens = re.split(r"(<answer>.*?</answer>)", cleaned, flags=re.DOTALL)

        def mask_text(text: str) -> str:
            out = text
            for term in banned_terms:
                if not term:
                    continue
                out = re.sub(re.escape(term), "", out)
                spaced = r"".join([re.escape(ch) + r"\s*" for ch in term])
                out = re.sub(spaced, "", out, flags=re.IGNORECASE)
            return out

        cleaned = "".join(seg if i % 2 == 1 else mask_text(seg) for i, seg in enumerate(tokens))

    return cleaned


def ensure_final_answer(trajectory: List[Dict[str, str]], golden: str) -> List[Dict[str, str]]:
    """<answer>(golden).<answer>, gold answer."""
    replaced = False
    for step in reversed(trajectory):
        if step.get("role") == "gpt" and "<answer>" in step.get("content", ""):
            content = step.get("content", "")
            # <think>, <answer>
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            think_text = think_match.group(1).strip() if think_match else ",."
            step["content"] = f"<think>{sanitize_gpt_content(think_text)}</think><answer>{golden}</answer>"
            replaced = True
            break
    if not replaced:
        final = f"<think>,.</think><answer>{golden}</answer>"
        trajectory.append({"role": "gpt", "content": final})
    return trajectory


TOOL_CALL_RE = re.compile(r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL)
TOOL_RESP_RE = re.compile(r"<tool_response>(.*?)</tool_response>", re.DOTALL)


def _tool_call_to_search_tag(tool_call_json_str: str) -> str:
    try:
        data = json.loads(tool_call_json_str)
        name = (data.get("name") or "").strip()
        args = data.get("arguments", {}) or {}
        query = ""
        if name in ("search_guidelines", "search_web"):
            query = str(args.get("query", "")).strip()
        elif name == "search_differential_diagnosis":
            # symptoms/age/specialty
            parts = []
            sym = args.get("symptoms")
            if sym:
                parts.extend(sym if isinstance(sym, list) else [sym])
            if args.get("age"):
                parts.append(str(args.get("age")))
            if args.get("specialty"):
                parts.append(str(args.get("specialty")))
            query = " ".join([p for p in parts if p])
        else:
            return ""  # output
        return f"<search> {query} </search>" if query else ""
    except Exception:
        return ""


def transform_gpt_to_search_r1(content: str) -> str:
    """ GPT content <tool_call> <search>, <think>/<answer>."""
    if not content:
        return content
    def repl(m):
        return _tool_call_to_search_tag(m.group(1))
    converted = TOOL_CALL_RE.sub(repl, content)
    return converted


def transform_user_to_information(content: str, banned_terms: Optional[List[str]] = None) -> str:
    """ tool_response <information>... </information>."""
    if not content:
        return content
    infos: List[str] = []
    for m in TOOL_RESP_RE.finditer(content):
        inner = m.group(1)
        # {"tool":...,"data":...}
        data_str = inner
        try:
            j = json.loads(inner)
            if isinstance(j, dict) and "data" in j:
                data_str = j["data"]
                if isinstance(data_str, (dict, list)):
                    data_str = json.dumps(data_str, ensure_ascii=False)
        except Exception:
            pass
        if banned_terms:
            for term in banned_terms:
                if term:
                    data_str = re.sub(re.escape(term), "", data_str)
        infos.append(f"<information>\n{data_str}\n</information>")
    return "\n".join(infos) if infos else ""


def to_search_r1_trajectory(raw: List[Dict[str, str]], short_question: str, info_text: str, banned_terms: Optional[List[str]] = None) -> List[Dict[str, str]]:
    new_traj: List[Dict[str, str]] = []
    # 1) system + user
    new_traj.append({"role": "system", "content": CHINESE_R1_SYSTEM})
    first_user = f"{short_question}\n\n{info_text}" if info_text else short_question
    new_traj.append({"role": "user", "content": first_user})

    # 2), assistant<tool_call><search>, usertext<tool_response><information>
    for step in raw:
        r = step.get("role")
        c = step.get("content", "")
        if r == "gpt":
            c2 = sanitize_gpt_content(transform_gpt_to_search_r1(c), banned_terms=banned_terms)
            new_traj.append({"role": "gpt", "content": c2})
        elif r == "user":
            info = transform_user_to_information(c, banned_terms=banned_terms)
            if info:
                new_traj.append({"role": "user", "content": info})
        # skip system
    #: <answer>assistant, all
    cut_idx = None
    for i, st in enumerate(new_traj):
        if st.get("role") == "gpt" and "<answer>" in st.get("content", ""):
            cut_idx = i
            break
    if cut_idx is not None:
        new_traj = new_traj[: cut_idx + 1]
    return new_traj


def run_agent(question: str, env: str, schemas: List[Dict[str, Any]], args, tokenizer, *, distill_with_gt: bool = False, golden: str = "") -> List[Dict[str, str]]:
    teacher_hint = None
    if distill_with_gt and golden:
        teacher_hint = (
            ": " + str(golden) + ".\n"
            "; <think>/<search>/<information>.<answer>."
        )
    agent = ReCallMedical(
        executor_url=args.executors,
        max_searches=args.max_searches,
        sys_prompt=None,
        teacher_hint=teacher_hint,
        suppress_logs=True,
    )
    _, _tool_calls, traj = agent.run(
        env=env,
        func_schemas=json.dumps(schemas, ensure_ascii=False, indent=2),
        question=question,
        model_url=args.model_url,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        tokenizer=tokenizer,
    )
    # gpt content
    for step in traj:
        if step.get("role") == "gpt":
            step["content"] = sanitize_gpt_content(
                step.get("content", ""),
                banned_terms=[golden] if distill_with_gt and golden else None,
            )
    return traj


def load_tokenizer(name: Optional[str]):
    if not name:
        return lambda x, **_: {"input_ids": list(range(len(x.split()))) }
    if AutoTokenizer is None:
        print("[warn] transformers, statistics.")
        return lambda x, **_: {"input_ids": list(range(len(x.split()))) }
    print(f"[tokenizer] load {name}")
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True)


def build_question(basic_info: Dict[str, Any], admission: Dict[str, Any], *, admission_only: bool) -> str:
    info_text = patient_summary_text(basic_info, admission, admission_only=admission_only)
    prefix = (
        "Review the admission record and answer the clinical question. "
        if admission_only else
        "Review the patient summary and admission record, then answer the clinical question. "
    )
    return (
        f"{prefix}"
        "what is the patient admission diagnosis?\n\n"
        f"{info_text}"
    )


def process_one_file(filepath: Path, args, out_f):
    basic_info, admission = load_patient(filepath)
    golden = str(basic_info.get("admission_diagnosis", "")).strip()

    # Build the ground-truth question prompt.
    admission_only = not getattr(args, "include_basic_info", False)
    question = build_question(basic_info, admission, admission_only=admission_only)
    short_question = "Does the patient need additional search support?"
    info_text = patient_summary_text(basic_info, admission, admission_only=admission_only)
    prompt_array = build_search_r1_prompt(short_question, info_text)

    # Optional environment payload for patient context.
    # payload = {
    #     "basic_info": {k: v for k, v in basic_info.items() if k not in ("admission_diagnosis", "admission_diagnosis_code")},
    #     "admission": admission,
    # }
    # env = build_env_for_patient(payload)
    env = build_env_for_patient({})

    # tokenizer
    tokenizer = load_tokenizer(args.tokenizer)
    # TODO: prompt
    # agent generate, schema
    # ALLOWED = {"get_patient", "search_guidelines", "search_differential_diagnosis", "search_web", "visit_url"}
    # R1_SCHEMAS = [s for s in MEDICAL_SCHEMAS if s.get("name") in ALLOWED]
    R1_SCHEMAS = MEDICAL_SCHEMAS
    raw_traj = run_agent(
        question=question,
        env=env,
        schemas=R1_SCHEMAS,
        args=args,
        tokenizer=tokenizer,
        distill_with_gt=args.distill_with_gt,
        golden=golden,
    )

    # answer; /GT
    trajectory = ensure_final_answer(raw_traj, golden)
    # Search-R1, user
    trajectory = to_search_r1_trajectory(
        trajectory,
        short_question,
        info_text,
        banned_terms=[golden] if args.distill_with_gt and golden else None,
    )

    record = {
        "question": question,
        "golden_answers": golden,
        "prompt": prompt_array,
        "trajectory": trajectory,
        "source_file": str(filepath),
    }
    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")


def iter_input_files(args) -> List[Path]:
    files: List[Path] = []
    if args.input_file:
        p = Path(args.input_file)
        if p.is_file() and p.suffix.lower() == ".json":
            files.append(p)
    if args.input_dir:
        d = Path(args.input_dir)
        if d.is_dir():
            for fp in sorted(d.glob("*.json")):
                files.append(fp)
    if not files:
        raise FileNotFoundError("Provide a JSON file with --input-file or a directory with --input-dir.")
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    return files


def main():
    parser = argparse.ArgumentParser(description="Build Search-R1 trajectory JSONL records")
    parser.add_argument("--input-file", help="Patient JSON file path")
    parser.add_argument("--input-dir", help="Directory containing patient JSON files")
    parser.add_argument("--output-jsonl", required=True, help="Output JSONL path")
    parser.add_argument("--model-url", required=True, help="Local model endpoint URL")
    parser.add_argument("--executors", required=True, help="Executor service URL")
    parser.add_argument("--tokenizer", default=None, help="Optional Hugging Face tokenizer name or path")
    parser.add_argument("--temperature", type=float, default=0.2, help="Generation temperature")
    parser.add_argument("--max-new-tokens", type=int, default=30000, help="Maximum generated tokens")
    parser.add_argument("--max-searches", type=int, default=8, help="Maximum search tool calls")
    parser.add_argument("--distill-with-gt", action="store_true", help="Use the reference answer as a teacher hint during trajectory generation")
    parser.add_argument("--include-basic-info", action="store_true", help="Include basic patient fields in the prompt")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of files to process; 0 processes all files")
    args = parser.parse_args()

    files = iter_input_files(args)
    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out_f:
        for fp in files:
            print(f"[build] {fp}")
            try:
                process_one_file(fp, args, out_f)
                out_f.flush()
            except Exception as e:
                print(f"[warn] {fp} -> {e}")

    print(f"\nGenerated trajectory file: {out_path}")


if __name__ == "__main__":
    main()
