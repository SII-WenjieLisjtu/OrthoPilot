# -*- coding: utf-8 -*-
import os
import json
import asyncio
import argparse
import time
import random
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from openai import OpenAI  # pip install openai
from tqdm import tqdm

# ========================= default() =========================
DEFAULT_MODEL_NAME = "deepseek-ai/DeepSeek-V3.1"
DEFAULT_MAX_WORKERS = 20         # /
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_TIMEOUT_SECS = 500       # (+5s)
DEFAULT_MAX_RETRIES = 3
JITTER_RANGE = (0.4, 1.2)        #

# vLLM(OpenAI) default max_tokens(vLLM default max_tokens)
# backend=vllm, OpenAI-compat
SEND_MAX_TOKENS = False


def normalize_openai_compat_base_url(base_url: str) -> str:
    """
:
 - http://localhost:8000
 - http://localhost:8000
 - http://localhost:8000
 - http://localhost:8000
:.../v1
 """
    u = (base_url or "").strip()
    if not u:
        return u
    u = u.rstrip("/")
    if not u.endswith("/v1"):
        u = u + "/v1"
    return u


# ========================= file I/O =========================
def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _atomic_write_json(path: str, obj: Any):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

async def atomic_write_json(path: str, obj: Any):
    # IO,
    await asyncio.to_thread(_atomic_write_json, path, obj)

def _append_line(path: str, line: str):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

async def append_jsonl(path: str, rec: Dict[str, Any], lock: Optional[asyncio.Lock] = None):
    """error; file,."""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    if lock is None:
        await asyncio.to_thread(_append_line, path, line)
        return
    async with lock:
        await asyncio.to_thread(_append_line, path, line)

def iter_input_items(input_path: str) -> Iterable[Dict[str, Any]]:
    """
:
 - .json file
 -.jsonl file()
 - (.json /.jsonl)
 """
    paths: List[str] = []
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for fn in files:
                if fn.lower().endswith(".json") or fn.lower().endswith(".jsonl"):
                    paths.append(os.path.join(root, fn))
    else:
        paths.append(input_path)

    for p in paths:
        if p.lower().endswith(".jsonl"):
            with open(p, "r", encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        item = json.loads(ln)
                        if isinstance(item, dict):
                            yield item
                    except Exception:
                        continue
        else:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                yield data
            elif isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict):
                        yield obj

def get_last_human_prompt(conversation_obj: Dict[str, Any]) -> Optional[str]:
    convs = conversation_obj.get("conversations", [])
    last_human = None
    for m in convs:
        if m.get("from") == "human":
            last_human = m.get("value", "")
    return last_human

# ========================= Case Key(skip case) =========================
def make_case_key(cid: str, prompt: str) -> str:
    """
 (id + prompt) generate key, id prompt skip.
 cid is empty, prompt.
 """
    cid = (cid or "").strip()
    prompt = (prompt or "").strip()
    if not cid:
        base = f"PROMPT_ONLY\n{prompt}"
    else:
        base = f"{cid}\n{prompt}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def extract_case_key_from_item(item: Dict[str, Any]) -> Optional[str]:
    """
 item case_key(prompt: human.value).
 """
    prompt = get_last_human_prompt(item)
    if not prompt:
        return None
    cid = (item.get("id") or "").strip()
    return make_case_key(cid, prompt)

# ========================= OpenAI () =========================
async def call_model_once(
    prompt: str,
    model_name: str,
    client: OpenAI,
    timeout_secs: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> str:
    """
 model: user, system.
 client.with_options(timeout=...), asyncio.wait_for.
 """
    def _sync_call() -> str:
        client_req = client.with_options(timeout=timeout_secs, max_retries=0)

        payload = dict(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=top_p,
            stream=False,
        )
        # vLLM(OpenAI): max_tokens, default
        if SEND_MAX_TOKENS:
            payload["max_tokens"] = max_tokens

        resp = client_req.chat.completions.create(**payload)
        return resp.choices[0].message.content or ""

    #: SDK,
    return await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=timeout_secs + 5)

