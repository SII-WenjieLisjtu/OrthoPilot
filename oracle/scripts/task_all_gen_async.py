#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import random
import asyncio
import argparse
import statistics
import csv
import hashlib
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional, Set
from pathlib import Path

from tqdm import tqdm
import httpx
import pandas as pd


def _parse_llm_output(content: str, as_dict: bool = True):
    if not as_dict:
        return content, ""
    text = (content or "").strip()
    try:
        return json.loads(text), ""
    except Exception:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip()), ""
            except Exception:
                pass
        match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), ""
            except Exception:
                pass
    return {"error": "failed to parse JSON response", "raw": text}, ""


def get_llm_response(client, model: str, prompt: str, max_retries: int = 5, as_dict: bool = True):
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = resp.choices[0].message.content or ""
            return _parse_llm_output(content, as_dict=as_dict)
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(min(2 ** (attempt - 1), 30))
    raise last_err if last_err else RuntimeError("LLM request failed")


def get_llm_response_local(client, model: str, prompt: str, max_retries: int = 5, as_dict: bool = True, timeout: int = 600):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
    }
    if model:
        payload["model"] = model
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.post("chat/completions", json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"].get("content") or ""
            return _parse_llm_output(content, as_dict=as_dict)
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(min(2 ** (attempt - 1), 30))
    raise last_err if last_err else RuntimeError("Local LLM request failed")


def _safe_patient_id(patient_id: str) -> str:
    return str(patient_id or "unknown").strip().replace("/", "_").replace("\\", "_")


def get_meta_path_by_str(meta_root: str, task_id: int, patient_id: str, subpath: str) -> str:
    return os.path.join(meta_root, f"task_{task_id}", subpath, f"{_safe_patient_id(patient_id)}.json")


def save_dict(meta: dict, save_path: str) -> str:
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return save_path


def make_uid(patient_id: str, input_text: str) -> str:
    raw = f"{patient_id or ''}||{(input_text or '').strip()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_last_human(conversations: List[dict]) -> str:
    last = ""
    for msg in conversations or []:
        role = msg.get("from", msg.get("role", ""))
        if role in {"human", "user"}:
            last = msg.get("value", msg.get("content", "")) or ""
    return last


def get_last_model_output(conversations: List[dict]) -> str:
    last = ""
    for msg in conversations or []:
        role = msg.get("from", msg.get("role", ""))
        if role not in {"human", "user", "system"}:
            last = msg.get("value", msg.get("content", "")) or ""
    return last


def compute_all_metrics(references: List[str], hypotheses: List[str]):
    def _ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, str(a), str(b)).ratio()

    from difflib import SequenceMatcher
    scores = [_ratio(r, h) for r, h in zip(references, hypotheses)]
    zeros = [0.0 for _ in scores]
    return scores, scores, zeros, zeros, zeros, scores, zeros

# =========================
# Default public-release paths
# =========================
DATA_ROOT = "test_final/test_subset"  # taskX.json
META_ROOT = "./meta/subset"

DEFAULT_INFER_ROOT = "outputs"
DEFAULT_INFER_MODEL_TAG = "qwen3-235b-a22b-instruct-2507"

API_BACKEND = "local"

INFER_ALL_SENTINELS = {"all", "*", "__all__"}

# =========================
# Extract patient IDs from item identifiers
# =========================
PID_PAT = re.compile(r"patient_([^_]+)", re.IGNORECASE)


def extract_pid(item_id: str) -> str:
    m = PID_PAT.search(item_id or "")
    return m.group(1) if m else ""


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def append_rows_csv(csv_path: str, fieldnames: List[str], rows: List[Dict[str, Any]]):
    """Append rows to a CSV file and create the header when the file is new."""
    ensure_dir(os.path.dirname(csv_path))
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    def _norm(v):
        if v is None:
            return ""
        if isinstance(v, (int, float, str)):
            return v
        return json.dumps(v, ensure_ascii=False)

    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        for r in rows:
            out = {k: _norm(r.get(k)) for k in fieldnames}
            w.writerow(out)


