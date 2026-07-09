#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 requests 库的批量推理脚本
参考 test.py 的调用方式，使用简单的 requests POST 请求
"""

import os
import json
import argparse
import time
import requests
import threading
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ========================= 默认配置 =========================
DEFAULT_MODEL_NAME = "gpt-4"
DEFAULT_MAX_WORKERS = 20
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_TIMEOUT_SECS = 300
DEFAULT_MAX_RETRIES = 3


def ensure_dir(p: str):
    """确保目录存在"""
    os.makedirs(p, exist_ok=True)


def atomic_write_json(path: str, obj: Any, lock: threading.Lock):
    """原子写入 JSON 文件（带锁保护）"""
    with lock:
        parent = os.path.dirname(path)
        if parent:
            ensure_dir(parent)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def append_error_log(path: str, record: Dict[str, Any], lock: threading.Lock):
    """追加错误日志（带锁保护）"""
    with lock:
        parent = os.path.dirname(path)
        if parent:
            ensure_dir(parent)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_input_items(input_path: str) -> List[Dict[str, Any]]:
    """
    加载输入文件，支持：
      - 单个 .json 文件（对象或对象列表）
      - 单个 .jsonl 文件（每行一个对象）
      - 目录（递归扫描 .json / .jsonl）
    """
    items = []
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
                            items.append(item)
                    except Exception:
                        continue
        else:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                items.append(data)
            elif isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict):
                        items.append(obj)

    return items


def get_last_human_prompt(conversation_obj: Dict[str, Any]) -> Optional[str]:
    """提取最后一条 human 消息作为 prompt"""
    convs = conversation_obj.get("conversations", [])
    last_human = None
    for m in convs:
        if m.get("from") == "human":
            last_human = m.get("value", "")
    return last_human


def call_api(
    prompt: str,
    url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout: int,
) -> str:
    """
    使用 requests 调用 OpenAI 兼容 API
    参考 test.py 的调用方式
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=timeout
    )

    response.raise_for_status()
    result = response.json()

    # 提取返回内容
    content = result["choices"][0]["message"]["content"]

    # 处理返回值：如果是字典且包含 text 字段，则提取 text；否则直接使用
    if isinstance(content, dict) and "text" in content:
        return content["text"]
    else:
        return content


def call_with_retry(
    prompt: str,
    url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout: int,
    max_retries: int,
) -> str:
    """带重试的 API 调用"""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            return call_api(
                prompt, url, model_name, api_key,
                temperature, top_p, max_tokens, timeout
            )
        except Exception as e:
            last_err = e
            if attempt >= max_retries:
                break
            # 指数退避
            backoff = min(2 ** (attempt - 1), 60)
            time.sleep(backoff)

    raise last_err if last_err else RuntimeError("unknown error")


def process_one_item(
    item: Dict[str, Any],
    url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout: int,
    max_retries: int,
    results_list: List[Dict[str, Any]],
    out_json_path: str,
    err_log_path: Optional[str],
    write_lock: threading.Lock,
    err_lock: threading.Lock,
) -> str:
    """
    处理单个样本，实时写入结果
    返回: "ok"|"error"|"no_human"
    """
    cid = item.get("id", "")
    prompt = get_last_human_prompt(item)

    if not prompt:
        if err_log_path:
            append_error_log(
                err_log_path,
                {"id": cid or "NO_ID", "error": "no human message found", "ts": int(time.time())},
                err_lock
            )
        return "no_human"

    try:
        answer = call_with_retry(
            prompt, url, model_name, api_key,
            temperature, top_p, max_tokens, timeout, max_retries
        )

        # 组装新条目
        new_item = dict(item)
        new_item.setdefault("conversations", [])
        new_item["conversations"] = list(new_item["conversations"]) + [
            {"from": model_name, "value": answer}
        ]

        # 实时写入：追加到列表并原子落盘
        results_list.append(new_item)
        atomic_write_json(out_json_path, results_list, write_lock)

        return "ok"

    except Exception as e:
        if err_log_path:
            append_error_log(
                err_log_path,
                {"id": cid or "NO_ID", "model": model_name, "error": repr(e), "ts": int(time.time())},
                err_lock
            )
        return "error"


