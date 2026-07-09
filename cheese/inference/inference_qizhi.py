# -*- coding: utf-8 -*-
import os
import json
import asyncio
import argparse
import time
import random
from typing import Any, Dict, Iterable, List, Optional

import httpx
from tqdm import tqdm

# ========================= 默认配置（可被命令行覆盖） =========================
DEFAULT_MODEL_NAME = "deepseek-r1-0528-ep"
DEFAULT_MAX_WORKERS = 50         # 可按后端能力调大/调小
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_TIMEOUT_SECS = 500       # 目标超时（外层再+5s硬超时）
DEFAULT_MAX_RETRIES = 3
JITTER_RANGE = (0.4, 1.2)        # 退避抖动
TASK = "7"

# httpx 请求缺省头
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# ========================= 文件 I/O 工具 =========================
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
    # 用线程把阻塞 IO 丢出去，避免卡住事件循环
    await asyncio.to_thread(_atomic_write_json, path, obj)

def _append_line(path: str, line: str):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

async def append_jsonl(path: str, rec: Dict[str, Any], lock: Optional[asyncio.Lock] = None):
    """仅用于错误日志；你若想彻底不产生日志文件，可不调用。"""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    if lock is None:
        await asyncio.to_thread(_append_line, path, line)
        return
    async with lock:
        await asyncio.to_thread(_append_line, path, line)

def iter_input_items(input_path: str) -> Iterable[Dict[str, Any]]:
    """
    支持：
      - 单个 .json 文件（对象或对象列表）
      - 单个 .jsonl 文件（每行一个对象）
      - 目录（递归扫描 .json / .jsonl）
    """
    paths = []
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