# =========================
# task JSON: gt, inp, pids
# =========================
def load_data(file_path: str) -> Tuple[List[str], List[str], List[str]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    gt: List[str] = []
    inp: List[str] = []
    pids: List[str] = []

    for case in tqdm(raw_data, desc=f"Loading {os.path.basename(file_path)}", unit="case"):
        item_id = (case.get("id") or case.get("ID") or "").strip()
        pid = extract_pid(item_id)

        if "conversations" in case:
            if 'value' in case['conversations'][-1]:
                gt.append(case['conversations'][-1]['value'].strip())
                inp.append(case['conversations'][-2]['value'].strip())
            else:
                gt.append(case['conversations'][-1]['content'].strip())
                inp.append(case['conversations'][-2]['content'].strip())
        else:
            tail = case['messages'][-1]['content']
            parts = tail.split("think>")
            gt.append(parts[-1].strip())
            inp.append(parts[-2].strip())

        pids.append(pid)

    return gt, inp, pids


# =========================
# Prompt builders
# =========================
def format_generation_prompt(gt: str) -> str:
    return (
        f"Task: {task}\n\n"
        f"Reference content:\n{gt}\n\n"
        f"Evaluation concerns:\n{concerns}\n\n"
        f"Generate a scoring rubric in this required format:\n{criteria_format}"
    )


def format_judge_prompt(inf: str, criteria: str) -> str:
    return (
        f"Model output for task {task}:\n{inf}\n\n"
        f"Scoring rubric:\n{criteria}\n\n"
        "Evaluate whether each rubric item is covered by the model output. "
        "Return only valid JSON in the required judgement schema:\n"
        f"{grading_format}\n\n"
        "Judge only from the model output and the rubric. Do not use external patient information."
    )


def _keep_only_content_field(x: Any) -> Any:
    """
 criteria
 {"content": "...", "classification_reason": "..."} -> "..."
.
 """
    if x is None:
        return x
    if isinstance(x, list):
        return [_keep_only_content_field(v) for v in x]
    if isinstance(x, dict):
        if "content" in x:
            return x.get("content", "")
        return {k: _keep_only_content_field(v) for k, v in x.items()}
    return x


def strip_criteria_reasoning(criteria_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
 category -> level -> [content,...] (classification_reason)
 """
    if not isinstance(criteria_dict, dict):
        return {}

    out: Dict[str, Any] = {}
    for cat, lv_obj in criteria_dict.items():
        if not isinstance(lv_obj, dict):
            continue
        new_lv: Dict[str, Any] = {}
        for lv in ["primary", "secondary", "additional"]:
            if lv not in lv_obj:
                continue
            items = lv_obj.get(lv)
            cleaned = _keep_only_content_field(items)
            if isinstance(cleaned, list):
                new_lv[lv] = [str(v).strip() for v in cleaned if str(v).strip()]
            elif isinstance(cleaned, str):
                cleaned = cleaned.strip()
                new_lv[lv] = [cleaned] if cleaned else []
            else:
                new_lv[lv] = []
        if new_lv:
            out[cat] = new_lv
    return out


def prune_criteria_for_judge(c: Any, gradings: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only judge-facing criteria and drop case metadata fields."""
    if not isinstance(c, dict):
        return {}

    cats = list((gradings or {}).keys())
    if cats:
        pruned = {k: c.get(k) for k in cats if k in c}
        if pruned:
            return pruned

    drop_keys = {"gt", "input", "thinking", "error", "uid", "id"}
    return {k: v for k, v in c.items() if k not in drop_keys}


def recall_prompt(inf: str, gt: str) -> str:
    return (
        f"Model answer for task {task}:\n{inf}\n\n"
        f"Reference answer:\n{gt}\n\n"
        "Extract clinically meaningful terms from both answers. Treat equivalent expressions as matches. "
        "Return JSON only in this format: {\"student\": [\"xxx\", \"xxx\"], \"answer\": [\"xxx\", \"xxx\"]}."
    )


def save_dict_grouped(meta: dict, save_path: str) -> str:
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    if os.path.exists(save_path):
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
        if isinstance(data, dict):
            data = [data]
        data.append(meta)
    else:
        data = [meta]
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return save_path


def _safe_model_tag(x: str) -> str:
    s = (x or "").strip()
    s = s.replace("/", "_")
    s = re.sub(r"[^a-zA-Z0-9_.:+-]+", "_", s)
    s = s.replace(":", "_")
    if len(s) > 100:
        s = s[:100]
    return s or "model"


def _normalize_base_url(u: str) -> str:
    s = (u or "").strip()
    if not s:
        return s
    if not s.endswith("/"):
        s += "/"
    return s


def discover_infer_jsons(infer_root: str, tid: int) -> Dict[str, str]:
    """Discover inference JSON files for one task and map model tags to absolute paths.

Example:
    infer_root/result/moonshotai/kimi-k2_task9.json -> model_tag "moonshotai/kimi-k2"
"""
    infer_root = os.path.abspath(infer_root)
    suffix = f"_task{tid}.json"
    found: Dict[str, str] = {}

    for root, _dirs, files in os.walk(infer_root):
        for fn in files:
            if not fn.endswith(suffix):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, infer_root).replace(os.sep, "/")
            model_tag = rel[:-len(suffix)]
            if not model_tag:
                continue
            if model_tag in found:
                try:
                    if os.path.getmtime(full) > os.path.getmtime(found[model_tag]):
                        found[model_tag] = full
                except Exception:
                    found[model_tag] = full
            else:
                found[model_tag] = full

    return dict(sorted(found.items(), key=lambda kv: kv[0]))


@dataclass(frozen=True)
class JudgeSpec:
    backend: str
    model: str
    base_url: str
    name: str


def parse_judge_specs(spec_str: str, *, default_local_base: str, default_openai_base: str) -> List[JudgeSpec]:
    """
 spec:
 - local:modelA
 - local@http://localhost:8000
 - openai:gpt-4o-mini
 - openai@https://api.openai.com/v1/:gpt-4o-mini
 """
    specs: List[JudgeSpec] = []
    for raw in (spec_str or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        if ":" not in raw:
            raise ValueError(f"Bad judge spec (missing ':'): {raw}")

        left, model_name = raw.rsplit(":", 1)
        model_name = model_name.strip()
        if not model_name:
            raise ValueError(f"Bad judge spec (empty model): {raw}")

        if "@" in left:
            backend, base_url = left.split("@", 1)
            backend = backend.strip().lower()
            base_url = base_url.strip()
        else:
            backend = left.strip().lower()
            base_url = ""

        if backend not in ("local", "openai"):
            raise ValueError(f"Bad judge spec backend={backend}: {raw}")

        if not base_url:
            base_url = default_local_base if backend == "local" else default_openai_base

        base_url = _normalize_base_url(base_url)
        url_h = hashlib.md5(base_url.encode("utf-8")).hexdigest()[:8]
        name = f"{backend}@{url_h}:{_safe_model_tag(model_name)}"

        specs.append(JudgeSpec(backend=backend, model=model_name, base_url=base_url, name=name))

    if not specs:
        raise ValueError("Empty --judge-specs")
    return specs


def make_ensemble_tag(names: List[str]) -> str:
    norm = "|".join([n.strip() for n in names if n and n.strip()])
    h = hashlib.md5(norm.encode("utf-8")).hexdigest()[:10]
    short = "_".join([_safe_model_tag(n).split("_")[-1] for n in names])[:80]
    return f"vote_{len(names)}_{h}_{short}"


def _normalize_judge_specs_for_compare(specs: List[Any]) -> Set[str]:
    result = set()
    for sp in specs or []:
        if isinstance(sp, dict):
            model = sp.get("model", "")
        elif hasattr(sp, "model"):
            model = sp.model
        else:
            continue
        if model:
            result.add(model)
    return result


def _judge_specs_match(stored_specs: List[Any], current_specs: List[JudgeSpec]) -> bool:
    stored_set = _normalize_judge_specs_for_compare(stored_specs)
    current_set = _normalize_judge_specs_for_compare(current_specs)
    return stored_set == current_set


def save_criteria_overwrite_by_uid(pid: str, inp_text: str, meta: dict) -> None:
    cpath = get_meta_path_by_str(META_ROOT, task_id, patient_id=pid, subpath="criteria")
    target_uid = make_uid(pid, inp_text)

    if os.path.exists(cpath):
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                records = [loaded]
            elif isinstance(loaded, list):
                records = loaded
            else:
                records = []
        except Exception:
            records = []
    else:
        records = []

    new_records: List[dict] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        human_i = item.get("input", "")
        if not human_i:
            continue
        if make_uid(pid, human_i) == target_uid:
            continue
        new_records.append(item)

    new_records.append(meta)

    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(new_records, f, ensure_ascii=False, indent=2)


def save_judgement_overwrite_by_uid(
    pid: str,
    *,
    uid: str,
    student_model_tag: str,
    ensemble_tag: str,
    meta: dict
) -> None:
    subpath = f"judgement_{_safe_model_tag(student_model_tag)}__{_safe_model_tag(ensemble_tag)}"
    jpath = get_meta_path_by_str(META_ROOT, task_id, patient_id=pid, subpath=subpath)

    if os.path.exists(jpath):
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                records = [loaded]
            elif isinstance(loaded, list):
                records = loaded
            else:
                records = []
        except Exception:
            records = []
    else:
        records = []

    new_records: List[dict] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        if item.get("uid") == uid and item.get("ensemble_tag") == ensemble_tag:
            continue
        new_records.append(item)

    new_records.append(meta)

    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(new_records, f, ensure_ascii=False, indent=2)


def criteria_need_regen(pid: str, inp_text: str) -> bool:
    cpath = get_meta_path_by_str(META_ROOT, task_id, patient_id=pid, subpath="criteria")
    if not os.path.exists(cpath):
        return True

    try:
        with open(cpath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            records = [loaded]
        elif isinstance(loaded, list):
            records = loaded
        else:
            return True
    except Exception:
        return True

    target_uid = make_uid(pid, inp_text)
    any_match = False
    has_error = False

    for item in records:
        if not isinstance(item, dict):
            continue
        human_i = item.get("input", "")
        if not human_i:
            continue
        if make_uid(pid, human_i) != target_uid:
            continue
        any_match = True
        if "error" in item:
            has_error = True

    if not any_match:
        return True
    if has_error:
        return True
    return False


MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "1"))

# ======== globals assigned in main ========
client = None
model = ""
API_BACKEND = "local"

JUDGE_SPECS: List[JudgeSpec] = []
JUDGE_CLIENTS: Dict[tuple, Any] = {}
JUDGE_ENSEMBLE_TAG: str = ""
# ========================================


async def async_call_llm(prompt: str, as_dict: bool = True):
    """Call the configured judge model for criteria and recall prompts."""
    if API_BACKEND == "local":
        return await asyncio.to_thread(
            get_llm_response_local, client, model, prompt, 5, as_dict, timeout=600
        )
    elif API_BACKEND == "openai":
        return await asyncio.to_thread(
            get_llm_response, client, model, prompt, 5, as_dict
        )
    else:
        raise ValueError(f"Unknown API_BACKEND: {API_BACKEND}")


async def generate_criteria(gt: list, inp: list, pids: list, bar_desc: str = None):
    assert len(gt) == len(inp) == len(pids), "gt/inp/pids "

    all_pairs = list(zip(gt, inp, pids))
    pairs: List[Tuple[str, str, str]] = []
    skipped = 0
    for g, i, pid in all_pairs:
        if criteria_need_regen(pid, i):
            pairs.append((g, i, pid))
        else:
            skipped += 1

    print(
        f"[criteria] task{task_id}: total samples {len(all_pairs)}, "
        f"skipped {skipped}, "
        f"generate/repair {len(pairs)}."
    )

    if not pairs:
        print(f"[criteria] task{task_id}: no generation or repair needed.")
        return

    desc = bar_desc or f"Generating criteria (task_id={task_id})"
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def worker(idx: int, g: str, i: str, pid: str):
        prompt = format_generation_prompt(g)
        try:
            resp, thinking = await async_call_llm(prompt, as_dict=True)
        except Exception as e:
            resp = {"error": str(e)}
            thinking = ""
        resp.update({"gt": g, "input": i, "thinking": thinking})
        save_criteria_overwrite_by_uid(pid, i, resp)

    tasks = []
    for idx, (g, i, pid) in enumerate(pairs):
        async def _wrapped(idx=idx, g=g, i=i, pid=pid):
            async with sem:
                await worker(idx, g, i, pid)
        tasks.append(_wrapped())

    for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=desc, unit="case"):
        await fut


THINK_END_RE = re.compile(r"</think\s*>", re.IGNORECASE)
FINAL_RE = re.compile(r"##\s*Final Response\s*\n+", re.IGNORECASE)


def extract_final_answer(text: str) -> str:
    """
 model:
 1) <think>...</think>: </think> content
 2) no '## Thinking' '## Final Response': '## Final Response' content
 3) no: (strip)
 """
    if not text:
        return ""
    s = str(text).strip()

    m_all = list(THINK_END_RE.finditer(s))
    if m_all:
        return s[m_all[-1].end():].strip()

    if ("## Thinking" in s) and ("## Final Response" in s):
        m2_all = list(FINAL_RE.finditer(s))
        if m2_all:
            return s[m2_all[-1].end():].strip()

    return s



