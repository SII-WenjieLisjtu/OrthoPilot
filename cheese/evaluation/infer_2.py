#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
infer_bone_async.py
-------------------------------------------------
• 递归读取 JSON / JSONL 文件
• 本地 (lmdeploy) 或 OpenAI-API 并发推理
• tqdm 实时显示已推理 record 数

使用示例：
    # 本地推理
    python infer_bone_async.py

    # OpenAI 并发推理
    python infer_bone_async.py --openai
"""
import argparse
import json
import asyncio
import random
from pathlib import Path
from typing import Any, Optional, List, Tuple, Set

import torch
from tqdm import tqdm

# ───── 固定 OpenAI 配置 ─────
OPENAI_API_KEY  = "YOUR_API_KEY"     # ← 改成你的 key
OPENAI_BASE_URL = "http://YOUR_HOST:YOUR_PORT"            # ← 如无需自建代理可留空
OPENAI_MODEL    = "gpt-4o"
OPENAI_CONCURRENCY = 128   # 并发上限

# ───── Azure OpenAI 配置 ─────              
AZURE_API_KEY        = "ecd405968a14b5d2be8b6c9484599c9f"
AZURE_ENDPOINT       = "https://YOUR_LLM_API_BASE_URL"
AZURE_API_VERSION    = "2025-04-01-preview"    
Azure_MODEL          = "gpt-5"

# ───── 本地推理 (lmdeploy) ─────
from lmdeploy import (
    pipeline, ChatTemplateConfig, GenerationConfig, TurbomindEngineConfig
)

# ───── OpenAI 异步客户端 ─────
try:
    from openai import (
        AsyncOpenAI,      
        AsyncAzureOpenAI  
    )
    from openai import OpenAIError, InternalServerError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ---------- 1. 初始化本地模型 ----------
def init_local_model(model_path: str, gpu_ids: Optional[List[int]] = None):
    if gpu_ids is None:
        gpu_ids = list(range(torch.cuda.device_count()))

    backend_config = TurbomindEngineConfig(
        model_name=None,
        tp=len(gpu_ids),
        session_len=32768,
        cache_max_entry_count=0.9,
        max_batch_size=len(gpu_ids) * 16,
    )
    chat_config = ChatTemplateConfig(model_name="llama3_1")
    return pipeline(model_path, backend_config=backend_config,chat_template_config=chat_config)

async def _call_llm(
    client,
    semaphore: asyncio.Semaphore,
    messages: list,
    model_name: str,
    retry: int = 4,
    backoff_base: float = 1.6
):
    async with semaphore:
        for attempt in range(retry + 1):
            try:
                resp = await client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                )
                if not resp or not getattr(resp, "choices", None):
                    raise RuntimeError("Empty response or missing choices")
                choice = resp.choices[0]
                content = getattr(getattr(choice, "message", None), "content", None)
                if content is None:
                    fc = getattr(getattr(choice, "message", None), "function_call", None)
                    content = json.dumps(fc, ensure_ascii=False) if fc else ""
                return (content or "").strip()

            except InternalServerError:
                wait = (backoff_base ** attempt) + random.uniform(0, 0.3)
                print(f"[LLM] 500 错误，重试 {attempt+1}/{retry}，等待 {wait:.1f}s")
                await asyncio.sleep(wait)

            except OpenAIError as e:
                # 返回错误字符串而不是抛异常，避免取消其它任务
                return f"[ERROR] LLM API 错误: {e}"

            except Exception as e:
                if attempt >= retry:
                    return f"[ERROR] {type(e).__name__}: {e}"
                wait = (backoff_base ** attempt) + random.uniform(0, 0.3)
                print(f"[LLM] 异常 {type(e).__name__}，重试 {attempt+1}/{retry}，等待 {wait:.1f}s")
                await asyncio.sleep(wait)

        return "[ERROR] 超过最大重试次数，仍无法获取响应"
    


async def generate_with_openai_async(prompts: List[str]) -> List[str]:
    kwargs = {"api_key": OPENAI_API_KEY, "base_url": OPENAI_BASE_URL}
    client = AsyncOpenAI(**kwargs)
    semaphore = asyncio.Semaphore(OPENAI_CONCURRENCY)
    tasks = [
        asyncio.create_task(
            _call_llm(client, semaphore,
                      [{"role": "user", "content": p}], OPENAI_MODEL)
        ) for p in prompts
    ]
    return await asyncio.gather(*tasks)

async def generate_with_azure_async(prompts: List[str]) -> List[str]:
    async with AsyncAzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION
    ) as client:
        semaphore = asyncio.Semaphore(OPENAI_CONCURRENCY)
        tasks = [
            asyncio.create_task(
                _call_llm(client, semaphore, [{"role": "user", "content": p}], Azure_MODEL)
            ) for p in prompts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    outs: List[str] = []
    for r in results:
        outs.append(f"[ERROR] {type(r).__name__}: {r}" if isinstance(r, Exception) else r)
    return outs


# ---------- 3. 统一生成接口 ----------
def generate_responses(
    engine: Any,
    prompts: List[str],
    gen_cfg: GenerationConfig,
    mode: str,                       # "local" / "openai" / "azure"
) -> List[str]:
    if mode == "openai":
        return asyncio.run(generate_with_openai_async(prompts))
    if mode == "azure":           
        return asyncio.run(generate_with_azure_async(prompts))
    # local
    outs = engine(prompts, gen_config=gen_cfg)
    if not isinstance(outs, (list, tuple)):
        outs = [outs]
    return [o.text for o in outs]


# ---------- 4. JSON 工具 ----------
def get_last_user_prompt(obj: Any) -> Optional[str]:
    if isinstance(obj, list):
        for m in reversed(obj):
            if isinstance(m, dict) and m.get("role") == "user":
                return m.get("content")
        return None
    if isinstance(obj, dict) and 'messages' in obj:
        for m in reversed(obj['messages']):
            if m.get("role") == "user":
                return m.get("content")
    return None


def append_assistant_reply(obj: dict, reply: str):
    obj.setdefault("messages", []).append(
        {"role": "gpt-5", "content": reply}
    )

# ---------- 5. Flush 批处理 ----------
def flush_pool(
    pool: List[Tuple[Path, int, list, dict]],
    engine: Any,
    gen_cfg: GenerationConfig,
    output_dir: Path,
    input_dir: Path,
    mode: str,
):
    prompts = [get_last_user_prompt(conv) for _fp, _idx, _records, conv in pool]
    responses = generate_responses(engine, prompts, gen_cfg, mode)

    for (fp, idx, records, _), reply in zip(pool, responses):
        append_assistant_reply(records[idx], reply)

    written: Set[Path] = set()
    for fp, _, records, _ in pool:
        if fp in written:
            continue
        written.add(fp)
        rel = fp.relative_to(input_dir).with_suffix('.infer.json')
        out_fp = output_dir / rel
        out_fp.parent.mkdir(parents=True, exist_ok=True)
        with out_fp.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

# ---------- 6. 主流程 ----------
def main():
    parser = argparse.ArgumentParser()
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--openai", action="store_true", help="使用 OpenAI 并发推理")
    grp.add_argument("--azure",  action="store_true", help="使用 Azure OpenAI 并发推理")   # ✏️
    args = parser.parse_args()

    if args.openai:
        mode = "openai"
    elif args.azure:
        mode = "azure"
    else:
        mode = "local"

    # model_path = "/path/to/storage"
    # model_path="/path/to/storage"
    # model_path="/path/to/storage"
    model_path="data_generate_0819/post_process/final_json_v2/test/task3.json data_generate_0819/post_process/final_json_v2/test/task4.json"
    input_dir  = Path("data_generate_0819/post_process/final_json_v2/test/task3.json data_generate_0819/post_process/final_json_v2/test/task4.json")
    output_dir = Path("/path/to/storage")
    output_dir.mkdir(parents=True, exist_ok=True)

    gpu_ids = [0, 1, 2, 3, 4, 5, 6, 7]

    gen_cfg = GenerationConfig(max_new_tokens=4096, do_sample=False)
    engine = None if mode != "local" else init_local_model(model_path, gpu_ids)

    json_files = sorted(input_dir.rglob("*.json"))
    batch_size = OPENAI_CONCURRENCY if mode != "local" else len(gpu_ids) * 4

    pool: List[Tuple[Path, int, list, dict]] = []
    processed = 0
    pbar = tqdm(total=0, unit="record", desc="已推理")

    for fp in json_files:
        records_json = json.loads(fp.read_text(encoding="utf-8"))
        records = records_json if isinstance(records_json, list) else [records_json]
        for idx, conv in enumerate(records):
            if (prompt := get_last_user_prompt(conv)) is None:
                continue
            pool.append((fp, idx, records, conv))
            if len(pool) >= batch_size:
                flush_pool(pool, engine, gen_cfg, output_dir, input_dir, mode)
                processed += len(pool)
                pbar.update(len(pool))
                pool.clear()

    if pool:
        flush_pool(pool, engine, gen_cfg, output_dir, input_dir, mode)
        processed += len(pool)
        pbar.update(len(pool))

    pbar.close()
    print(f"\n全部完成：共 {processed} 条记录已推理并保存至 {output_dir}\n")

# ---------- 7. 入口 ----------
if __name__ == "__main__":
    main()
