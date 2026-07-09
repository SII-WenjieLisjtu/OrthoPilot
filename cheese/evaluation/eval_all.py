#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评测脚本  - evaluate_bone_tasks.py  (BLEU‑1~4 ＋ BERTScore 版)
===============================================================
新增：
* **BLEU-1 / BLEU-2 / BLEU-3 / BLEU-4** 分别统计
* **BERTScore (F1)**
  * 自动检测语言：若参考文本包含中文字符，则 `lang='zh'`，否则默认英文
  * 依赖 `pip install bert_score`，若未安装则返回 0.0 并给出提示
Open 题指标列顺序：
```
ROUGE_L, BLEU1, BLEU2, BLEU3, BLEU4, Cosine, BERT_F1
```
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
# ───── Azure OpenAI 配置 ─────               
AZURE_API_KEY        = "b6d0c8453a36428abb63550487388a48"
AZURE_ENDPOINT       = "https://YOUR_LLM_API_BASE_URL"
AZURE_API_VERSION    = "2025-04-01-preview"    
Azure_MODEL          = "gpt-4o"
OPENAI_CONCURRENCY=8
client = AsyncAzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION
)

CHOICE_PROMPT = """
你是评分员。只需判断模型给出的选项字母是否与参考答案相同。
- 若相同，回答 YES；
- 否则回答 NO。
注意：忽略大小写、空格、标点，不考虑其它解释文字。
参考答案: {gt}
模型答案: {pred}
"""

YN_PROMPT = """
你是针对判断题回答是否正确的评分员,只需注意“是”或“否”等语气关键词，无需注意给出的其他语句。
- 若参考答案为是，模型答案也为是：回答 YES；
- 若参考答案为否，模型答案也为否：回答 YES；
- 若参考答案为是，模型答案为否：回答 NO；
- 若参考答案为否，模型答案为是：回答 NO；
参考答案: {gt}
模型答案: {pred}
"""


async def is_semantically_equal(gt: str, pred: str, q_type: str) -> bool:
    """调用 LLM 判断是否等价；返回 bool"""
    if q_type == "选择":
        prompt = CHOICE_PROMPT.format(gt=gt, pred=pred)
    elif q_type == "判断":
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
        # 出错时回退到严格字符串对比
        print("[LLM 判等] 调用失败，退回严格匹配：", e)
        return gt.strip() == pred.strip()


async def batch_sem_judge(triples: List[Tuple[str, str, str]]) -> List[bool]:
    """
    triples: [(gt, pred, q_type), ...]
    """
    sem = asyncio.Semaphore(OPENAI_CONCURRENCY)

    async def _one(t):
        gt, pred, qt = t
        async with sem:
            return await is_semantically_equal(gt, pred, qt)

    return await asyncio.gather(*[_one(t) for t in triples])


# ---------------- 针对 task1-4 开放题的医生判定 ----------------
DIAG_TASKS = {"task1", "task2", "task3", "task4"}

DIAG_PROMPT = """
你是专业医生，请判断以下模型输出是否与参考诊断一致，只回答是或否，不要其它内容:
参考诊断: {gold}
模型输出: {pred}
"""

async def is_diag_equal(gt: str, pred: str) -> bool:
    """医生 prompt 判等"""
    try:
        resp = await client.chat.completions.create(
            model=Azure_MODEL,
            messages=[{"role": "system", "content": "你是专业医生，擅长判断诊断是否一致。"},
                {"role": "user",
                       "content": DIAG_PROMPT.format(gold=gt, pred=pred)}],
            temperature=0
        )
        ans = (resp.choices[0].message.content or "").strip().upper()
        return ans.startswith("是") or ans.startswith("Y")
    except Exception as e:
        print("[DIAG 判等] 调用失败，退回严格匹配：", e)
        return gt.strip() == pred.strip()

async def batch_diag_judge(pairs: List[Tuple[str, str]]) -> List[bool]:
    sem = asyncio.Semaphore(OPENAI_CONCURRENCY)
    async def _one(p):
        async with sem:
            return await is_diag_equal(*p)
    return await asyncio.gather(*[_one(p) for p in pairs])


def zh_tokenize(text: str) -> List[str]:
    text = text.replace("\n", "").replace("\t", "").strip()
    # jieba 切词
    words = jieba.lcut(text, cut_all=False)
    return [w for w in words if w.strip()]


# ---------- 可选 BERTScore ----------
try:
    from bert_score import score as bert_score
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    print("[警告] 未安装 bert_score，BERTScore 将统一返回 0.0")

# ---------- NLP 工具 ----------
NLTK_DIR = os.getenv("NLTK_DATA", "./nltk_data")
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", download_dir=NLTK_DIR)
    nltk.data.path.append(os.path.abspath(NLTK_DIR))