def build_scoring_triples_uid(
    infer_json_path: str,
    gt: List[str],
    inp: List[str],
    pids: List[str]
) -> List[tuple]:
    """
 triple: (inf_text, criteria_dict, gt_text, input_text, uid)
 """
    uid2inf: Dict[str, str] = {}
    if os.path.exists(infer_json_path):
        with open(infer_json_path, "r", encoding="utf-8") as f:
            infer_items = json.load(f)
        for obj in infer_items:
            full_id = (obj.get("id") or obj.get("ID") or "").strip()
            pid = extract_pid(full_id)
            convs = obj.get("conversations", [])
            human_text = get_last_human(convs)
            model_out = get_last_model_output(convs)
            model_out = extract_final_answer(model_out)

            if pid and human_text:
                uid = make_uid(pid, human_text)
                uid2inf[uid] = (model_out or "").strip()

        print("infer number:", len(uid2inf))
    else:
        print(f"[WARN] result file does not exist: {infer_json_path}")

    uid2crit: Dict[str, Dict[str, Any]] = {}
    for pid in set(pids):
        cpath = get_meta_path_by_str(META_ROOT, task_id, patient_id=pid, subpath="criteria")
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                loaded = [loaded]
            elif not isinstance(loaded, list):
                loaded = []
        except Exception:
            loaded = []
        for item in loaded:
            human_i = item.get("input", "")
            if human_i:
                uid2crit[make_uid(pid, human_i)] = item
    print("criteria number:", len(uid2crit))

    triples = []
    miss_inf, miss_crit = 0, 0
    for g, i, pid in zip(gt, inp, pids):
        uid = make_uid(pid, i)
        itext = (uid2inf.get(uid, "") or "").strip()
        if not itext:
            miss_inf += 1
        cdict = uid2crit.get(uid, {})
        if not cdict:
            miss_crit += 1
        triples.append((itext, cdict, g, i, uid))

    if miss_inf or miss_crit:
        print(f"[WARN] missing inference: {miss_inf}; missing criteria: {miss_crit}.")

    return triples


def filter_cases_with_nonempty_inference(triples: List[tuple],
                                         gt: List[str],
                                         inp: List[str],
                                         pids: List[str],
                                         tag: str = ""):
    assert len(triples) == len(gt) == len(inp) == len(pids)
    keep_idx = []
    for idx, t in enumerate(triples):
        inf_text = (t[0] or "").strip()
        if inf_text:
            keep_idx.append(idx)

    dropped = len(triples) - len(keep_idx)
    if dropped > 0:
        prefix = f"[{tag}] " if tag else ""
        print(f"{prefix}[INFO] skipped empty inference samples for judge/score/recall: kept {len(keep_idx)} / {len(triples)}, dropped {dropped}")

    triples2 = [triples[i] for i in keep_idx]
    gt2 = [gt[i] for i in keep_idx]
    inp2 = [inp[i] for i in keep_idx]
    pids2 = [pids[i] for i in keep_idx]
    return triples2, gt2, inp2, pids2, keep_idx


JUDGE_TIMEOUT = 60
JUDGE_MAX_RETRIES = 5
JITTER = (0.4, 1.2)


async def call_judge_with_retry(prompt: str, *, spec: JudgeSpec):
    last_err = None
    for k in range(1, JUDGE_MAX_RETRIES + 1):
        try:
            cli = JUDGE_CLIENTS[(spec.backend, spec.base_url)]
            if spec.backend == "local":
                coro = asyncio.to_thread(
                    get_llm_response_local, cli, spec.model, prompt, 5, True, timeout=600
                )
            else:
                coro = asyncio.to_thread(
                    get_llm_response, cli, spec.model, prompt, 5, True
                )
            resp, thinking = await asyncio.wait_for(coro, timeout=JUDGE_TIMEOUT)
            return resp, thinking
        except Exception as e:
            last_err = e
            if k >= JUDGE_MAX_RETRIES:
                break
            backoff = (2 ** (k - 1)) + random.uniform(*JITTER)
            await asyncio.sleep(backoff)
    raise last_err if last_err else RuntimeError("judge timeout")


def _majority_true(values: List[bool], total: int) -> bool:
    need = total // 2 + 1
    return sum(1 for v in values if v) >= need


def _merge_vote_nodes(nodes: List[Any], total_models: int) -> Any:
    """
 Merge judge outputs by majority vote for the covered field.
 / False.
 """
    norm_nodes = [n if n is not None else {} for n in nodes]

    if all(isinstance(n, dict) for n in norm_nodes):
        out: Dict[str, Any] = {}
        keys: Set[str] = set()
        for n in norm_nodes:
            keys.update(n.keys())

        for k in keys:
            if k == "covered":
                bools: List[bool] = []
                for n in norm_nodes:
                    v = n.get("covered", False)
                    bools.append(bool(v) if isinstance(v, bool) else False)
                out["covered"] = _majority_true(bools, total_models)
                out["vote_true"] = int(sum(1 for b in bools if b))
                out["vote_total"] = int(total_models)
            else:
                vals = [n.get(k) for n in norm_nodes]
                if any(isinstance(v, (dict, list)) for v in vals if v is not None):
                    out[k] = _merge_vote_nodes(vals, total_models)
                else:
                    v0 = None
                    for v in vals:
                        if v is None:
                            continue
                        if isinstance(v, str) and not v.strip():
                            continue
                        v0 = v
                        break
                    out[k] = v0
        return out

    if all(isinstance(n, list) for n in norm_nodes):
        max_len = max((len(n) for n in norm_nodes), default=0)
        out_list = []
        for i in range(max_len):
            ith = []
            for n in norm_nodes:
                ith.append(n[i] if i < len(n) else None)
            out_list.append(_merge_vote_nodes(ith, total_models))
        return out_list

    for n in norm_nodes:
        if n is None:
            continue
        if isinstance(n, str) and not n.strip():
            continue
        return n
    return None


def _judgement_has_any_category(resp: Any, gradings: Dict[str, Any]) -> bool:
    if not isinstance(resp, dict):
        return False
    cats = {str(k).strip() for k in (gradings or {}).keys() if str(k).strip()}
    if not cats:
        return False
    rkeys = {str(k).strip() for k in resp.keys() if str(k).strip()}
    return bool(cats & rkeys)


