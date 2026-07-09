#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluation utilities for open-response, choice and yes/no tasks.

The script computes lexical metrics such as BLEU and ROUGE, optional
embedding-based similarity, and optional LLM-based equivalence judgements.
Set Azure/OpenAI credentials through environment variables before use.
"""
from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
import jieba

import asyncio
import numpy as np
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from openai import AsyncAzureOpenAI
# ----- Azure OpenAI -----
AZURE_API_KEY        = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_ENDPOINT       = os.getenv("AZURE_OPENAI_ENDPOINT", "https://api.openai.com/v1")
AZURE_API_VERSION    = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
Azure_MODEL          = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
OPENAI_CONCURRENCY=8
client = AsyncAzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION
)

CHOICE_PROMPT = """
Judge whether the model answer is correct. Return yes or no only.
Reference Reference answer: {gt}
Model Reference answer: {pred}
"""

YN_PROMPT = """
Judge with yes or no only. Do not add extra text.
- answer yes, model answer yes: YES;
- answer no, model answer no: YES;
- answer yes, model answer no: NO;
- answer no, model answer yes: NO;
Reference answer: {gt}
Model Reference answer: {pred}
"""


async def is_semantically_equal(gt: str, pred: str, q_type: str) -> bool:
    """Return whether an LLM judge marks two answers as equivalent."""
    if q_type == "choice":
        prompt = CHOICE_PROMPT.format(gt=gt, pred=pred)
    elif q_type == "judgement":
        prompt = YN_PROMPT.format(gt=gt, pred=pred)

    try:
        resp = await client.chat.completions.create(
            model=Azure_MODEL,
            messages=[{"role": "user",
                       "content": prompt.format(gt=gt, pred=pred)}],
        )
        ans = resp.choices[0].message.content.strip().upper()
        # print(prompt)
        # print(ans)
        # print("--------------------")
        return ans.startswith("Y")
    except Exception as e:
        #
        print("[LLM judge error]:", e)
        return gt.strip() == pred.strip()


async def batch_sem_judge(triples: List[Tuple[str, str, str]]) -> List[bool]:
    """
 triples: [(gt, pred, q_type),...]
 """
    sem = asyncio.Semaphore(OPENAI_CONCURRENCY)

    async def _one(t):
        gt, pred, qt = t
        async with sem:
            return await is_semantically_equal(gt, pred, qt)

    return await asyncio.gather(*[_one(t) for t in triples])


# ---------------- Task 1-4 open diagnosis tasks ----------------
DIAG_TASKS = {"task1", "task2", "task3", "task4"}

DIAG_PROMPT = """
You are a clinician. Judge whether the model output matches the reference answer. Return yes or no only.
Reference answer: {gold}
Model output: {pred}
"""

async def is_diag_equal(gt: str, pred: str) -> bool:
    """Return whether a clinician-style judge marks two diagnosis answers as equivalent."""
    try:
        resp = await client.chat.completions.create(
            model=Azure_MODEL,
            messages=[{"role": "system", "content": "You are a clinician. Judge with yes or no."},
                {"role": "user",
                       "content": DIAG_PROMPT.format(gold=gt, pred=pred)}],
            temperature=0
        )
        ans = (resp.choices[0].message.content or "").strip().upper()
        return ans.startswith("yes") or ans.startswith("Y")
    except Exception as e:
        print("[diagnosis judge error]:", e)
        return gt.strip() == pred.strip()

async def batch_diag_judge(pairs: List[Tuple[str, str]]) -> List[bool]:
    sem = asyncio.Semaphore(OPENAI_CONCURRENCY)
    async def _one(p):
        async with sem:
            return await is_diag_equal(*p)
    return await asyncio.gather(*[_one(p) for p in pairs])


def zh_tokenize(text: str) -> List[str]:
    text = text.replace("\n", "").replace("\t", "").strip()
    # jieba
    words = jieba.lcut(text, cut_all=False)
    return [w for w in words if w.strip()]


# ---------- BERTScore ----------
try:
    from bert_score import score as bert_score
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    print("[warning] bert_score, BERTScore 0.0")

# ---------- NLP ----------
NLTK_DIR = os.getenv("NLTK_DATA", "./nltk_data")
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", download_dir=NLTK_DIR)
    nltk.data.path.append(os.path.abspath(NLTK_DIR))

_smoother = SmoothingFunction().method1
_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)

# ---------- ----------
BLEU_WEIGHTS = {
    1: (1.0, ),
    2: (0.5, 0.5),
    3: (1/3, 1/3, 1/3),
    4: (0.25, 0.25, 0.25, 0.25)
}

re_zh = re.compile(r"[\u4e00-\u9fa5]")

def compute_all_metrics(ref: str, hyp: str) -> Tuple[float, float, float, float, float, float, float]:
    """ 7: ROUGE_L, BLEU1-4, Cosine, BERTScore_F1(all)"""
    if not ref or not hyp:
        return (0.0,) * 7

    # ()
    tok_ref = zh_tokenize(ref)
    tok_hyp = zh_tokenize(hyp)

    # ------------- ROUGE-L(result) -------------
    try:
        rouge = _scorer.score(" ".join(tok_ref), " ".join(tok_hyp))["rougeL"].fmeasure
    except Exception:
        rouge = 0.0

    # ------------- BLEU 1-4(token) -------------
    bleu_vals = []
    for n in (1, 2, 3, 4):
        try:
            bleu_n = sentence_bleu(
                [tok_ref],
                tok_hyp,
                weights=BLEU_WEIGHTS[n],
                smoothing_function=_smoother
            )
        except Exception:
            bleu_n = 0.0
        bleu_vals.append(bleu_n)

    # ------------- TF-IDF (vectorizer) -------------
    try:
        vec = TfidfVectorizer(
            tokenizer=lambda txt: jieba.lcut(txt, cut_all=False),
            lowercase=False,token_pattern=None
        ).fit_transform([ref, hyp])
        cosine_val = cosine_similarity(vec[0:1], vec[1:2])[0][0]
    except ValueError:
        cosine_val = 0.0

    # ------------- BERTScore() -------------
    if BERT_AVAILABLE:
        try:
            P, R, F1 = bert_score(
                [hyp], [ref],
                lang="zh",
                rescale_with_baseline=True,
                model_type="bert-base-chinese"
            )
            bert_f1 = F1.item()
        except Exception:
            bert_f1 = 0.0
    else:
        bert_f1 = 0.0

    return (rouge, *bleu_vals, cosine_val, bert_f1)


# ---------- & JSON ----------
LETTER_RE = re.compile(r"^[A-Za-z]$")
def is_yes_or_no(txt: str) -> bool:
    first = txt.lstrip()[:1]          #
    return first in {"yes", "no"}

def is_no(txt: str) -> bool:
    for pattern in {"no",
        '',
        '',
        '',
        '',
        ''}:
        if pattern in txt:
            return True
    return False

def strip_think(txt: str) -> str:
    if "</think>" in txt:
        txt = txt.split("</think>")[-1]
    return txt.strip()

# ------------- (model tag)-------------
PRED_ROLES = {
    "qwen3", "gpt-4.1", "internlm3-8b",
    "Llama-3.1-8B", "Llama-3.1-70B", "HuatuoGPT-o1-8B", "Lingshu-7B","MedReason-8B","kimi-k2","llama-4-scout","gemini-2.5-flash-nothinking","deepseek-r1","llama-3.1-70b-instruct","HuatuoGPT-o1-7B","II-Medical-8B-1706","Baichuan2-13B-Chat","o3-mini","gpt-4o","gpt-5","o3-mini"
}

def extract_gt_pred(msgs: List[dict]) -> Tuple[str, str]:
    """ PRED_ROLES, assistant GT"""
    pred = gt = ""
    for i in range(len(msgs) - 1, -1, -1):
        role = msgs[i].get("role", "")
        content = strip_think(msgs[i].get("value") or msgs[i].get("content", ""))
        if not pred and role in PRED_ROLES:
            pred = content
            continue
        if pred and role in {"assistant", "assistant_gt"}:
            gt = content
            break
    if not gt and len(msgs) >= 2:
        gt = strip_think(msgs[-2].get("value") or msgs[-2].get("content", ""))
    return gt.strip(), pred.strip()


def pick_letter(txt: str) -> str:
    m = re.findall(r"[A-Za-z]", txt)
    return (m[-1] if m else "").lower()


def autodetect_type(q_type: str, gt: str, pred: str) -> str:
    if q_type in {"open", "choice", "judgement"}:
        return q_type
    if LETTER_RE.match(gt):
        return "choice"
    if is_yes_or_no(gt):
        return "judgement"
    return "open"

# ---------- evaluation ----------

def evaluate_files(files: List[Path]) -> Dict[str, dict]:
    """
 1. open: ROUGE/BLEU/BERTScore 7
 2. choice and judgement: all LLM answers should be yes or no
 - ->
 - -> error
 """
    res: Dict[str, dict] = {}

    # -- all (gt, pred), LLM --
    llm_pairs: List[Tuple[str, str]] = []     # (gt, pred)
    llm_meta:  List[Tuple[str, str]] = []     # (task_id, q_type)

        # 2 task1-4 open
    diag_pairs: List[Tuple[str, str]] = []       # [(gt, pred),...]
    diag_meta:  List[str] = []

    for fp in files:
        # task_id
        task_match = re.search(r"task_?(\d+)", fp.stem)
        task_id = f"task{task_match.group(1)}" if task_match else "unknown"

        # result
        if task_id not in res:
            res[task_id] = {
                "open_metrics": [],      # 7 (task1-4)
                "open_acc": [0, 0],      # [correct, total](task1-4)
                "choice": [0, 0],          # [correct, wrong]
                "judgement": [0, 0, 0, 0],    # [tt, tf, ft, ff]
            }

        #
        data = json.loads(fp.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]

        for rec in records:
            gt, pred = extract_gt_pred(rec.get("messages", []))
            q_type = autodetect_type(rec.get("type", ""), gt, pred)

            # --- open ---
            if q_type == "open":
                if task_id in {"task1", "task2", "task3", "task4"}:
                    diag_pairs.append((gt, pred))
                    diag_meta.append(task_id)
                else:
                    res[task_id]["open_metrics"].append(compute_all_metrics(gt, pred))
                continue

            # --- choice / judgement -> LLM ---
            if q_type in {"choice", "judgement"}:
                llm_pairs.append((gt, pred, q_type))
                llm_meta.append((task_id, q_type, gt))
                continue

    # -- LLM, --
    if llm_pairs:
        loop = asyncio.get_event_loop()
        ok_flags: List[bool] = loop.run_until_complete(batch_sem_judge(llm_pairs))

        for (task_id, q_type, gt_txt), ok in zip(llm_meta, ok_flags):
            if q_type == "choice":
                res[task_id]["choice"][0 if ok else 1] += 1
            else:
                gt_is_yes = not is_no(gt_txt.strip())
                if gt_is_yes and ok:
                    res[task_id]["judgement"][0] += 1
                elif gt_is_yes and not ok:
                    res[task_id]["judgement"][1] += 1
                elif (not gt_is_yes) and ok:
                    res[task_id]["judgement"][3] += 1
                else:
                    res[task_id]["judgement"][2] += 1

    # ----------: task1-4 open ----------
    if diag_pairs:
        ok_flags = asyncio.get_event_loop().run_until_complete(
            batch_diag_judge(diag_pairs))
        for task_id, ok in zip(diag_meta, ok_flags):
            res[task_id]["open_acc"][1] += 1
            if ok:
                res[task_id]["open_acc"][0] += 1

    return res

# ---------- & CSV ----------
OPEN_COLS = ["ROUGE_L", "BLEU1", "BLEU2",
             "BLEU3", "BLEU4", "Cosine", "BERT_F1"]

def _safe_div(num: float, den: float) -> float:
    return num / den if den else np.nan

def save_csv(stats: Dict[str, dict], out_csv: Path) -> None:
    rows = []
    for task, d in sorted(stats.items()):
        row: Dict[str, Union[str, int, float]] = {"Task": task}

        # ---------- open ----------
        correct, total = d["open_acc"]
        open_cnt = total if total else len(d["open_metrics"])
        row["open_cnt"] = open_cnt
        row["open_acc"] = _safe_div(correct, total)

        if d["open_metrics"]:
            arr = np.array(d["open_metrics"])
            for i, col in enumerate(OPEN_COLS):
                row[col] = arr[:, i].mean()
        else:
            for col in OPEN_COLS:
                row[col] = np.nan

        # ---------- choice ----------
        c, w = d["choice"]
        sel_tot = c + w
        row["choice_cnt"] = sel_tot
        row["choice_acc"] = _safe_div(c, sel_tot)

        # ---------- judgement ----------
        tt, tf, ft, ff = d["judgement"]      # TP, FN, FP, TN
        jud_tot = tt + tf + ft + ff
        row["judgement_cnt"] = jud_tot
        row["judgement_acc"] = _safe_div(tt + ff, jud_tot)

        # precision / recall / f1
        precision = _safe_div(tt, tt + ft)      # TP / (TP+FP)
        recall    = _safe_div(tt, tt + tf)      # TP / (TP+FN)
        f1 = (_safe_div(2 * precision * recall, precision + recall)
              if not np.isnan(precision) and not np.isnan(recall) else np.nan)

        row["judgement_precision"] = precision
        row["judgement_recall"]    = recall
        row["judgement_f1"]        = f1

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, float_format="%.4f")
    print(df.to_string(index=False, na_rep="-"))
    print("save ->", out_csv)


# ---------- CLI ----------
if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input_dir", default="data/storage")
    ap.add_argument("--output_csv", default="data/storage")
    args=ap.parse_args()
    files=sorted(Path(args.input_dir).rglob("*.infer.json"))
    if not files:
        raise FileNotFoundError(" infer.json file")
    stats=evaluate_files(files)
    save_csv(stats, Path(args.output_csv))