def process_batch(
    input_path: str,
    out_json_path: str,
    err_log_path: Optional[str],
    url: str,
    model_name: str,
    api_key: str,
    max_workers: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout: int,
    max_retries: int,
):
    """
    批量处理样本，实时写入结果
    """
    print(f"\n========== 开始处理 input: {input_path} ==========")
    print(f"输出文件: {out_json_path}")
    if err_log_path:
        print(f"错误日志: {err_log_path}")

    # 加载输入
    items = load_input_items(input_path)
    print(f"[INFO] 加载了 {len(items)} 条样本")

    if not items:
        print("[WARN] 没有找到可处理的样本")
        return

    # 加载已有结果（断点续跑）
    processed_ids = set()
    results = []

    if os.path.exists(out_json_path):
        try:
            with open(out_json_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            if isinstance(results, list):
                for obj in results:
                    item_id = obj.get("id", "")
                    if item_id:
                        processed_ids.add(item_id)
            print(f"[INFO] 断点续跑：已加载 {len(results)} 条历史结果")
        except Exception as e:
            print(f"[WARN] 读取已存在的输出文件失败，将重新开始：{e}")
            results = []

    # 过滤已处理的样本
    items_to_process = []
    for item in items:
        item_id = item.get("id", "")
        if item_id and item_id in processed_ids:
            continue
        items_to_process.append(item)

    skipped = len(items) - len(items_to_process)
    if skipped > 0:
        print(f"[INFO] 跳过已处理样本 {skipped} 条")

    if not items_to_process:
        print("[INFO] 所有样本均已处理完成")
        return

    print(f"[INFO] 待处理样本数: {len(items_to_process)}")

    # 创建锁
    write_lock = threading.Lock()
    err_lock = threading.Lock()

    # 多线程处理，每个任务完成后立即写入
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_one_item,
                item, url, model_name, api_key,
                temperature, top_p, max_tokens, timeout, max_retries,
                results, out_json_path, err_log_path, write_lock, err_lock
            ): item
            for item in items_to_process
        }

        with tqdm(total=len(futures), desc="Processing", ncols=100) as pbar:
            for future in as_completed(futures):
                try:
                    status = future.result()
                    # 状态已经由 process_one_item 处理并写入
                except Exception as e:
                    print(f"\n[ERROR] 未预期的异常: {e}")
                finally:
                    pbar.update(1)

    print(f"[DONE] 处理完成，共 {len(results)} 条结果")


def main():
    parser = argparse.ArgumentParser(
        description="基于 requests 的批量推理脚本（参考 test.py 调用方式）"
    )

    # 单任务模式
    parser.add_argument(
        "--input",
        required=False,
        default="/path/to/orthopilot/gen_validation/test_final/test_subset/task6.json",
        help="输入文件或目录"
    )
    parser.add_argument(
        "--out_json",
        required=False,
        help="输出 JSON 文件路径"
    )
    parser.add_argument(
        "--err_log",
        required=False,
        help="错误日志 JSONL 路径"
    )

    # 多任务模式
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="任务编号，逗号分隔，例如: 1,2,3,4"
    )
    parser.add_argument(
        "--input-template",
        type=str,
        default="/path/to/orthopilot/gen_validation/test_final/test_subset/task{task}.json",
        help="输入文件模板，支持占位符 {task} 和 {model}"
    )
    parser.add_argument(
        "--out-json-template",
        type=str,
        default="/path/to/orthopilot/gen_validation/result/{model}_task{task}.json",
        help="输出 JSON 模板"
    )
    parser.add_argument(
        "--err-log-template",
        type=str,
        default="/path/to/orthopilot/gen_validation/result/{model}_task{task}_error.jsonl",
        help="错误日志模板"
    )

    # API 参数
    parser.add_argument(
        "--url",
        default="http://YOUR_HOST:YOUR_PORT",
        help="API 端点 URL"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help="模型名称"
    )
    parser.add_argument(
        "--api_key",
        default="",
        help="API Key（也可使用环境变量 OPENAI_API_KEY）"
    )

    # 推理参数
    parser.add_argument("--max_workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECS)
    parser.add_argument("--max_retries", type=int, default=DEFAULT_MAX_RETRIES)

    args = parser.parse_args()

    # 获取 API Key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("[ERROR] 必须提供 API Key（通过 --api_key 或环境变量 OPENAI_API_KEY）")
        return

    # 多任务模式
    if args.tasks.strip():
        task_ids = []
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
            print("[ERROR] 任务列表为空")
            return

        print(f"[INFO] 将依次处理任务: {task_ids}")

        for tid in task_ids:
            input_path = args.input_template.format(task=tid, model=args.model)
            out_json_path = args.out_json_template.format(task=tid, model=args.model)
            err_log_path = (
                args.err_log_template.format(task=tid, model=args.model)
                if args.err_log_template else None
            )

            process_batch(
                input_path=input_path,
                out_json_path=out_json_path,
                err_log_path=err_log_path,
                url=args.url,
                model_name=args.model,
                api_key=api_key,
                max_workers=args.max_workers,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
                max_retries=args.max_retries,
            )
    else:
        # 单任务模式
        out_json = args.out_json or f"/path/to/orthopilot/gen_validation/result/{args.model}_result.json"

        process_batch(
            input_path=args.input,
            out_json_path=out_json,
            err_log_path=args.err_log,
            url=args.url,
            model_name=args.model,
            api_key=api_key,
            max_workers=args.max_workers,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )


if __name__ == "__main__":
    main()