_smoother = SmoothingFunction().method1
_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)

# ---------- 指标计算 ----------
BLEU_WEIGHTS = {
    1: (1.0, ),
    2: (0.5, 0.5),
    3: (1/3, 1/3, 1/3),
    4: (0.25, 0.25, 0.25, 0.25)
}

re_zh = re.compile(r"[\u4e00-\u9fa5]")

def compute_all_metrics(ref: str, hyp: str) -> Tuple[float, float, float, float, float, float, float]:
    """返回 7 项指标：ROUGE_L, BLEU1-4, Cosine, BERTScore_F1（全部走中文分词）"""
    if not ref or not hyp:
        return (0.0,) * 7

    # 分词（统一中文）
    tok_ref = zh_tokenize(ref)
    tok_hyp = zh_tokenize(hyp)

    # ------------- ROUGE-L（先用空格把分词结果重新拼回字符串） -------------
    try:
        rouge = _scorer.score(" ".join(tok_ref), " ".join(tok_hyp))["rougeL"].fmeasure
    except Exception:
        rouge = 0.0

    # ------------- BLEU 1-4（直接送 token 列表即可） -------------
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

    # ------------- TF-IDF 余弦相似度（vectorizer 自带分词器） -------------
    try:
        vec = TfidfVectorizer(
            tokenizer=lambda txt: jieba.lcut(txt, cut_all=False),
            lowercase=False,token_pattern=None
        ).fit_transform([ref, hyp])
        cosine_val = cosine_similarity(vec[0:1], vec[1:2])[0][0]
    except ValueError:
        cosine_val = 0.0

    # ------------- BERTScore（强制中文） -------------
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


# ---------- 题型自动判别 & JSON 工具 ----------
LETTER_RE = re.compile(r"^[A-Za-z]$")
def is_yes_or_no(txt: str) -> bool:
    first = txt.lstrip()[:1]          # 首个非空白字符
    return first in {"是", "否"}

def is_no(txt: str) -> bool:
    for pattern in {"否",
        '不建议',
        '不能进行',
        '暂缓手术',
        '推迟手术',
        '需满足以下条件'}:
        if pattern in txt:
            return True
    return False

def strip_think(txt: str) -> str:
    if "</think>" in txt:
        txt = txt.split("</think>")[-1]
    return txt.strip()

# ───────────── 角色白名单（所有可能的模型 tag）─────────────
PRED_ROLES = {
    "qwen3", "gpt-4.1", "internlm3-8b",
    "Llama-3.1-8B", "Llama-3.1-70B", "HuatuoGPT-o1-8B", "Lingshu-7B","MedReason-8B","kimi-k2","llama-4-scout","gemini-2.5-flash-nothinking","deepseek-r1","llama-3.1-70b-instruct","HuatuoGPT-o1-7B","II-Medical-8B-1706","Baichuan2-13B-Chat","o3-mini","gpt-4o","gpt-5","o3-mini"
}

def extract_gt_pred(msgs: List[dict]) -> Tuple[str, str]:
    """最后出现的 PRED_ROLES 视为预测，再往前遇到 assistant 当 GT"""
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
    if q_type in {"开放", "选择", "判断"}:
        return q_type
    if LETTER_RE.match(gt):
        return "选择"
    if is_yes_or_no(gt):
        return "判断"
    return "开放"

# ---------- 主评测 ----------

