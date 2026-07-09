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

# ========================= 默认配置（可被命令行覆盖） =========================
DEFAULT_MODEL_NAME = "deepseek-ai/DeepSeek-V3.1"
DEFAULT_MAX_WORKERS = 20         # 可按后端能力调大/调小
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_TIMEOUT_SECS = 500       # 目标超时（外层再+5s硬超时）
DEFAULT_MAX_RETRIES = 3
JITTER_RANGE = (0.4, 1.2)        # 退避抖动

# vLLM(OpenAI兼容) 默认建议显式传 max_tokens（很多 vLLM 服务端默认 max_tokens 较小）
# 仅当 backend=vllm 时开启，不影响你原来的远程 OpenAI-compat 服务行为
SEND_MAX_TOKENS = False


def normalize_openai_compat_base_url(base_url: str) -> str:
    """
    兼容：
      - http://YOUR_HOST:YOUR_PORT
      - http://YOUR_HOST:YOUR_PORT
      - http://YOUR_HOST:YOUR_PORT
      - http://YOUR_HOST:YOUR_PORT
    统一成：.../v1
    """
    u = (base_url or "").strip()
    if not u:
        return u
    u = u.rstrip("/")
    if not u.endswith("/v1"):
        u = u + "/v1"
    return u


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

# ========================= Case Key（用于跳过已处理 case） =========================
def make_case_key(cid: str, prompt: str) -> str:
    """
    用 (id + prompt) 生成稳定 key，避免同 id 不同 prompt 被误跳过。
    若 cid 为空，则退化为仅 prompt。
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
    从 item 推导 case_key（与实际推理用到的 prompt 一致：只取最后一条 human.value）。
    """
    prompt = get_last_human_prompt(item)
    if not prompt:
        return None
    cid = (item.get("id") or "").strip()
    return make_case_key(cid, prompt)

# ========================= OpenAI 请求封装（带硬超时与重试） =========================
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
    单次模型调用：仅传 user，不带 system。
    用 client.with_options(timeout=...)，再加 asyncio.wait_for 做硬超时兜底。
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
        # vLLM(OpenAI兼容) 本地服务：建议显式给 max_tokens，避免服务端默认值过小
        if SEND_MAX_TOKENS:
            payload["max_tokens"] = max_tokens

        resp = client_req.chat.completions.create(**payload)
        return resp.choices[0].message.content or ""

    # 硬超时：代理或SDK若未如期返回，强行中止这次等待
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

# ========================= 单条样本处理（聚合到一个 JSON 列表文件） =========================
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

    # 并发去重 + 断点续跑跳过：都用 case_key（而不是仅 id）
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

        # 处理返回值：如果是字典且包含 text 字段，则提取 text；否则直接使用
        if isinstance(answer, dict) and "text" in answer:
            answer_value = answer["text"]
        else:
            answer_value = answer

        # 组装新条目：在原条目基础上（浅复制+追加）
        new_item = dict(item)
        new_item.setdefault("conversations", [])
        new_item["conversations"] = list(new_item["conversations"]) + [
            {"from": model_name, "value": answer_value}
        ]

        # 加入聚合列表并原子落盘（需要锁以保证列表与文件一致性）
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

# ========================= 针对“一个输入文件/目录”的主逻辑 =========================
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
    print(f"\n========== 开始处理 input: {input_path} ==========")
    print(f"输出文件: {out_json_path}")
    if err_log_path:
        print(f"错误日志: {err_log_path}")

    # 读取已有输出（断点续跑）：若 out_json 已存在，则加载并提取 done_case_keys
    shared_out_list: List[Dict[str, Any]] = []
    shared_done_case_keys: Set[str] = set()
    inflight_case_keys: Set[str] = set()

    if os.path.exists(out_json_path):
        try:
            with open(out_json_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, list):
                shared_out_list = prev
                # 用 (id + last_human_prompt) 推导 done_case_keys
                for obj in shared_out_list:
                    k = extract_case_key_from_item(obj)
                    if k:
                        shared_done_case_keys.add(k)
            print(f"[INFO] 断点续跑：已加载 {len(shared_out_list)} 条历史结果，done_case_keys={len(shared_done_case_keys)}。")
        except Exception as e:
            print(f"[WARN] 读取已存在的输出文件失败，将重新开始：{e}")

    # 读入全部待处理条目
    items: List[Dict[str, Any]] = list(iter_input_items(input_path))

    # 过滤掉已完成（出现在 out_json 推导出的 case_key 里）
    filtered: List[Dict[str, Any]] = []
    skipped = 0
    no_human = 0
    for it in items:
        prompt = get_last_human_prompt(it)
        if not prompt:
            no_human += 1
            filtered.append(it)  # 仍交给 process_one 去记录 err_log / 返回 no_human
            continue
        cid = (it.get("id") or "").strip()
        k = make_case_key(cid, prompt)
        if k in shared_done_case_keys:
            skipped += 1
            continue
        filtered.append(it)

    items = filtered
    if skipped:
        print(f"[INFO] 预过滤：已跳过已完成 case {skipped} 条（按 case_key），无 human 的样本 {no_human} 条。")

    if not items:
        print("所有条目均已完成或无可处理样本。")
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

    print(f"[DONE] input={input_path} 处理完成，最终样本数={len(shared_out_list)}（done_case_keys={len(shared_done_case_keys)}）")

