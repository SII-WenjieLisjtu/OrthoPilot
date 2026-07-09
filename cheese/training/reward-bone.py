# -*- coding: utf-8 -*-
import re
import time
import math
import requests
from typing import Optional, Dict, Any

# =========================
# Config (edit here)
# =========================
JUDGE_API_URL = "https://YOUR_INTERNAL_API_URL"  # 改成你的
JUDGE_API_KEY = None  # 如需鉴权: "sk-xxx"
JUDGE_MODEL = "/path/to/models/Qwen2.5-72B-Instruct"  # 改成你的指令模型名

TIMEOUT_SEC = 30
MAX_RETRY = 3

# =========================
# Helpers
# =========================
THINK_TAIL_RE = re.compile(r"^\s*<think>.*?</think>(.+)$", flags=re.DOTALL | re.IGNORECASE)
CLOSED_GT_RE = re.compile(r"^[A-Z]$")  # 单个大写字母

def extract_after_think(text: str) -> Optional[str]:
    """Return content after </think>, stripped. If format invalid -> None."""
    if not isinstance(text, str):
        return None
    m = THINK_TAIL_RE.match(text)
    if not m:
        return None
    tail = (m.group(1) or "").strip()
    return tail if tail else None

def is_closed_gt(gt: str) -> bool:
    """Closed-form: single uppercase letter OR exactly 是/否."""
    if not isinstance(gt, str):
        return False
    gt = gt.strip()
    return bool(CLOSED_GT_RE.fullmatch(gt)) or gt in ("是", "否")

# =========================
# Length penalty (adaptive soft cap)
# =========================
CLOSED_CAP = 64
OPEN_CAP_MIN = 256
OPEN_CAP_MAX = 1024
OPEN_CAP_GT_MULT = 2.0   # 允许到 GT 的 2 倍不罚

LEN_TAU = 256            # 衰减速度
MIN_PENALTY = 0.2        # 下限

def adaptive_soft_cap(pred_tail: str, gt_tail: str) -> int:
    gt_tail = (gt_tail or "").strip()
    if is_closed_gt(gt_tail):
        return CLOSED_CAP
    gt_len = max(1, len(gt_tail))
    cap = int(OPEN_CAP_GT_MULT * gt_len)
    cap = max(OPEN_CAP_MIN, min(OPEN_CAP_MAX, cap))
    return cap

def length_penalty(pred_tail: str, gt_tail: str) -> float:
    pred = (pred_tail or "").strip()
    L = len(pred)
    cap = adaptive_soft_cap(pred, gt_tail)
    if L <= cap:
        return 1.0
    pen = math.exp(-float(L - cap) / float(max(1, LEN_TAU)))
    return max(MIN_PENALTY, float(pen))

# =========================
# HTTP
# =========================
def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if JUDGE_API_KEY:
        h["Authorization"] = f"Bearer {JUDGE_API_KEY}"
    return h

def _post(payload: dict) -> dict:
    last_err = None
    for i in range(MAX_RETRY):
        try:
            r = requests.post(JUDGE_API_URL, headers=_headers(), json=payload, timeout=TIMEOUT_SEC)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = str(e)
            time.sleep(0.5 * (i + 1))
    raise RuntimeError(f"Judge API failed: {last_err}")

def _get_content(resp: dict) -> str:
    return (resp.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()

# =========================
# Judge (lenient parsing)
# =========================
def judge_binary(pred: str, gt: str) -> float:
    """
    Return 1.0 if correct else 0.0
    Judge SHOULD output: yes or no (lenient parse)
    """
    system = (
        "You are a strict grader. Compare PREDICTION with GROUND TRUTH for correctness. "
        "Output exactly one token: yes or no. No punctuation, no explanation."
    )
    user = f"""GROUND TRUTH:
{gt}

PREDICTION:
{pred}

Is the prediction correct? Answer exactly: yes or no
"""
    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 4,  # 放宽一点，避免 yes\n 之类被截断
    }
    resp = _post(payload)
    out = _get_content(resp).lower().strip()

    # 宽松解析：yes/no 开头即可（允许 yes. / yes\n / YES）
    if out.startswith("yes"):
        return 1.0
    if out.startswith("no"):
        return 0.0
    return 0.0