def evaluate_files(files: List[Path]) -> Dict[str, dict]:
    """
    1. 开放题：按 ROUGE/BLEU/BERTScore 计算 7 项指标
    2. 选择题 & 判断题：全部调用 LLM 判定 “候选答案” 是否与 “参考答案” 语义等价
         - 等价 → 记为正确
         - 不等价 → 记为错误
    """
    res: Dict[str, dict] = {}

    # —— 全部 (gt, pred) 对，留待一次性 LLM 调用 ——
    llm_pairs: List[Tuple[str, str]] = []     # (gt, pred)
    llm_meta:  List[Tuple[str, str]] = []     # (task_id, q_type)

        # ② task1-4 开放判等批次
    diag_pairs: List[Tuple[str, str]] = []       # [(gt, pred), ...]
    diag_meta:  List[str] = []        
  
    for fp in files:
        # 确定 task_id
        task_match = re.search(r"task_?(\d+)", fp.stem)
        task_id = f"task{task_match.group(1)}" if task_match else "unknown"

        # 初始化结果结构
        if task_id not in res:
            res[task_id] = {
                "开放_metrics": [],      # 7 指标列表（非 task1-4）
                "开放_acc": [0, 0],      # [correct, total]（仅 task1-4）
                "选择": [0, 0],          # [correct, wrong]
                "判断": [0, 0, 0, 0],    # [tt, tf, ft, ff]
            }

        # 读取记录
        data = json.loads(fp.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]

        for rec in records:
            gt, pred = extract_gt_pred(rec.get("messages", []))
            q_type = autodetect_type(rec.get("type", ""), gt, pred)

            # --- 开放题 ---
            if q_type == "开放":
                if task_id in {"task1", "task2", "task3", "task4"}:
                    diag_pairs.append((gt, pred))
                    diag_meta.append(task_id)
                else:
                    res[task_id]["开放_metrics"].append(compute_all_metrics(gt, pred))
                continue

            # --- 选择 / 判断 -> 暂存 LLM 判等 ---
            if q_type in {"选择", "判断"}:
                llm_pairs.append((gt, pred, q_type))
                llm_meta.append((task_id, q_type, gt))   
                continue

    # —— 统一 LLM 判等、回填计数 ——
    if llm_pairs:
        loop = asyncio.get_event_loop()
        ok_flags: List[bool] = loop.run_until_complete(batch_sem_judge(llm_pairs))

        for (task_id, q_type, gt_txt), ok in zip(llm_meta, ok_flags):
            if q_type == "选择":
                res[task_id]["选择"][0 if ok else 1] += 1
            else: 
                gt_is_yes = not is_no(gt_txt.strip())
                if gt_is_yes and ok:
                    res[task_id]["判断"][0] += 1      
                elif gt_is_yes and not ok:
                    res[task_id]["判断"][1] += 1     
                elif (not gt_is_yes) and ok:
                    res[task_id]["判断"][3] += 1     
                else:
                    res[task_id]["判断"][2] += 1      

    # ---------- 批量判等：task1-4 开放 ----------
    if diag_pairs:
        ok_flags = asyncio.get_event_loop().run_until_complete(
            batch_diag_judge(diag_pairs))
        for task_id, ok in zip(diag_meta, ok_flags):
            res[task_id]["开放_acc"][1] += 1          
            if ok:
                res[task_id]["开放_acc"][0] += 1     

    return res

# ---------- 汇总 & CSV ----------
OPEN_COLS = ["ROUGE_L", "BLEU1", "BLEU2",
             "BLEU3", "BLEU4", "Cosine", "BERT_F1"]

def _safe_div(num: float, den: float) -> float:
    return num / den if den else np.nan

def save_csv(stats: Dict[str, dict], out_csv: Path) -> None:
    rows = []
    for task, d in sorted(stats.items()):
        row: Dict[str, Union[str, int, float]] = {"Task": task}

        # ---------- 开放 ----------
        correct, total = d["开放_acc"]
        open_cnt = total if total else len(d["开放_metrics"])
        row["开放_cnt"] = open_cnt
        row["开放_acc"] = _safe_div(correct, total)

        if d["开放_metrics"]:
            arr = np.array(d["开放_metrics"])
            for i, col in enumerate(OPEN_COLS):
                row[col] = arr[:, i].mean()
        else:
            for col in OPEN_COLS:
                row[col] = np.nan

        # ---------- 选择 ----------
        c, w = d["选择"]
        sel_tot = c + w
        row["选择_cnt"] = sel_tot
        row["选择_acc"] = _safe_div(c, sel_tot)

        # ---------- 判断 ----------
        tt, tf, ft, ff = d["判断"]      # TP, FN, FP, TN
        jud_tot = tt + tf + ft + ff
        row["判断_cnt"] = jud_tot
        row["判断_acc"] = _safe_div(tt + ff, jud_tot)

        # 追加 precision / recall / f1
        precision = _safe_div(tt, tt + ft)      # TP / (TP+FP)
        recall    = _safe_div(tt, tt + tf)      # TP / (TP+FN)
        f1 = (_safe_div(2 * precision * recall, precision + recall)
              if not np.isnan(precision) and not np.isnan(recall) else np.nan)

        row["判断_precision"] = precision
        row["判断_recall"]    = recall
        row["判断_f1"]        = f1

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, float_format="%.4f")
    print(df.to_string(index=False, na_rep="-"))
    print("已保存 →", out_csv)


# ---------- CLI ----------
if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input_dir", default="/path/to/storage")
    ap.add_argument("--output_csv", default="/path/to/storage")
    args=ap.parse_args()
    files=sorted(Path(args.input_dir).rglob("*.infer.json"))
    if not files:
        raise FileNotFoundError("未找到 infer.json 文件")
    stats=evaluate_files(files)
    save_csv(stats, Path(args.output_csv))