# ========================= HTTPX 异步请求封装（带硬超时与重试） =========================
async def call_model_once(
    prompt: str,
    model_name: str,
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict[str, str],
    timeout_secs: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> str:
    """
    单次模型调用：使用 httpx.AsyncClient 直接请求本地 OpenAI 兼容接口。
    """
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        # 若后端支持，可直接透传以下参数；不支持会被忽略
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": False,
    }

    async def _do_post() -> str:
        resp = await client.post(base_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""

    # 硬超时兜底
    return await asyncio.wait_for(_do_post(), timeout=timeout_secs + 5)

async def call_model_with_retry(
    prompt: str,
    model_name: str,
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict[str, str],
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
                prompt=prompt,
                model_name=model_name,
                client=client,
                base_url=base_url,
                headers=headers,
                timeout_secs=timeout_secs,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        except Exception as e:
            last_err = e
            if attempt >= max_retries:
                break
            backoff = (2 ** (attempt - 1)) + random.uniform(*JITTER_RANGE)
            await asyncio.sleep(backoff)
    raise last_err if last_err else RuntimeError("unknown error")

# ========================= 单条样本处理（聚合到一个 JSON 列表文件） =========================
async def process_one(
    item: Dict[str, Any],
    model_name: str,
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict[str, str],
    timeout_secs: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    max_retries: int,
    shared_out_list: List[Dict[str, Any]],
    shared_done_ids: set,
    out_json_path: str,
    write_lock: asyncio.Lock,
    err_log_path: Optional[str] = None,
):
    cid = item.get("id") or f"sample_{int(time.time()*1000)}"

    # 已完成则跳过（断点续跑：从 out_json 里恢复的 done_ids）
    if cid in shared_done_ids:
        return "skipped_done"

    prompt = get_last_human_prompt(item)
    if not prompt:
        if err_log_path:
            await append_jsonl(err_log_path, {"id": cid, "error": "no_human_message"}, write_lock)
        return "no_human"

    try:
        answer = await call_model_with_retry(
            prompt=prompt,
            model_name=model_name,
            client=client,
            base_url=base_url,
            headers=headers,
            timeout_secs=timeout_secs,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )

        # 组装新条目：在原条目基础上（深拷贝不必，浅复制+替换 value）
        new_item = dict(item)
        new_item.setdefault("conversations", [])
        new_item["conversations"] = list(new_item["conversations"]) + [
            {"from": model_name, "value": answer}
        ]

        # 加入聚合列表并原子落盘（需要锁以保证列表与文件一致性）
        async with write_lock:
            shared_out_list.append(new_item)
            shared_done_ids.add(cid)
            await atomic_write_json(out_json_path, shared_out_list)

        return "ok"

    except Exception as e:
        if err_log_path:
            await append_jsonl(
                err_log_path,
                {"id": cid, "model": model_name, "error": repr(e), "ts": int(time.time())},
                write_lock,
            )
        return "error"

# ========================= 主流程 =========================
async def main():
    parser = argparse.ArgumentParser(description="批量异步推理到单一 JSON（仅使用 human 作为 prompt）")
    parser.add_argument("--input", required=False,
                        default=f"/path/to/orthopilot/gen_validation/test_final/test_subset/task{TASK}.json",
                        help="输入：文件(.json/.jsonl)或目录")
    parser.add_argument("--out_json", required=False,
                        default=f"/path/to/orthopilot/gen_validation/result/{DEFAULT_MODEL_NAME}_task{TASK}.json",
                        help="输出单一 JSON 文件（列表）")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="模型名")
    parser.add_argument("--max_workers", type=int, default=DEFAULT_MAX_WORKERS, help="最大并发")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECS, help="单次调用超时秒")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS, help="最大生成token")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="温度")
    parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P, help="top_p")
    parser.add_argument(
        "--base_url",
        default="https://YOUR_LLM_API_BASE_URL",
        help="OpenAI 兼容服务 base_url",
    )
    parser.add_argument(
        "--api_key",
        default="",
        help="API Key（若本地服务无需鉴权，可留空）",
    )
    parser.add_argument(
        "--err_log",
        default=f"/path/to/orthopilot/gen_validation/result/{DEFAULT_MODEL_NAME}_task{TASK}_error.json",
        help="（可选）错误日志 JSONL 路径；若不想生成就留空",
    )
    args = parser.parse_args()

    model_name   = args.model
    max_workers  = args.max_workers
    timeout_secs = args.timeout
    max_tokens   = args.max_tokens
    temperature  = args.temperature
    top_p        = args.top_p

    # 组装 HTTP 头
    headers = dict(DEFAULT_HEADERS)
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    # 读取已有输出（断点续跑）：若 out_json 已存在，则加载并提取 done_ids
    shared_out_list: List[Dict[str, Any]] = []
    shared_done_ids: set = set()
    if os.path.exists(args.out_json):
        try:
            with open(args.out_json, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, list):
                shared_out_list = prev
                for obj in shared_out_list:
                    cid = obj.get("id")
                    if cid:
                        shared_done_ids.add(cid)
        except Exception:
            # 如果旧文件损坏，可在这里选择：报错或初始化为空
            pass
    
    # 读入全部待处理条目
    items: List[Dict[str, Any]] = list(iter_input_items(args.input))

    # 过滤掉已完成（出现在 out_json 里的 id）
    def not_done(it: Dict[str, Any]) -> bool:
        cid = it.get("id")
        if cid and cid in shared_done_ids:
            return False
        return True

    items = [it for it in items if not_done(it)]

    if not items:
        print("所有条目均已完成或无可处理样本。")
        return

    write_lock = asyncio.Lock()
    sem = asyncio.Semaphore(max_workers)

    async with httpx.AsyncClient(timeout=timeout_secs + 5) as client:

        async def _guarded(item: Dict[str, Any]):
            async with sem:
                return await process_one(
                    item=item,
                    model_name=model_name,
                    client=client,
                    base_url=args.base_url,
                    headers=headers,
                    timeout_secs=timeout_secs,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    max_retries=DEFAULT_MAX_RETRIES,
                    shared_out_list=shared_out_list,
                    shared_done_ids=shared_done_ids,
                    out_json_path=args.out_json,
                    write_lock=write_lock,
                    err_log_path=args.err_log,
                )

        tasks = [_guarded(it) for it in items]

        pbar = tqdm(total=len(tasks), desc="processing", ncols=100)
        for coro in asyncio.as_completed(tasks):
            try:
                _ = await coro
            finally:
                pbar.update(1)
        pbar.close()

if __name__ == "__main__":
    asyncio.run(main())