async def generate_judgements(
    triples: list,
    student_model_tag: str,
    pids: list,
    *,
    judge_specs: List[JudgeSpec],
    ensemble_tag: str,
    resume_skip: str = "any",
    resume_any_ensemble: bool = False,
    resume_match_judge_specs: bool = True,
) -> list:
    """
 (mode=judge):
 - resume_skip="any": skip(yes error/)
 - resume_skip="valid": skip records that already contain a valid category
 - resume_match_judge_specs=True: match existing judgements by judge specification
 """
    judgements: List[Optional[dict]] = [None] * len(pids)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    total_models = len(judge_specs)

    safe_stu = _safe_model_tag(student_model_tag)
    safe_ens = _safe_model_tag(ensemble_tag)
    subpath_exact = f"judgement_{safe_stu}__{safe_ens}"

    existing_valid: Dict[tuple, dict] = {}
    existing_any: Set[tuple] = set()

    def _extract_uid(item: dict, pid: str) -> Optional[str]:
        uid = item.get("uid")
        if uid:
            return uid
        inp_txt = item.get("input", "")
        if inp_txt:
            return make_uid(pid, inp_txt)
        return None

    def _clean_record(rec: dict) -> dict:
        rc = dict(rec)
        for k in ["inference", "thinking", "raw_judgements", "raw_errors", "judge_specs", "ensemble_tag", "uid", "input"]:
            rc.pop(k, None)
        return rc

    for pid in set(pids):
        paths_to_check = []
        jpath = get_meta_path_by_str(META_ROOT, task_id, patient_id=pid, subpath=subpath_exact)
        if os.path.exists(jpath):
            paths_to_check.append((jpath, True))

        if resume_any_ensemble or resume_match_judge_specs:
            task_dir = os.path.join(META_ROOT, f"task_{task_id}")
            if os.path.isdir(task_dir):
                prefix = f"judgement_{safe_stu}__"
                for fn in os.listdir(task_dir):
                    if fn.startswith(prefix):
                        judgement_dir = os.path.join(task_dir, fn)
                        if os.path.isdir(judgement_dir):
                            safe_pid = str(pid).strip().replace("/", "_").replace("\\", "_")
                            pid_file = os.path.join(judgement_dir, f"{safe_pid}.json")
                            if os.path.exists(pid_file) and pid_file != jpath:
                                paths_to_check.append((pid_file, False))

        for path, is_exact in paths_to_check:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    loaded = [loaded]
                elif not isinstance(loaded, list):
                    loaded = []
            except Exception:
                loaded = []

            for item in loaded:
                if not isinstance(item, dict):
                    continue

                should_use = False

                if is_exact:
                    if item.get("ensemble_tag") == ensemble_tag:
                        should_use = True
                    elif resume_match_judge_specs:
                        stored_specs = item.get("judge_specs", [])
                        if stored_specs and _judge_specs_match(stored_specs, judge_specs):
                            should_use = True
                else:
                    if resume_any_ensemble:
                        should_use = True
                    elif resume_match_judge_specs:
                        stored_specs = item.get("judge_specs", [])
                        if stored_specs and _judge_specs_match(stored_specs, judge_specs):
                            should_use = True

                if not should_use:
                    continue

                uid = _extract_uid(item, pid)
                if not uid:
                    continue
                key = (pid, uid)
                existing_any.add(key)

                if _judgement_has_any_category(item, gradings):
                    existing_valid[key] = _clean_record(item)

    if resume_skip not in ("any", "valid"):
        resume_skip = "any"

    skip_set = existing_any if resume_skip == "any" else set(existing_valid.keys())
    print(f"[judge-resume] resume_skip={resume_skip} resume_any_ensemble={resume_any_ensemble} "
          f"resume_match_judge_specs={resume_match_judge_specs} "
          f"skip_uids={len(skip_set)} / {len(triples)} (uid-level)")

    async def worker(idx: int, triple, pid: str):
        (inf_text, crit_dict, _g, input_text, uid) = triple
        if not (inf_text or "").strip():
            return

        key = (pid, uid)
        if key in skip_set:
            judgements[idx] = dict(existing_valid.get(key, {}))
            return

        c_for_judge = prune_criteria_for_judge(crit_dict, gradings)
        c_for_judge = strip_criteria_reasoning(c_for_judge)
        prompt = format_judge_prompt(inf_text, json.dumps(c_for_judge, ensure_ascii=False))

        raw_resps: List[Any] = []
        raw_errors: Dict[str, str] = {}
        raw_invalid: Dict[str, str] = {}

        for sp in judge_specs:
            try:
                r, _t = await call_judge_with_retry(prompt, spec=sp)
            except Exception as e:
                r, _t = {"error": str(e)}, ""

            keyname = sp.name
            raw_resps.append(r)

            if isinstance(r, dict) and "error" in r:
                raw_errors[keyname] = str(r.get("error"))

            ok = _judgement_has_any_category(r, gradings)
            if not ok:
                if isinstance(r, dict):
                    raw_invalid[keyname] = f"no_category(keys={list(r.keys())[:20]})"
                else:
                    raw_invalid[keyname] = f"bad_type(type={type(r).__name__})"

        vote_nodes = []
        for r in raw_resps:
            vote_nodes.append(r if _judgement_has_any_category(r, gradings) else {})
        voted = _merge_vote_nodes(vote_nodes, total_models)

        if not isinstance(voted, dict):
            voted = {}

        voted_meta = dict(voted)
        voted_meta.update({
            "uid": uid,
            "input": input_text,
            "inference": inf_text,
            "ensemble_tag": ensemble_tag,
            "judge_specs": [sp.__dict__ for sp in judge_specs],
            "raw_errors": raw_errors,
            "raw_invalid": raw_invalid,
            "raw_judgements": raw_resps,
        })

        save_judgement_overwrite_by_uid(
            pid,
            uid=uid,
            student_model_tag=student_model_tag,
            ensemble_tag=ensemble_tag,
            meta=voted_meta,
        )

        judgements[idx] = dict(voted)

    tasks = []
    for idx, (triple, pid) in enumerate(zip(triples, pids)):
        async def _wrapped(idx=idx, triple=triple, pid=pid):
            async with sem:
                await worker(idx, triple, pid)
        tasks.append(_wrapped())

    for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Judging (mixed backends + vote)", unit="case"):
        await fut

    return [j if j is not None else {} for j in judgements]



def load_judgements_from_meta(
    triples: list,
    pids: list,
    student_model_tag: str,
    *,
    ensemble_tag: str
) -> list:
    subpath = f"judgement_{_safe_model_tag(student_model_tag)}__{_safe_model_tag(ensemble_tag)}"

    uid2rec: Dict[str, dict] = {}

    for pid in set(pids):
        jpath = get_meta_path_by_str(
            META_ROOT,
            task_id,
            patient_id=pid,
            subpath=subpath
        )
        if not os.path.exists(jpath):
            continue
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                loaded = [loaded]
            elif not isinstance(loaded, list):
                loaded = []
        except Exception:
            loaded = []

        for item in loaded:
            if not isinstance(item, dict):
                continue
            if item.get("ensemble_tag") != ensemble_tag:
                continue
            uid = item.get("uid")
            if not uid:
                inp_txt = item.get("input", "")
                if inp_txt:
                    uid = make_uid(pid, inp_txt)
            if uid:
                uid2rec[uid] = item

    judgements = []
    missing = 0
    for triple, pid in zip(triples, pids):
        uid = triple[4]
        rec = uid2rec.get(uid)
        if rec is None:
            judgements.append({})
            missing += 1
        else:
            rc = dict(rec)
            for k in ["inference", "thinking", "raw_judgements", "raw_errors", "raw_invalid", "judge_specs", "ensemble_tag", "uid", "input"]:
                rc.pop(k, None)
            judgements.append(rc)

    print(f"[INFO] loaded {len(judgements)} judgements from {subpath}; missing {missing}.")
    return judgements


# =========================
# score: choice judgement file
# =========================
def parse_ensemble_tag_from_agg_filename(task_id: int, student_model_tag: str, agg_path: str) -> str:
    """Parse the ensemble tag from an aggregate judgement filename."""
    bn = os.path.basename(agg_path)
    prefix = f"task{task_id}_judgements_{_safe_model_tag(student_model_tag)}__"
    if bn.startswith(prefix) and bn.endswith(".json"):
        return bn[len(prefix):-5]
    return ""


def discover_score_judgement_candidates(task_id: int, student_model_tag: str) -> List[Dict[str, Any]]:
    """Find judgement files for one task and student model under META_ROOT."""
    safe_stu = _safe_model_tag(student_model_tag)
    prefix = f"task{task_id}_judgements_{safe_stu}__"

    out: List[Dict[str, Any]] = []
    if not os.path.isdir(META_ROOT):
        return out

    for fn in sorted(os.listdir(META_ROOT)):
        if not (fn.startswith(prefix) and fn.endswith(".json")):
            continue
        path = os.path.join(META_ROOT, fn)
        ens = fn[len(prefix):-5]
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = 0.0
        out.append({
            "filename": fn,
            "path": path,
            "ensemble_tag": ens,
            "mtime": mtime,
        })

    out.sort(key=lambda x: x["filename"])
    for i, item in enumerate(out, start=1):
        item["index"] = i
    return out


def print_score_judgement_candidates(task_id: int, student_model_tag: str):
    cands = discover_score_judgement_candidates(task_id, student_model_tag)
    print(f"[task{task_id}] student_model={student_model_tag} judgement files:")
    if not cands:
        print(" (none)")
        return
    for item in cands:
        print(f" [{item['index']}] {item['filename']}")


def resolve_score_judgement_source(
    task_id: int,
    student_model_tag: str,
    *,
    current_ensemble_tag: str,
    score_judgement_index: int = 0,
    score_judgement_tag: str = "",
    score_judgement_file: str = "",
) -> Tuple[str, str]:
    """
:
 (ensemble_tag, agg_path)

:
 -: index / tag / file
 - default: use JUDGE_ENSEMBLE_TAG
 - tag/index,, skipmodel
 """
    score_judgement_tag = (score_judgement_tag or "").strip()
    score_judgement_file = (score_judgement_file or "").strip()

    chosen = int(bool(score_judgement_index)) + int(bool(score_judgement_tag)) + int(bool(score_judgement_file))
    if chosen > 1:
        raise ValueError("--score-judgement-index / --score-judgement-tag / --score-judgement-file ")

    if chosen == 0:
        return current_ensemble_tag, ""

    candidates = discover_score_judgement_candidates(task_id, student_model_tag)

    if score_judgement_file:
        agg_path = os.path.abspath(score_judgement_file)
        if not os.path.exists(agg_path):
            raise FileNotFoundError(f"--score-judgement-file specified file does not exist: {agg_path}")
        ens = parse_ensemble_tag_from_agg_filename(task_id, student_model_tag, agg_path)
        print(f"[task{task_id}] score uses specified judgement file: {agg_path}")
        if ens:
            print(f"[task{task_id}] ensemble_tag: {ens}")
        else:
            print(f"[task{task_id}] warning: file has no ensemble_tag; matching samples by uid.")
        return ens, agg_path

    if score_judgement_index:
        if score_judgement_index < 1 or score_judgement_index > len(candidates):
            print_score_judgement_candidates(task_id, student_model_tag)
            print(
                f"[WARN] task{task_id} student_model={student_model_tag} --score-judgement-index={score_judgement_index} "
                f"is outside the available range ({len(candidates)}); skipping model."
            )
            return "", ""
        item = candidates[score_judgement_index - 1]
        print(f"[task{task_id}] score judgement file [{item['index']}]: {item['filename']}")
        return item["ensemble_tag"], item["path"]

    raw = os.path.basename(score_judgement_tag)

    for item in candidates:
        if raw == item["filename"]:
            print(f"[task{task_id}] score judgement file: {item['filename']}")
            return item["ensemble_tag"], item["path"]

    prefix = f"task{task_id}_judgements_{_safe_model_tag(student_model_tag)}__"
    norm = raw
    if norm.startswith(prefix):
        norm = norm[len(prefix):]
    if norm.endswith(".json"):
        norm = norm[:-5]

    for item in candidates:
        if norm == item["ensemble_tag"]:
            print(f"[task{task_id}] score judgement file: {item['filename']}")
            return item["ensemble_tag"], item["path"]

    print_score_judgement_candidates(task_id, student_model_tag)
    print(
        f"[WARN] task{task_id} student_model={student_model_tag} judgement not found: {score_judgement_tag}; "
        f"skipping model."
    )
    return "", ""