# ========================= 顶层主程序 =========================
async def main():
    parser = argparse.ArgumentParser(
        description="批量异步推理到单一 JSON（仅使用 human 作为 prompt），支持多任务列表；支持本地 vLLM(OpenAI兼容) 服务"
    )

    # 单任务模式下仍可用的参数
    parser.add_argument(
        "--input",
        required=False,
        default="/path/to/orthopilot/gen_validation/test_final/test_subset/task6.json",
        help="【单任务模式】输入：文件(.json/.jsonl)或目录；若提供 --tasks 则忽略此项"
    )
    parser.add_argument(
        "--out_json",
        required=False,
        default=f"/path/to/orthopilot/gen_validation/result/{DEFAULT_MODEL_NAME}_task6.json",
        help="【单任务模式】输出单一 JSON 文件（列表）；若提供 --tasks 则忽略此项"
    )
    parser.add_argument(
        "--err_log",
        required=False,
        default=f"/path/to/orthopilot/gen_validation/result/{DEFAULT_MODEL_NAME}_task6_error.json",
        help="【单任务模式】错误日志 JSONL 路径；若不想生成就留空；若提供 --tasks 则忽略此项"
    )

    # 多任务模式：使用模板生成路径
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="要处理的任务编号，逗号分隔，例如: 5,6,10；留空则只跑 --input / --out_json"
    )
    parser.add_argument(
        "--input-template",
        type=str,
        default="/path/to/orthopilot/gen_validation/test_final/test_subset/task{task}.json",
        help="【多任务模式】输入文件模板，支持占位符 {task} 和 {model}"
    )
    parser.add_argument(
        "--out-json-template",
        type=str,
        # 修正：原来是 //inspire...（双斜杠容易产生意外路径）
        default="/path/to/orthopilot/gen_validation/result/{model}_task{task}.json",
        help="【多任务模式】输出 JSON 模板，支持占位符 {task} 和 {model}"
    )
    parser.add_argument(
        "--err-log-template",
        type=str,
        default="/path/to/orthopilot/gen_validation/result/{model}_task{task}_error.json",
        help="【多任务模式】错误日志模板，支持占位符 {task} 和 {model}；留空则不记录错误日志"
    )

    # 模型与连接参数
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="模型名")

    # 新增：backend 选择（默认仍是 openai_compat，不影响你原来的用法）
    parser.add_argument(
        "--backend",
        choices=["openai_compat", "vllm"],
        default="openai_compat",
        help="后端类型：openai_compat=任意OpenAI兼容服务；vllm=集群本地vLLM(OpenAI兼容)服务"
    )

    parser.add_argument("--max_workers", type=int, default=DEFAULT_MAX_WORKERS, help="最大并发")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECS, help="单次调用超时秒")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS, help="最大生成token")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="温度")
    parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P, help="top_p")
    parser.add_argument(
        "--base_url",
        default="http://YOUR_HOST:YOUR_PORT",
        help="OpenAI 兼容服务 base_url；vLLM本地一般填 http://<ip>:<port> 或 http://<ip>:<port>/v1"
    )
    parser.add_argument(
        "--api_key",
        default="",
        help="API Key（建议用环境变量 OPENAI_API_KEY；或命令行 --api_key 传入；vLLM本地可留空）"
    )

    args = parser.parse_args()

    model_name   = args.model
    max_workers  = args.max_workers
    timeout_secs = args.timeout
    max_tokens   = args.max_tokens
    temperature  = args.temperature
    top_p        = args.top_p

    # vLLM 本地：默认显式传 max_tokens；其它后端保持你原来的行为
    global SEND_MAX_TOKENS
    SEND_MAX_TOKENS = (args.backend == "vllm")

    # 规范化 base_url（vLLM/OpenAI兼容服务常见写法差异）
    base_url = normalize_openai_compat_base_url(args.base_url)

    # vLLM 本地通常不校验 api_key，但 openai SDK 需要非空字符串
    api_key = (os.getenv("OPENAI_API_KEY", "") or args.api_key or "").strip()
    if not api_key:
        api_key = "EMPTY"

    # 初始化客户端
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    # ============ 判断是“多任务模式”还是“单任务模式” ============
    if args.tasks.strip():
        # 多任务模式：解析 task 列表
        task_ids: List[int] = []
        for x in args.tasks.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                task_ids.append(int(x))
            except ValueError:
                print(f"[WARN] 非法 task id: {x}，已忽略")
        task_ids = sorted(set(task_ids))

        if not task_ids:
            print("[ERROR] --tasks 提供的任务列表为空或非法，终止。")
            return

        print(f"[INFO] 将依次处理任务: {task_ids}")
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
        # 单任务模式：保持原有用法
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