def judge_ternary(pred: str, gt: str) -> float:
    """
    Return 1.0 / 0.5 / 0.0
    Judge SHOULD output: correct / partial / wrong (lenient parse)
    """
    system = (
        "You are a strict grader. Compare PREDICTION with GROUND TRUTH semantically. "
        "Output exactly one label from: correct, partial, wrong. "
        "No punctuation, no explanation."
    )
    user = f"""GROUND TRUTH:
{gt}

PREDICTION:
{pred}

Classify correctness:
- correct: fully correct
- partial: partially correct
- wrong: incorrect

Answer exactly one label: correct, partial, or wrong
"""
    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 4,
    }
    resp = _post(payload)
    out = _get_content(resp).lower().strip()

    # 宽松解析：label 开头即可（允许 correct. / partial\n）
    if out.startswith("correct"):
        return 1.0
    if out.startswith("partial"):
        return 0.5
    if out.startswith("wrong"):
        return 0.0
    return 0.0

def compute_score(
    data_source: str,
    solution_str: str,
    ground_truth: str,
    extra_info: Optional[Dict[str, Any]] = None
):
    """
    - format invalid => score=-1 (early stop)
    - otherwise:
        all_score = (format_reward + acc_reward) * len_pen
        score = normalized(all_score)
    """
    # print(f"############################ solution_str:{solution_str}")
    pred_tail = extract_after_think(solution_str)
    if pred_tail is None:
        return {
            "score": -1.0,
            "all_score": -1.0,
            "format_reward": -1.0,
            "acc_reward": 0.0,
            "len_pen": 0.0,
            "judge_mode": "none",
        }

    # Use ground_truth directly, no need to extract after <think>
    gt_tail = ground_truth.strip()
    if not gt_tail:
        return {
            "score": -1.0,
            "all_score": -1.0,
            "format_reward": -1.0,
            "acc_reward": 0.0,
            "len_pen": 0.0,
            "judge_mode": "none",
        }

    format_reward = 0.0

    if is_closed_gt(gt_tail):
        acc_reward = judge_binary(pred_tail, gt_tail)  # 0/1
        judge_mode = "binary"
    else:
        acc_reward = judge_ternary(pred_tail, gt_tail)  # 0/0.5/1
        judge_mode = "ternary"

    lp = length_penalty(pred_tail, gt_tail)

    all_score = (format_reward + acc_reward) * lp  # ∈ [0,1]
    # Normalize: this all_score is already in [0,1], so we use it as the normalized score
    score = float(all_score)

    return {
        "score": float(score),
        "all_score": float(all_score),
        "format_reward": float(format_reward),
        "acc_reward": float(acc_reward),
        "len_pen": float(lp),
        "judge_mode": judge_mode,
    }




# =========================
# Local test
# =========================
# def _print_result(name: str, result: Dict[str, Any]): 
#     print(f"\n=== {name} ===") 
#     for k, v in result.items(): 
#         print(f"{k:14s}: {v}")

# def main():
#     # ---------- 封闭式：正确 ----------
#     sol_1 = """<think>
# The answer is clearly A.
# </think>
# A
# """
#     gt_1 = "A"

#     r1 = compute_score("test", sol_1, gt_1)
#     _print_result("Closed / Correct", r1)

#     # ---------- 封闭式：错误 ----------
#     sol_2 = """<think>
# I think it's B.
# </think>
# B
# """
#     gt_2 = "A"

#     r2 = compute_score("test", sol_2, gt_2)
#     _print_result("Closed / Wrong", r2)

#     # ---------- 开放式：完全正确 ----------
#     sol_3 = """<think>
# Reasoning...
# </think>
# Paris is the capital of France.
# """
#     gt_3 = "Paris is the capital of France."

#     r3 = compute_score("test", sol_3, gt_3)
#     _print_result("Open / Correct", r3)

#     # ---------- 开放式：部分正确 ----------
#     sol_4 = """<think>
# Reasoning...
# </think>
# Paris is a city in France.
# """
#     gt_4 = "Paris is the capital of France."

#     r4 = compute_score("test", sol_4, gt_4)
#     _print_result("Open / Partial", r4)

#     # ---------- 开放式：错误 ----------
#     sol_5 = """<think>
# Reasoning...
# </think>
# Berlin is the capital of France.
# """
#     gt_5 = "Paris is the capital of France."

#     r5 = compute_score("test", sol_5, gt_5)
#     _print_result("Open / Wrong", r5)

#     # ---------- 长度惩罚测试 ----------
#     long_answer = "Paris is the capital of France. " * 200
#     sol_6 = f"""<think>
# Reasoning...
# </think>
# {long_answer}
# """
#     gt_6 = "Paris is the capital of France."

#     r6 = compute_score("test", sol_6, gt_6)
#     _print_result("Open / Long Answer (Len Penalty)", r6)

#     # ---------- 格式错误 ----------
#     sol_7 = "Paris is the capital of France."
#     gt_7 = "Paris is the capital of France."

#     r7 = compute_score("test", sol_7, gt_7)
#     _print_result("Format Invalid", r7)



# if __name__ == "__main__":
#     main()