def load_judgements_cached(
    triples: list,
    pids: list,
    student_model_tag: str,
    *,
    ensemble_tag: str
) -> list:
    agg_path = os.path.join(
        META_ROOT,
        f"task{task_id}_judgements_{_safe_model_tag(student_model_tag)}__{_safe_model_tag(ensemble_tag)}.json"
    )

    if os.path.exists(agg_path):
        with open(agg_path, "r", encoding="utf-8") as f:
            judgements = json.load(f)
        if len(judgements) == len(triples):
            print(f"[INFO] loaded {len(judgements)} sample judgements from {agg_path}.")
            return judgements
        else:
            print(
                f"[INFO] judgement file {agg_path} sample count ({len(judgements)}) "
                f"differs from evaluation sample count ({len(triples)}); falling back to per-patient judgement files."
            )

    judgements = load_judgements_from_meta(triples, pids, student_model_tag, ensemble_tag=ensemble_tag)
    if judgements and len(judgements) == len(triples):
        os.makedirs(os.path.dirname(agg_path), exist_ok=True)
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(judgements, f, ensure_ascii=False, indent=2)
        print(f"[INFO] loaded judgements and cached them to {agg_path}.")
    return judgements


def load_judgements_for_score(
    triples: list,
    pids: list,
    student_model_tag: str,
    *,
    ensemble_tag: str,
    agg_path_override: str = "",
) -> list:
    """
 score load:
 1) specified judgement file
 2) filesample, per-patient judgement file uid
 3) specified file and ensemble tag
 """
    agg_path_override = (agg_path_override or "").strip()

    if agg_path_override:
        if not os.path.exists(agg_path_override):
            raise FileNotFoundError(f"specified judgement file does not exist: {agg_path_override}")

        with open(agg_path_override, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict):
            loaded = [loaded]
        elif not isinstance(loaded, list):
            loaded = []

        if len(loaded) == len(triples):
            print(f"[INFO] loaded {len(loaded)} records from specified judgement file: {agg_path_override}")
            return loaded

        print(
            f"[INFO] specified judgement file sample count ({len(loaded)}) "
            f"differs from evaluation sample count ({len(triples)}); falling back to per-patient judgement files by uid."
        )

        if ensemble_tag:
            return load_judgements_from_meta(
                triples,
                pids,
                student_model_tag,
                ensemble_tag=ensemble_tag,
            )

        print("[WARN] No matching ensemble tag was found for the specified file.")
        return []

    return load_judgements_cached(
        triples,
        pids,
        student_model_tag,
        ensemble_tag=ensemble_tag,
    )


def get_score_output_paths(task_id: int, student_model_tag: str, ensemble_tag: str) -> Tuple[str, str]:
    safe_stu = _safe_model_tag(student_model_tag)
    safe_ens = _safe_model_tag(ensemble_tag)
    out_scores = os.path.join(META_ROOT, f"task{task_id}_scores_{safe_stu}__{safe_ens}.json")
    out_summary = os.path.join(META_ROOT, f"task{task_id}_summary_{safe_stu}__{safe_ens}.json")
    return out_scores, out_summary



def score_outputs_already_done(task_id: int, student_model_tag: str, ensemble_tag: str) -> bool:
    """Return whether score and summary outputs already exist for this ensemble."""
    if not ensemble_tag:
        return False
    out_scores, out_summary = get_score_output_paths(task_id, student_model_tag, ensemble_tag)
    try:
        ok_scores = os.path.exists(out_scores) and os.path.getsize(out_scores) > 0
        ok_summary = os.path.exists(out_summary) and os.path.getsize(out_summary) > 0
    except Exception:
        return False
    return bool(ok_scores and ok_summary)


def filter_invalid_judgements_with_indices(judgements: List[dict],
                                           gradings: Dict[str, Any]):
    categories = set(gradings.keys())
    filtered_j = []
    keep_indices = []
    drop_indices = []

    for idx, j in enumerate(judgements):
        if not isinstance(j, dict):
            drop_indices.append(idx)
            continue
        has_category = any(k in categories for k in j.keys())
        if has_category:
            filtered_j.append(j)
            keep_indices.append(idx)
        else:
            drop_indices.append(idx)

    print(
        f"[INFO] valid samples: {len(keep_indices)} / {len(judgements)} "
        f"({len(drop_indices)} dropped error/inference/thinking samples)"
    )
    return filtered_j, keep_indices, drop_indices


def _iter_dict_items(x):
    if x is None:
        return
    if isinstance(x, dict):
        yield x
        return
    if isinstance(x, list):
        for y in x:
            yield from _iter_dict_items(y)


def calculate_scores(judgements, gradings):
    results = []
    for judgement in judgements:
        score_dict = {}
        for category in gradings:
            score_dict[category] = {
                "primary": [0, 0],
                "secondary": [0, 0],
                "additional": [0, 0]
            }
        for category, items in judgement.items():
            if category in gradings:
                for level in ["primary", "secondary", "additional"]:
                    if level in items:
                        items_list = items[level]
                        per_item_score = gradings[category][level]
                        flat_items = list(_iter_dict_items(items_list))
                        covered = sum(1 for item in flat_items if item.get("covered", False))
                        total = len(flat_items)
                        score_dict[category][level] = [covered * per_item_score, total * per_item_score]
        results.append(score_dict)
    return results


