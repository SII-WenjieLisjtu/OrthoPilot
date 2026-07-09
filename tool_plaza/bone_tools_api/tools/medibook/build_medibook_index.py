# -*- coding: utf-8 -*-
"""
build_medibook_index.py
 medibook (+ GPU/CPU)

:
- MEDIBOOK_DEVICE: "cuda:0" / "cuda:1" / "cpu"(default cpu)
- MEDIBOOK_INDEX_WORKERS: CPU worker (default 8; cpu)
- MEDIBOOK_INDEX_BATCH: encode (default 128; GPU 256/512)
"""

import os
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from multiprocessing import get_context
import numpy as np
from tqdm import tqdm

# ============== ==============
MODEL_NAME = "BAAI/bge-base-zh-v1.5"
QUERY_INSTR = "generate: "
USE_FP16 = True

DEVICE = os.getenv("MEDIBOOK_DEVICE", "cpu").strip().lower()   # "cuda:0" or "cpu"
NUM_WORKERS = int(os.getenv("MEDIBOOK_INDEX_WORKERS", "8"))    # cpu only
BATCH_SIZE = int(os.getenv("MEDIBOOK_INDEX_BATCH", "128"))

TOP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = TOP_DIR
BOOK_JSON = DATA_DIR / "data"/ "medibook"/"medical_books_content.json"
OUT_DIR = DATA_DIR / "medibook"/"index"

CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP = 120
# =================================


def normalize_text(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def split_paragraphs(text: str) -> List[str]:
    text = normalize_text(text)
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_paragraphs(paras: List[str], max_chars: int, overlap_chars: int) -> List[str]:
    chunks: List[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
            continue
        if len(buf) + 2 + len(p) <= max_chars:
            buf = buf + "\n\n" + p
        else:
            chunks.append(buf)
            if overlap_chars > 0:
                tail = buf[-overlap_chars:]
                buf = tail + "\n\n" + p
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def collect_keys_and_leaves(book: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    keys_meta = []
    leaves = []

    def dfs(node: Any, path: List[str]):
        if not isinstance(node, dict):
            return
        for k, v in node.items():
            p = path + [k]
            keys_meta.append({
                "key": k,
                "path": p,
                "path_str": " -> ".join(p),
            })
            if isinstance(v, dict):
                dfs(v, p)
            elif isinstance(v, str):
                leaves.append({
                    "path": p,
                    "path_str": " -> ".join(p),
                    "book_title": p[0] if p else "",
                    "text": v,
                })

    dfs(book, [])
    return keys_meta, leaves


# ---------------- encode: single-process (GPU/CPU) ----------------

def encode_texts_singleprocess(texts: List[str], batch_size: int, device: str) -> np.ndarray:
    """
 encode(GPU; CPU)
 """
    from FlagEmbedding import FlagAutoModel
    devs = [device] if device != "cpu" else ["cpu"]

    model = FlagAutoModel.from_finetuned(
        MODEL_NAME,
        query_instruction_for_retrieval=QUERY_INSTR,
        use_fp16=USE_FP16,
        devices=devs,
    )

    outs = []
    for i in tqdm(range(0, len(texts), batch_size), desc=f"Encoding ({device})", unit="batch"):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch)
        emb = np.asarray(emb)
        if emb.ndim == 1:
            emb = emb[np.newaxis, :]
        outs.append(emb)

    emb = np.concatenate(outs, axis=0).astype(np.float16)
    return emb


# ---------------- encode: multi-process (CPU only) ----------------

_worker_model = None

def _init_worker_cpu():
    global _worker_model
    from FlagEmbedding import FlagAutoModel
    _worker_model = FlagAutoModel.from_finetuned(
        MODEL_NAME,
        query_instruction_for_retrieval=QUERY_INSTR,
        use_fp16=USE_FP16,
        devices=["cpu"],
    )

def _encode_batch_cpu(texts: List[str]) -> np.ndarray:
    global _worker_model
    emb = _worker_model.encode(texts)
    emb = np.asarray(emb)
    if emb.ndim == 1:
        emb = emb[np.newaxis, :]
    return emb

def encode_texts_multiprocess_cpu(texts: List[str], num_workers: int, batch_size: int) -> np.ndarray:
    """
 CPU encode + tqdm (imap)
 """
    ctx = get_context("spawn")
    tasks = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    outs = []
    with ctx.Pool(processes=num_workers, initializer=_init_worker_cpu) as pool:
        for emb in tqdm(pool.imap(_encode_batch_cpu, tasks), total=len(tasks), desc=f"Encoding (cpu x{num_workers})", unit="batch"):
            outs.append(emb)

    emb = np.concatenate(outs, axis=0).astype(np.float16)
    return emb


def encode_texts(texts: List[str]) -> np.ndarray:
    """
:
 - GPU: ()
 - CPU: default(MEDIBOOK_INDEX_WORKERS)
 """
    if DEVICE.startswith("cuda"):
        # GPU:
        return encode_texts_singleprocess(texts, BATCH_SIZE, DEVICE)
    else:
        # CPU:
        return encode_texts_multiprocess_cpu(texts, NUM_WORKERS, BATCH_SIZE)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    book = json.load(open(BOOK_JSON, "r", encoding="utf-8"))
    keys_meta, leaves = collect_keys_and_leaves(book)

    # ---- keys ----
    for i, m in enumerate(keys_meta):
        m["kid"] = i
    keys_texts = [m["key"] for m in keys_meta]
    print(f"[Index] keys: {len(keys_texts)} | device={DEVICE} | batch={BATCH_SIZE}")

    keys_emb = encode_texts(keys_texts)
    np.save(OUT_DIR / "keys_emb.npy", keys_emb)
    with open(OUT_DIR / "keys_meta.jsonl", "w", encoding="utf-8") as f:
        for m in keys_meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    # ---- leaf chunks () ----
    chunks = []
    leaf_meta = []
    chunk_id = 0

    for leaf_id, lf in enumerate(tqdm(leaves, desc="Chunking leaves", unit="leaf")):
        text = normalize_text(lf["text"])
        paras = split_paragraphs(text)
        cks = chunk_paragraphs(paras, CHUNK_MAX_CHARS, CHUNK_OVERLAP)

        start = chunk_id
        for ck in cks:
            chunks.append({
                "chunk_id": chunk_id,
                "leaf_id": leaf_id,
                "chunk_text": ck,
            })
            chunk_id += 1

        leaf_meta.append({
            "leaf_id": leaf_id,
            "path": lf["path"],
            "path_str": lf["path_str"],
            "book_title": lf["book_title"],
            "chunk_start": start,
            "chunk_count": len(cks),
        })

    print(f"[Index] leaves: {len(leaves)}, chunks: {len(chunks)}")

    # ---- chunks embedding(: + GPU) ----
    chunk_texts = [c["chunk_text"] for c in chunks]
    chunks_emb = encode_texts(chunk_texts)
    np.save(OUT_DIR / "chunks_emb.npy", chunks_emb)

    with open(OUT_DIR / "leaf_meta.jsonl", "w", encoding="utf-8") as f:
        for m in leaf_meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    with open(OUT_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"[Done] index saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