async def call_model_with_retry(
    prompt: str,
    model_name: str,
    client: OpenAI,
    timeout_secs: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return await call_model_once(
                prompt, model_name, client, timeout_secs, temperature, top_p, max_tokens
            )
        except Exception as e:
            last_err = e
            if attempt >= max_retries:
                break
            backoff = (2 ** (attempt - 1)) + random.uniform(*JITTER_RANGE)
            await asyncio.sleep(backoff)
    raise last_err if last_err else RuntimeError("unknown error")

# ========================= sample(JSON file) =========================
async def process_one(
    item: Dict[str, Any],
    model_name: str,
    client: OpenAI,
    timeout_secs: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    max_retries: int,
    shared_out_list: List[Dict[str, Any]],
    shared_done_case_keys: Set[str],
    inflight_case_keys: Set[str],
    out_json_path: str,
    write_lock: asyncio.Lock,
    err_log_path: Optional[str] = None,
):
    cid = (item.get("id") or "").strip()

    prompt = get_last_human_prompt(item)
    if not prompt:
        if err_log_path:
            await append_jsonl(err_log_path, {"id": cid or "NO_ID", "error": "no_human_message"}, write_lock)
        return "no_human"

    case_key = make_case_key(cid, prompt)

    # + skip: case_key(yes id)
    async with write_lock:
        if case_key in shared_done_case_keys:
            return "skipped_done"
        if case_key in inflight_case_keys:
            return "skipped_inflight"
        inflight_case_keys.add(case_key)

    try:
        answer = await call_model_with_retry(
            prompt, model_name, client, timeout_secs, temperature, top_p, max_tokens, max_retries
        )

        #: yes,; no
        if isinstance(answer, dict) and "answer" in answer:
            answer_value = answer["answer"]
        else:
            answer_value = answer

        #: (+)
        new_item = dict(item)
        new_item.setdefault("conversations", [])
        new_item["conversations"] = list(new_item["conversations"]) + [
            {"from": model_name, "value": answer_value}
        ]

        # (file)
        async with write_lock:
            shared_out_list.append(new_item)
            shared_done_case_keys.add(case_key)
            inflight_case_keys.discard(case_key)
            await atomic_write_json(out_json_path, shared_out_list)

        return "ok"

    except Exception as e:
        async with write_lock:
            inflight_case_keys.discard(case_key)
        if err_log_path:
            await append_jsonl(
                err_log_path,
                {"id": cid or "NO_ID", "model": model_name, "error": repr(e), "ts": int(time.time())},
                write_lock,
            )
        return "error"

# ========================= "input file/" =========================
async def run_for_one_input(
    input_path: str,
    out_json_path: str,
    err_log_path: Optional[str],
    model_name: str,
    client: OpenAI,
    max_workers: int,
    timeout_secs: int,
    max_tokens: int,
    temperature: float,
    top_p: float,
    max_retries: int,
):
    print(f"\n========== start processing input: {input_path} ==========")
    print(f"output file: {out_json_path}")
    if err_log_path:
        print(f"error log: {err_log_path}")

    # output(): out_json, load done_case_keys
    shared_out_list: List[Dict[str, Any]] = []
    shared_done_case_keys: Set[str] = set()
    inflight_case_keys: Set[str] = set()

    if os.path.exists(out_json_path):
        try:
            with open(out_json_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, list):
                shared_out_list = prev
                # (id + last_human_prompt) done_case_keys
                for obj in shared_out_list:
                    k = extract_case_key_from_item(obj)
                    if k:
                        shared_done_case_keys.add(k)
            print(f"[INFO] loaded {len(shared_out_list)} existing results, done_case_keys={len(shared_done_case_keys)}.")
        except Exception as e:
            print(f"[WARN] failed to read output file: {e}")

    # all
    items: List[Dict[str, Any]] = list(iter_input_items(input_path))

    # (out_json case_key)
    filtered: List[Dict[str, Any]] = []
    skipped = 0
    no_human = 0
    for it in items:
        prompt = get_last_human_prompt(it)
        if not prompt:
            no_human += 1
            filtered.append(it)  # process_one err_log / no_human
            continue
        cid = (it.get("id") or "").strip()
        k = make_case_key(cid, prompt)
        if k in shared_done_case_keys:
            skipped += 1
            continue
        filtered.append(it)

    items = filtered
    if skipped:
        print(f"[INFO] skipped {skipped} cases by case_key; no-human samples {no_human}.")

    if not items:
        print("No samples to process.")
        return

    write_lock = asyncio.Lock()
    sem = asyncio.Semaphore(max_workers)

    async def _guarded(item: Dict[str, Any]):
        async with sem:
            return await process_one(
                item=item,
                model_name=model_name,
                client=client,
                timeout_secs=timeout_secs,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                max_retries=max_retries,
                shared_out_list=shared_out_list,
                shared_done_case_keys=shared_done_case_keys,
                inflight_case_keys=inflight_case_keys,
                out_json_path=out_json_path,
                write_lock=write_lock,
                err_log_path=err_log_path,
            )

    tasks = [_guarded(it) for it in items]

    pbar = tqdm(total=len(tasks), desc="processing", ncols=100)
    for coro in asyncio.as_completed(tasks):
        try:
            _ = await coro
        finally:
            pbar.update(1)
    pbar.close()

    print(f"[DONE] input={input_path}; samples={len(shared_out_list)} (done_case_keys={len(shared_done_case_keys)})")

# ========================= =========================
async def main():
    parser = argparse.ArgumentParser(
        description="Run inference on JSON or JSONL task files with an OpenAI-compatible backend"
    )

    # task
    parser.add_argument(
        "--input",
        required=False,
        default="data/task6.json",
        help="input file for a single task (.json or .jsonl); use --tasks for batch mode"
    )
    parser.add_argument(
        "--out_json",
        required=False,
        default=f"outputs/{DEFAULT_MODEL_NAME}_task6.json",
        help="output JSON file for a single task; use --tasks for batch mode"
    )
    parser.add_argument(
        "--err_log",
        required=False,
        default=f"outputs/{DEFAULT_MODEL_NAME}_task6_error.json",
        help="error JSONL path for a single task; generated on failures; use --tasks for batch mode"
    )

    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="Comma-separated task IDs for batch mode, for example 5,6,10"
    )
    parser.add_argument(
        "--input-template",
        type=str,
        default="data/task{task}.json",
        help="Input path template for batch mode; supports {task} and {model}"
    )
    parser.add_argument(
        "--out-json-template",
        type=str,
        default="outputs/{model}_task{task}.json",
        help="Output JSON path template for batch mode; supports {task} and {model}"
    )
    parser.add_argument(
        "--err-log-template",
        type=str,
        default="outputs/{model}_task{task}_error.json",
        help="Error JSONL path template for batch mode; supports {task} and {model}"
    )

    # model
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="model")

    parser.add_argument(
        "--backend",
        choices=["openai_compat", "vllm"],
        default="openai_compat",
        help="Inference backend: openai_compat uses an OpenAI-compatible endpoint; vllm uses the vLLM endpoint"
    )

    parser.add_argument("--max_workers", type=int, default=DEFAULT_MAX_WORKERS, help="Maximum concurrent requests")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECS, help="Request timeout in seconds")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Maximum generated tokens")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Generation temperature")
    parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P, help="Nucleus sampling probability")
    parser.add_argument(
        "--base_url",
        default="http://localhost:8000",
        help="OpenAI base_url; vLLM http://<ip>:<port> http://<ip>:<port>/v1"
    )
    parser.add_argument(
        "--api_key",
        default="",
        help="API Key(OPENAI_API_KEY; --api_key; vLLM)"
    )

    args = parser.parse_args()

    model_name   = args.model
    max_workers  = args.max_workers
    timeout_secs = args.timeout
    max_tokens   = args.max_tokens
    temperature  = args.temperature
    top_p        = args.top_p

    # vLLM: default max_tokens;
    global SEND_MAX_TOKENS
    SEND_MAX_TOKENS = (args.backend == "vllm")

    # base_url(vLLM/OpenAI)
    base_url = normalize_openai_compat_base_url(args.base_url)

    # vLLM api_key, openai SDK
    api_key = (os.getenv("OPENAI_API_KEY", "") or args.api_key or "").strip()
    if not api_key:
        api_key = "EMPTY"

    #
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    # ============ judgementyes"task"yes"task" ============
    if args.tasks.strip():
        # task: task
        task_ids: List[int] = []
        for x in args.tasks.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                task_ids.append(int(x))
            except ValueError:
                print(f"[WARN] task id: {x}, ")
        task_ids = sorted(set(task_ids))

        if not task_ids:
            print("[ERROR] --tasks taskis empty,.")
            return

        print(f"[INFO] tasks: {task_ids}")
        for tid in task_ids:
            input_path = args.input_template.format(task=tid, model=model_name)
            out_json_path = args.out_json_template.format(task=tid, model=model_name)
            err_log_path = (
                args.err_log_template.format(task=tid, model=model_name)
                if args.err_log_template else None
            )

            await run_for_one_input(
                input_path=input_path,
                out_json_path=out_json_path,
                err_log_path=err_log_path,
                model_name=model_name,
                client=client,
                max_workers=max_workers,
                timeout_secs=timeout_secs,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                max_retries=DEFAULT_MAX_RETRIES,
            )
    else:
        # task:
        await run_for_one_input(
            input_path=args.input,
            out_json_path=args.out_json,
            err_log_path=args.err_log or None,
            model_name=model_name,
            client=client,
            max_workers=max_workers,
            timeout_secs=timeout_secs,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            max_retries=DEFAULT_MAX_RETRIES,
        )

if __name__ == "__main__":
    asyncio.run(main())