def summarize_scores(
    jmetric: List[Dict[str, Dict[str, List[float]]]],
    gradings: Dict[str, Any],
    pids_valid: List[str],
    *,
    gt_valid: Optional[List[str]] = None,
    inf_valid: Optional[List[str]] = None,
):
    levels = ["primary", "secondary", "additional"]
    categories = sorted(set(gradings.keys()))

    def _safe_ratio(a: float, b: float) -> Optional[float]:
        return (a / b) if b > 0 else None

    def _mean(xs: List[float]) -> Optional[float]:
        return (sum(xs) / len(xs)) if xs else None

    def _median(xs: List[float]) -> Optional[float]:
        return statistics.median(xs) if xs else None

    sample_norm_scores: List[Optional[float]] = []
    for record in jmetric:
        total_actual = 0.0
        total_max = 0.0
        for cat in categories:
            cat_dict = record.get(cat, {})
            for lv in levels:
                a, m = cat_dict.get(lv, [0.0, 0.0])
                total_actual += float(a)
                total_max += float(m)
        sample_norm_scores.append(_safe_ratio(total_actual, total_max))
    valid_case = [s for s in sample_norm_scores if s is not None]
    case_macro_mean = _mean(valid_case)

    patient_total_acc: Dict[str, List[float]] = {}
    for record, pid in zip(jmetric, pids_valid):
        total_actual = 0.0
        total_max = 0.0
        for cat in categories:
            for lv in levels:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                total_actual += float(a)
                total_max += float(m)
        patient_total_acc.setdefault(pid, [0.0, 0.0])
        patient_total_acc[pid][0] += total_actual
        patient_total_acc[pid][1] += total_max
    patient_norms = []
    for pid, (act, mx) in patient_total_acc.items():
        r = _safe_ratio(act, mx)
        if r is not None:
            patient_norms.append(r)
    patient_macro_mean = _mean(patient_norms)

    category_micro: Dict[str, Dict[str, Any]] = {}
    category_macro: Dict[str, Optional[float]] = {}

    patient_cat_acc: Dict[str, Dict[str, List[float]]] = {}
    for record, pid in zip(jmetric, pids_valid):
        patient_cat_acc.setdefault(pid, {})
        for cat in categories:
            patient_cat_acc[pid].setdefault(cat, [0.0, 0.0])
            for lv in levels:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                patient_cat_acc[pid][cat][0] += float(a)
                patient_cat_acc[pid][cat][1] += float(m)

    for cat in categories:
        a_sum = 0.0
        m_sum = 0.0
        for record in jmetric:
            for lv in levels:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                a_sum += float(a)
                m_sum += float(m)
        category_micro[cat] = {
            "micro": _safe_ratio(a_sum, m_sum),
            "sum_actual": a_sum,
            "sum_max": m_sum,
        }
        macro_list = []
        for pid in patient_cat_acc:
            act, mx = patient_cat_acc[pid][cat]
            r = _safe_ratio(act, mx)
            if r is not None:
                macro_list.append(r)
        category_macro[cat] = _mean(macro_list)

    level_micro: Dict[str, Dict[str, Any]] = {}
    level_macro: Dict[str, Optional[float]] = {}

    patient_level_acc: Dict[str, Dict[str, List[float]]] = {}
    for record, pid in zip(jmetric, pids_valid):
        patient_level_acc.setdefault(pid, {lv: [0.0, 0.0] for lv in levels})
        for lv in levels:
            a_lv = 0.0
            m_lv = 0.0
            for cat in categories:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                a_lv += float(a)
                m_lv += float(m)
            patient_level_acc[pid][lv][0] += a_lv
            patient_level_acc[pid][lv][1] += m_lv

    for lv in levels:
        a_sum = 0.0
        m_sum = 0.0
        for record in jmetric:
            for cat in categories:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                a_sum += float(a)
                m_sum += float(m)
        level_micro[lv] = {
            "micro": _safe_ratio(a_sum, m_sum),
            "sum_actual": a_sum,
            "sum_max": m_sum,
        }
        macro_list = []
        for pid in patient_level_acc:
            act, mx = patient_level_acc[pid][lv]
            r = _safe_ratio(act, mx)
            if r is not None:
                macro_list.append(r)
        level_macro[lv] = _mean(macro_list)

    cat_level_micro: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for cat in categories:
        cat_level_micro[cat] = {}
        for lv in levels:
            a_sum = 0.0
            m_sum = 0.0
            for record in jmetric:
                a, m = record.get(cat, {}).get(lv, [0.0, 0.0])
                a_sum += float(a)
                m_sum += float(m)
            cat_level_micro[cat][lv] = {
                "micro": _safe_ratio(a_sum, m_sum),
                "sum_actual": a_sum,
                "sum_max": m_sum,
            }

    mt = None
    if gt_valid is not None and inf_valid is not None and len(gt_valid) == len(inf_valid) and len(gt_valid) > 0:
        try:
            rouge_l, bleu1, bleu2, bleu3, bleu4, cosine, bert_f1 = compute_all_metrics(gt_valid, inf_valid)

            def _clean(xs):
                return [x for x in xs if x is not None]

            mt = {
                "n": len(gt_valid),
                "rougeL_mean": _mean(_clean(rouge_l)),
                "rougeL_median": _median(_clean(rouge_l)),
                "bleu1_mean": _mean(_clean(bleu1)),
                "bleu1_median": _median(_clean(bleu1)),
                "bleu2_mean": _mean(_clean(bleu2)),
                "bleu2_median": _median(_clean(bleu2)),
                "bleu3_mean": _mean(_clean(bleu3)),
                "bleu3_median": _median(_clean(bleu3)),
                "bleu4_mean": _mean(_clean(bleu4)),
                "bleu4_median": _median(_clean(bleu4)),
                "cosine_mean": _mean(_clean(cosine)),
                "cosine_median": _median(_clean(cosine)),
                "bertscore_f1_mean": _mean(_clean(bert_f1)),
                "bertscore_f1_median": _median(_clean(bert_f1)),
            }
        except Exception as e:
            print(f"[WARN] MT metrics failed: {e}")

    return {
        "case_macro_mean": case_macro_mean,
        "patient_macro_mean": patient_macro_mean,
        "n_cases": len(jmetric),
        "n_patients": len(set(pids_valid)),
        "category_micro": category_micro,
        "category_macro": category_macro,
        "level_micro": level_micro,
        "level_macro": level_macro,
        "category_level_micro": cat_level_micro,
        "mt": mt,
    }



def write_metric_outputs(
    out_dir: str,
    *,
    run_ts: str,
    task_id: int,
    student_model_tag: str,
    judge_backend: str,
    judge_model: str,
    judge_ensemble_tag: str,
    infer_root: str,
    subset_csv: str,
    summary: Dict[str, Any],
):
    ensure_dir(out_dir)

    common = {
        "run_ts": run_ts,
        "task_id": task_id,
        "student_model_tag": student_model_tag,
        "judge_backend": judge_backend,
        "judge_model": judge_model,
        "judge_ensemble_tag": judge_ensemble_tag,
        "infer_root": infer_root,
        "subset_csv": subset_csv,
        "n_cases": summary.get("n_cases"),
        "n_patients": summary.get("n_patients"),
    }

    mt = summary.get("mt") or {}
    overall_row = {
        **common,
        "case_macro_mean": summary.get("case_macro_mean"),
        "patient_macro_mean": summary.get("patient_macro_mean"),
        "rougeL_mean": mt.get("rougeL_mean"),
        "rougeL_median": mt.get("rougeL_median"),
        "bleu1_mean": mt.get("bleu1_mean"),
        "bleu1_median": mt.get("bleu1_median"),
        "bleu2_mean": mt.get("bleu2_mean"),
        "bleu2_median": mt.get("bleu2_median"),
        "bleu3_mean": mt.get("bleu3_mean"),
        "bleu3_median": mt.get("bleu3_median"),
        "bleu4_mean": mt.get("bleu4_mean"),
        "bleu4_median": mt.get("bleu4_median"),
        "cosine_mean": mt.get("cosine_mean"),
        "cosine_median": mt.get("cosine_median"),
        "bertscore_f1_mean": mt.get("bertscore_f1_mean"),
        "bertscore_f1_median": mt.get("bertscore_f1_median"),
        "mt_n": mt.get("n"),
    }
    overall_fields = list(overall_row.keys())
    append_rows_csv(os.path.join(out_dir, "summary_scores.csv"), overall_fields, [overall_row])

    level_rows = []
    for lv, obj in (summary.get("level_micro") or {}).items():
        level_rows.append({
            **common,
            "level": lv,
            "micro": obj.get("micro"),
            "macro": (summary.get("level_macro") or {}).get(lv),
            "sum_actual": obj.get("sum_actual"),
            "sum_max": obj.get("sum_max"),
        })
    if level_rows:
        level_fields = list(level_rows[0].keys())
        append_rows_csv(os.path.join(out_dir, "level_scores.csv"), level_fields, level_rows)

    cat_rows = []
    for cat, obj in (summary.get("category_micro") or {}).items():
        cat_rows.append({
            **common,
            "category": cat,
            "micro": obj.get("micro"),
            "macro": (summary.get("category_macro") or {}).get(cat),
            "sum_actual": obj.get("sum_actual"),
            "sum_max": obj.get("sum_max"),
        })
    if cat_rows:
        cat_fields = list(cat_rows[0].keys())
        append_rows_csv(os.path.join(out_dir, "category_scores.csv"), cat_fields, cat_rows)

    cl_rows = []
    cl = summary.get("category_level_micro") or {}
    for cat, lv_dict in cl.items():
        for lv, obj in lv_dict.items():
            cl_rows.append({
                **common,
                "category": cat,
                "level": lv,
                "micro": obj.get("micro"),
                "sum_actual": obj.get("sum_actual"),
                "sum_max": obj.get("sum_max"),
            })
    if cl_rows:
        cl_fields = list(cl_rows[0].keys())
        append_rows_csv(os.path.join(out_dir, "category_level_scores.csv"), cl_fields, cl_rows)

    mt_rows = []
    if mt:
        for name in ["rougeL", "bleu1", "bleu2", "bleu3", "bleu4", "cosine", "bertscore_f1"]:
            mt_rows.append({
                **common,
                "metric": name,
                "mean": mt.get(f"{name}_mean"),
                "median": mt.get(f"{name}_median"),
                "mt_n": mt.get("n"),
            })
    if mt_rows:
        mt_fields = list(mt_rows[0].keys())
        append_rows_csv(os.path.join(out_dir, "mt_metrics.csv"), mt_fields, mt_rows)


async def run_one_task(
    tid: int,
    mode: str,
    infer_model_tag: str,
    infer_root: str,
    max_num: int,
    subset_pids: Optional[Set[str]] = None,
    *,
    infer_json_path_override: Optional[str] = None,
    run_ts: str,
    metrics_output_dir: str,
    subset_csv_path: str,
    judge_backend: str,
    judge_model: str,
    judge_ensemble_tag: str,
):
    global task, task_id, concerns, criteria_format, grading_format, gradings

    task_id = tid

    mod_name = f"task{tid}promt"
    try:
        mod = __import__(mod_name, fromlist=["task", "task_id", "concerns", "criteria_format", "grading_format", "gradings"])
    except ImportError as e:
        print(f"[WARN] failed to import {mod_name}; skipping task{tid}: {e}")
        return

    task = getattr(mod, "task")
    _tid_from_mod = getattr(mod, "task_id")
    assert _tid_from_mod == tid, f"{mod_name}.task_id={_tid_from_mod} does not match tid {tid}"

    concerns = getattr(mod, "concerns")
    criteria_format = getattr(mod, "criteria_format")
    grading_format = getattr(mod, "grading_format")
    gradings = getattr(mod, "gradings")

    if not isinstance(gradings, dict) or not gradings:
        raise RuntimeError(f"[task{tid}] {mod_name}.gradings is empty; all judge outputs would be invalid.")
    print(f"[task{tid}] gradings categories = {list(gradings.keys())}")

    print(f"\n========== start processing task{tid}, mode={mode}, student_model={infer_model_tag} ==========")

    data_path = os.path.join(DATA_ROOT, f"task{tid}.json")
    if not os.path.exists(data_path):
        print(f"[WARN] data file does not exist: {data_path}; skipping task{tid}")
        return

    gt, inp, pids = load_data(data_path)

    if subset_pids is not None:
        before_n = len(pids)
        gt_f, inp_f, pids_f = [], [], []
        for g, i, p in zip(gt, inp, pids):
            if p and (p in subset_pids):
                gt_f.append(g)
                inp_f.append(i)
                pids_f.append(p)
        gt, inp, pids = gt_f, inp_f, pids_f
        print(f"[task{tid}] subset_test_ids filter: {before_n} -> {len(pids)} samples")
        if not pids:
            print(f"[task{tid}] no samples after filtering; skipping task.")
            return

    if max_num > 0 and len(pids) > max_num:
        print(f"[task{tid}] max_num={max_num}; sampling first {max_num} cases")
        gt, inp, pids = gt[:max_num], inp[:max_num], pids[:max_num]

    if mode in ("criteria", "all"):
        await generate_criteria(gt, inp, pids, bar_desc=f"Generating criteria (task{tid})")

    if mode in ("judge", "score", "all"):
        infer_json_path = infer_json_path_override or os.path.join(infer_root, f"{infer_model_tag}_task{tid}.json")
        if not os.path.exists(infer_json_path):
            print(f"[WARN] result file does not exist: {infer_json_path}; skipping task{tid} judge/score")
            return

        triples = build_scoring_triples_uid(infer_json_path, gt, inp, pids)

        triples, gt, inp, pids, _keep_idx = filter_cases_with_nonempty_inference(
            triples, gt, inp, pids, tag=f"task{tid}"
        )
        if not triples:
            print(f"[task{tid}] no non-empty inference samples; skipping judge/score/recall.")
            return

        score_ensemble_tag = JUDGE_ENSEMBLE_TAG
        score_agg_path = ""

        if mode == "score":
            if args.list_score_judgements:
                print_score_judgement_candidates(tid, infer_model_tag)
                return

            score_ensemble_tag, score_agg_path = resolve_score_judgement_source(
                task_id=tid,
                student_model_tag=infer_model_tag,
                current_ensemble_tag=JUDGE_ENSEMBLE_TAG,
                score_judgement_index=args.score_judgement_index,
                score_judgement_tag=args.score_judgement_tag,
                score_judgement_file=args.score_judgement_file,
            )

            if not score_ensemble_tag and not score_agg_path:
                print(f"[WARN] task{tid} student_model={infer_model_tag} no judgement source; skipping score.")
                return

            if not score_ensemble_tag and score_agg_path:
                print(f"[WARN] task{tid} student_model={infer_model_tag} no ensemble_tag for score output; skipping.")
                return

            if score_outputs_already_done(tid, infer_model_tag, score_ensemble_tag):
                out_scores0, out_summary0 = get_score_output_paths(tid, infer_model_tag, score_ensemble_tag)
                print(
                    f"[INFO] task{tid} student_model={infer_model_tag} score outputs already exist; skipping:\n"
                    f" - {out_scores0}\n"
                    f" - {out_summary0}"
                )
                return

        if mode in ("judge", "all"):
            judgements_new = await generate_judgements(
                triples, infer_model_tag, pids,
                judge_specs=JUDGE_SPECS,
                ensemble_tag=JUDGE_ENSEMBLE_TAG,
                resume_skip=args.resume_skip,
                resume_any_ensemble=args.resume_any_ensemble,
                resume_match_judge_specs=args.resume_match_judge_specs,
            )

            agg_path = os.path.join(
                META_ROOT,
                f"task{tid}_judgements_{_safe_model_tag(infer_model_tag)}__{_safe_model_tag(JUDGE_ENSEMBLE_TAG)}.json"
            )
            os.makedirs(os.path.dirname(agg_path), exist_ok=True)
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump(judgements_new, f, ensure_ascii=False, indent=2)
            print(f"[INFO] judgement result: {agg_path}")

        if mode in ("score", "all"):
            judgements_all = load_judgements_for_score(
                triples,
                pids,
                infer_model_tag,
                ensemble_tag=score_ensemble_tag,
                agg_path_override=score_agg_path,
            )
            if not judgements_all:
                print(f"[WARN] task{tid} could not load judgements.")
                return

            judgements_valid, keep_indices, drop_indices = filter_invalid_judgements_with_indices(
                judgements_all, gradings
            )
            if not judgements_valid:
                print(f"[WARN] task{tid} has no valid samples.")
                return

            pids_valid = [pids[i] for i in keep_indices]
            gt_valid = [gt[i] for i in keep_indices]
            triples_valid = [triples[i] for i in keep_indices]
            inf_valid = [t[0] for t in triples_valid]

            jmetric = calculate_scores(judgements_valid, gradings)

            out_scores = os.path.join(
                META_ROOT,
                f"task{tid}_scores_{_safe_model_tag(infer_model_tag)}__{_safe_model_tag(score_ensemble_tag)}.json"
            )
            os.makedirs(os.path.dirname(out_scores), exist_ok=True)
            score_items = [{"patient_id": pid, "scores": score} for pid, score in zip(pids_valid, jmetric)]
            with open(out_scores, "w", encoding="utf-8") as f:
                json.dump(score_items, f, ensure_ascii=False, indent=2)
            print(f"[INFO] Score file saved to: {out_scores}")

            summary_obj = summarize_scores(
                jmetric, gradings, pids_valid,
                gt_valid=gt_valid,
                inf_valid=inf_valid,
            )

            out_summary = os.path.join(
                META_ROOT,
                f"task{tid}_summary_{_safe_model_tag(infer_model_tag)}__{_safe_model_tag(score_ensemble_tag)}.json"
            )
            with open(out_summary, "w", encoding="utf-8") as f:
                json.dump(summary_obj, f, ensure_ascii=False, indent=2)
            print(f"[INFO] Summary file saved to: {out_summary}")

            score_judge_backend = judge_backend
            score_judge_model = judge_model
            if score_agg_path:
                score_judge_backend = "existing"
                score_judge_model = os.path.basename(score_agg_path)

            write_metric_outputs(
                metrics_output_dir,
                run_ts=run_ts,
                task_id=tid,
                student_model_tag=infer_model_tag,
                judge_backend=score_judge_backend,
                judge_model=score_judge_model,
                judge_ensemble_tag=score_ensemble_tag,
                infer_root=infer_root,
                subset_csv=subset_csv_path,
                summary=summary_obj,
            )
            print(f"[INFO] Metrics appended to CSVs under: {metrics_output_dir}")


async def main(args):
    global client, model, API_BACKEND, JUDGE_SPECS, JUDGE_CLIENTS, JUDGE_ENSEMBLE_TAG

    run_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    metrics_output_dir = args.metrics_output_dir or os.path.join(META_ROOT, "metric_outputs")

    API_BACKEND = args.api_backend
    model = args.eval_model or "local-model"

    if args.infer_all and args.score_judgement_file:
        raise ValueError("--score-judgement-file cannot be used with --infer-all; use --score-judgement-index or --score-judgement-tag instead")

    if API_BACKEND == "local":
        LOCAL_BASE_URL = _normalize_base_url(os.getenv("LOCAL_BASE_URL", "http://localhost:8000"))
        LOCAL_HEADERS = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-local",
        }
        client = httpx.Client(
            base_url=LOCAL_BASE_URL,
            headers=LOCAL_HEADERS,
            timeout=60,
        )
        print(f"[INFO] using local HTTP backend, base_url={LOCAL_BASE_URL}, model(default)={model}")

    elif API_BACKEND == "openai":
        from openai import OpenAI
        base_url = _normalize_base_url(args.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("API_BACKEND=openai requires OPENAI_API_KEY")
        client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
        print(f"[INFO] using OpenAI-compatible API, base_url={base_url}, model(default)={model}")
    else:
        raise ValueError(f"unknown API_BACKEND: {API_BACKEND}")

    default_local_base = _normalize_base_url(os.getenv("LOCAL_BASE_URL", "http://localhost:8000"))
    default_openai_base = _normalize_base_url(args.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))

    judge_specs: List[JudgeSpec] = []
    if args.judge_specs.strip():
        judge_specs = parse_judge_specs(
            args.judge_specs,
            default_local_base=default_local_base,
            default_openai_base=default_openai_base,
        )
    elif args.judge_models.strip():
        models = [x.strip() for x in args.judge_models.split(",") if x.strip()]
        if not models:
            raise ValueError("--judge-models is empty")
        for m in models:
            base = default_local_base if args.api_backend == "local" else default_openai_base
            base = _normalize_base_url(base)
            url_h = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
            name = f"{args.api_backend}@{url_h}:{_safe_model_tag(m)}"
            judge_specs.append(JudgeSpec(backend=args.api_backend, model=m, base_url=base, name=name))
    else:
        base = default_local_base if API_BACKEND == "local" else default_openai_base
        base = _normalize_base_url(base)
        url_h = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
        name = f"{API_BACKEND}@{url_h}:{_safe_model_tag(model)}"
        judge_specs = [JudgeSpec(backend=API_BACKEND, model=model, base_url=base, name=name)]

    if len(judge_specs) < 1:
        raise ValueError("At least one judge specification is required")

    judge_clients: Dict[tuple, Any] = {}

    LOCAL_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-local",
    }

    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    for sp in judge_specs:
        key = (sp.backend, sp.base_url)
        if key in judge_clients:
            continue
        if sp.backend == "local":
            judge_clients[key] = httpx.Client(base_url=sp.base_url, headers=LOCAL_HEADERS, timeout=60)
        else:
            from openai import OpenAI
            if not openai_api_key:
                raise RuntimeError("OpenAI judge specifications require OPENAI_API_KEY")
            judge_clients[key] = OpenAI(api_key=openai_api_key, base_url=sp.base_url.rstrip("/"))

    JUDGE_SPECS = judge_specs
    JUDGE_CLIENTS = judge_clients
    JUDGE_ENSEMBLE_TAG = make_ensemble_tag([sp.name for sp in judge_specs])

    print("[INFO] Judge specs (mixed backends):")
    for sp in judge_specs:
        print(f" - backend={sp.backend} base_url={sp.base_url} model={sp.model} name={sp.name}")
    print(f"[INFO] Judge ensemble tag: {JUDGE_ENSEMBLE_TAG}")

    task_ids: List[int] = []
    for x in args.tasks.split(","):
        x = x.strip()
        if not x:
            continue
        try:
            task_ids.append(int(x))
        except ValueError:
            print(f"[WARN] invalid task id ignored: {x}")
    task_ids = sorted(set(task_ids))
    if not task_ids:
        print("[ERROR] no valid task id specified (for example, --tasks 5,6,10)")
        return

    subset_pids: Optional[Set[str]] = None
    subset_csv_path = args.subset_test_ids_csv or ""
    if subset_csv_path:
        subset_path = Path(subset_csv_path)
        if not subset_path.exists():
            raise FileNotFoundError(f"--subset-test-ids-csv specified file does not exist: {subset_path}")
        df_sub = pd.read_csv(subset_path, encoding="utf-8-sig")
        if "patient_id" not in df_sub.columns:
            raise ValueError(f"{subset_path} must contain a patient_id column")
        subset_pids = set(df_sub["patient_id"].astype(str).tolist())
        print(f"[INFO] loaded {len(subset_pids)} patient_id values from subset_test_ids_csv; evaluating this subset.")

    judge_backend = "mixed" if any(sp.backend != judge_specs[0].backend for sp in judge_specs) else judge_specs[0].backend
    judge_model = "|".join([sp.name for sp in judge_specs])

    for tid in task_ids:
        infer_all = bool(args.infer_all) or ((args.infer_model_tag or "").strip().lower() in INFER_ALL_SENTINELS)

        if infer_all and args.mode == "criteria":
            await run_one_task(
                tid=tid,
                mode=args.mode,
                infer_model_tag="ALL",
                infer_root=args.infer_root,
                max_num=args.max_num,
                subset_pids=subset_pids,
                run_ts=run_ts,
                metrics_output_dir=metrics_output_dir,
                subset_csv_path=subset_csv_path,
                judge_backend=judge_backend,
                judge_model=judge_model,
                judge_ensemble_tag=JUDGE_ENSEMBLE_TAG,
            )
            continue

        if infer_all:
            model2path = discover_infer_jsons(args.infer_root, tid)
            if not model2path:
                print(f"[WARN] infer_all=1 found no *_task{tid}.json files under {args.infer_root}; skipping task{tid}")
                continue
            print(f"[INFO] task{tid}: infer_all found {len(model2path)} models:")
            for mt, pth in list(model2path.items())[:50]:
                print(f" - {mt} => {pth}")
            if len(model2path) > 50:
                print(f"... (showing 50 / {len(model2path)})")

            for model_tag, infer_path in model2path.items():
                await run_one_task(
                    tid=tid,
                    mode=args.mode,
                    infer_model_tag=model_tag,
                    infer_root=args.infer_root,
                    max_num=args.max_num,
                    subset_pids=subset_pids,
                    infer_json_path_override=infer_path,
                    run_ts=run_ts,
                    metrics_output_dir=metrics_output_dir,
                    subset_csv_path=subset_csv_path,
                    judge_backend=judge_backend,
                    judge_model=judge_model,
                    judge_ensemble_tag=JUDGE_ENSEMBLE_TAG,
                )
        else:
            await run_one_task(
                tid=tid,
                mode=args.mode,
                infer_model_tag=args.infer_model_tag,
                infer_root=args.infer_root,
                max_num=args.max_num,
                subset_pids=subset_pids,
                run_ts=run_ts,
                metrics_output_dir=metrics_output_dir,
                subset_csv_path=subset_csv_path,
                judge_backend=judge_backend,
                judge_model=judge_model,
                judge_ensemble_tag=JUDGE_ENSEMBLE_TAG,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate rubrics, run judges, and score ORACLE task outputs.")
    parser.add_argument("--tasks", type=str, default="10", help="Comma-separated task IDs, for example: 5,6,10")
    parser.add_argument("--mode", type=str, default="score", choices=["criteria", "judge", "score", "all"])
    parser.add_argument("--infer-model-tag", type=str, default=DEFAULT_INFER_MODEL_TAG)
    parser.add_argument("--infer-root", type=str, default=DEFAULT_INFER_ROOT)
    parser.add_argument(
        "--infer-all",
        action="store_true",
        help="Discover *_task{tid}.json files under --infer-root and judge or score every model tag."
    )
    parser.add_argument("--max-num", type=int, default=-1)
    parser.add_argument("--subset-test-ids-csv", type=str, default="")
    parser.add_argument("--api-backend", type=str, default="local", choices=["local", "openai"])
    parser.add_argument("--eval-model", type=str, default="")
    parser.add_argument("--openai-base-url", type=str, default="")
    parser.add_argument(
        "--resume-skip",
        type=str,
        default="valid",
        choices=["any", "valid"],
        help="mode=judge resume behavior: any skips any existing record; valid skips records with valid categories"
    )
    parser.add_argument(
        "--resume-any-ensemble",
        action="store_true",
        help="Resume from any existing judgement file for the same model tag, regardless of ensemble tag."
    )
    parser.add_argument(
        "--resume-match-judge-specs",
        action="store_true",
        default=True,
        help="Skip existing judgements when judge specifications match by model (default)."
    )
    parser.add_argument(
        "--no-resume-match-judge-specs",
        action="store_false",
        dest="resume_match_judge_specs",
        help="Disable judge-specification matching during judgement resume."
    )

    parser.add_argument(
        "--judge-specs",
        type=str,
        default="",
        help=(
            "Comma-separated judge specifications, for example: "
            "local:modelA,local@http://localhost:8888/v1/:modelB,openai:gpt-4o-mini,openai@https://api.openai.com/v1/:gpt-4o"
        )
    )

    parser.add_argument(
        "--judge-models",
        type=str,
        default="",
        help="Comma-separated judge model names for the selected backend. Ignored when --judge-specs is set."
    )

    parser.add_argument(
        "--metrics-output-dir",
        dest="metrics_output_dir",
        type=str,
        default="",
        help="Directory for score outputs; default is META_ROOT/metric_outputs."
    )

    # Score from a selected judgement file.
    parser.add_argument(
        "--list-score-judgements",
        action="store_true",
        help="List available judgement files for each task and model tag, then exit."
    )

    parser.add_argument(
        "--score-judgement-index",
        type=int,
        default=0,
        help="Select a judgement file for scoring by 1-based index when --infer-all is enabled."
    )

    parser.add_argument(
        "--score-judgement-tag",
        type=str,
        default="",
        help="Select a judgement file for scoring by ensemble tag when --infer-all is enabled."
    )

    parser.add_argument(
        "--score-judgement-file",
        type=str,
        default="",
        help="Select a specific judgement JSON file for scoring. Do not combine with --infer-all."
    )

    args = parser.parse_args()
    asyncio.run(main(args))
