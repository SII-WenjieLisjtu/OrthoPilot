#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计分析脚本：分析医生评价结果
- Bradley-Terry模型分析排序
- 评价者一致性分析（Kappa, Kendall's W）
- 与自动评测对比验证
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from scipy import stats
from itertools import combinations

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODELS, TASKS, DATA_DIR, EVALUATIONS_DIR
from utils.storage import load_all_evaluations, load_doctors

# =====================
# 数据加载
# =====================
def load_evaluations_by_case() -> Dict[Tuple[int, str], List[Dict]]:
    """
    按case组织评价数据
    返回: {(task_id, case_id): [evaluation1, evaluation2, ...]}
    """
    evaluations = load_all_evaluations()
    by_case = defaultdict(list)

    for eval_data in evaluations:
        task_id = eval_data.get("task_id")
        case_id = eval_data.get("case_id")
        if task_id and case_id:
            by_case[(task_id, case_id)].append(eval_data)

    return dict(by_case)

def load_evaluations_by_task() -> Dict[int, List[Dict]]:
    """
    按task组织评价数据
    返回: {task_id: [evaluation1, evaluation2, ...]}
    """
    evaluations = load_all_evaluations()
    by_task = defaultdict(list)

    for eval_data in evaluations:
        task_id = eval_data.get("task_id")
        if task_id:
            by_task[task_id].append(eval_data)

    return dict(by_task)

# =====================
# Bradley-Terry模型
# =====================
def rankings_to_pairwise_comparisons(rankings: List[Dict[str, int]]) -> List[Tuple[str, str]]:
    """
    将排序数据转换为配对比较
    ranking: {model: rank}，rank越小越好
    返回: [(winner, loser), ...]
    """
    comparisons = []
    for ranking in rankings:
        for m1, m2 in combinations(MODELS, 2):
            r1 = ranking.get(m1, 999)
            r2 = ranking.get(m2, 999)
            if r1 < r2:  # m1排名更好（数字更小）
                comparisons.append((m1, m2))
            elif r2 < r1:
                comparisons.append((m2, m1))
            # 相等则不添加（并列情况）
    return comparisons

def calculate_win_rates(comparisons: List[Tuple[str, str]]) -> Dict[str, Dict[str, float]]:
    """
    计算配对胜率矩阵
    返回: {model1: {model2: win_rate}}
    """
    wins = defaultdict(lambda: defaultdict(int))
    total = defaultdict(lambda: defaultdict(int))

    for winner, loser in comparisons:
        wins[winner][loser] += 1
        total[winner][loser] += 1
        total[loser][winner] += 1

    win_rates = {}
    for m1 in MODELS:
        win_rates[m1] = {}
        for m2 in MODELS:
            if m1 == m2:
                win_rates[m1][m2] = None
            elif total[m1][m2] > 0:
                win_rates[m1][m2] = wins[m1][m2] / total[m1][m2]
            else:
                win_rates[m1][m2] = None

    return win_rates

def bradley_terry_simple(comparisons: List[Tuple[str, str]], max_iter: int = 1000, tol: float = 1e-6) -> Dict[str, float]:
    """
    简单Bradley-Terry模型实现
    返回每个模型的"能力参数"（归一化，越大越好）
    """
    # 统计胜负
    wins = defaultdict(int)
    matches = defaultdict(lambda: defaultdict(int))

    for winner, loser in comparisons:
        wins[winner] += 1
        matches[winner][loser] += 1
        matches[loser][winner] += 1

    # 初始化参数
    params = {m: 1.0 for m in MODELS}

    # 迭代优化
    for iteration in range(max_iter):
        old_params = params.copy()

        for m in MODELS:
            numerator = wins[m]
            denominator = 0.0
            for other in MODELS:
                if m != other:
                    n_matches = matches[m][other]
                    if n_matches > 0:
                        denominator += n_matches / (params[m] + params[other])

            if denominator > 0:
                params[m] = numerator / denominator

        # 归一化
        total = sum(params.values())
        if total > 0:
            params = {m: p / total for m, p in params.items()}

        # 检查收敛
        diff = max(abs(params[m] - old_params[m]) for m in MODELS)
        if diff < tol:
            break

    return params

# =====================
# 评价者一致性
# =====================
def fleiss_kappa(ratings: List[List[int]], n_categories: int) -> float:
    """
    计算Fleiss' Kappa
    ratings: [[rater1_item1, rater2_item1, ...], [rater1_item2, ...], ...]
    n_categories: 类别数（对于排序，可能是4）
    """
    n_items = len(ratings)
    n_raters = len(ratings[0]) if ratings else 0

    if n_items == 0 or n_raters < 2:
        return None

    # 计算每个item每个category的频数
    counts = []
    for item_ratings in ratings:
        item_counts = [0] * n_categories
        for r in item_ratings:
            if 0 <= r < n_categories:
                item_counts[r] += 1
        counts.append(item_counts)

    # P_i: 每个item的一致性
    P_i = []
    for item_counts in counts:
        n = sum(item_counts)
        if n < 2:
            continue
        sum_sq = sum(c * c for c in item_counts)
        p_i = (sum_sq - n) / (n * (n - 1))
        P_i.append(p_i)

    if not P_i:
        return None

    P_bar = np.mean(P_i)

    # P_j: 每个category的比例
    total_ratings = n_items * n_raters
    P_j = []
    for j in range(n_categories):
        count_j = sum(counts[i][j] for i in range(n_items))
        P_j.append(count_j / total_ratings)

    P_e = sum(p ** 2 for p in P_j)

    if P_e == 1:
        return 1.0

    kappa = (P_bar - P_e) / (1 - P_e)
    return kappa

def kendall_w(rankings: List[List[int]]) -> Tuple[float, float]:
    """
    计算Kendall's W（排序一致性系数）
    rankings: [[rater1_ranks], [rater2_ranks], ...]
              每个rater对所有item的排名
    返回: (W, p_value)
    """
    rankings = np.array(rankings)
    n_raters, n_items = rankings.shape

    if n_raters < 2 or n_items < 2:
        return None, None

    # 计算每个item的排名和
    R = np.sum(rankings, axis=0)
    R_mean = np.mean(R)

    # 计算S（排名和的方差）
    S = np.sum((R - R_mean) ** 2)

    # 计算W
    W = 12 * S / (n_raters ** 2 * (n_items ** 3 - n_items))

    # 计算显著性（使用卡方近似）
    chi2 = n_raters * (n_items - 1) * W
    df = n_items - 1
    p_value = 1 - stats.chi2.cdf(chi2, df)

    return W, p_value

def calculate_icc(ratings: np.ndarray) -> float:
    """
    计算ICC(2,k) - 随机效应模型，评价者均值
    ratings: shape (n_items, n_raters)
    """
    n_items, n_raters = ratings.shape

    if n_items < 2 or n_raters < 2:
        return None

    # ANOVA components
    grand_mean = np.mean(ratings)
    row_means = np.mean(ratings, axis=1)
    col_means = np.mean(ratings, axis=0)

    # Sum of squares
    SS_total = np.sum((ratings - grand_mean) ** 2)
    SS_rows = n_raters * np.sum((row_means - grand_mean) ** 2)
    SS_cols = n_items * np.sum((col_means - grand_mean) ** 2)
    SS_error = SS_total - SS_rows - SS_cols

    # Mean squares
    MS_rows = SS_rows / (n_items - 1)
    MS_cols = SS_cols / (n_raters - 1)
    MS_error = SS_error / ((n_items - 1) * (n_raters - 1))

    # ICC(2,k)
    icc = (MS_rows - MS_error) / (MS_rows + (MS_cols - MS_error) / n_items)

    return icc

# =====================
# 与自动评测对比
# =====================
def load_auto_scores(task_id: int) -> Dict[str, Dict[str, float]]:
    """
    加载自动评测得分
    返回: {case_id: {model: score}}
    """
    # 这里需要从meta目录读取自动评测结果
    # 格式可能需要根据实际情况调整
    auto_scores = {}

    meta_root = "/path/to/orthopilot/gen_validation/meta/subset"

    for model in MODELS:
        model_safe = model.replace("/", "_").replace("-", "_")
        # 尝试查找score文件
        pattern = f"task{task_id}_scores_{model_safe}"

        if os.path.exists(meta_root):
            for filename in os.listdir(meta_root):
                if filename.startswith(f"task{task_id}_scores") and model in filename:
                    filepath = os.path.join(meta_root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        for item in data:
                            pid = item.get("patient_id")
                            scores = item.get("scores", {})
                            # 计算总分
                            total_covered = 0
                            total_possible = 0
                            for cat, levels in scores.items():
                                for level, (covered, possible) in levels.items():
                                    total_covered += covered
                                    total_possible += possible

                            if total_possible > 0:
                                score = total_covered / total_possible
                            else:
                                score = 0

                            case_id = f"patient_{pid}_open"
                            if case_id not in auto_scores:
                                auto_scores[case_id] = {}
                            auto_scores[case_id][model] = score
                    except Exception as e:
                        print(f"Error loading {filepath}: {e}")

    return auto_scores

def calculate_embedded_auto_correlation(evaluations: List[Dict]) -> Dict[str, float]:
    """
    使用评价记录内嵌的 auto_eval_scores 计算相关性
    """
    human_scores = []
    auto_score_list = []

    for evaluation in evaluations:
        ranking = evaluation.get("ranking", {})
        auto_scores = evaluation.get("auto_eval_scores", {})
        for model in MODELS:
            human_rank = ranking.get(model)
            auto_s = auto_scores.get(model)
            if human_rank is not None and auto_s is not None:
                human_scores.append(5 - human_rank)
                auto_score_list.append(auto_s)

    if len(human_scores) < 3:
        return {"spearman_rho": None, "spearman_p": None,
                "kendall_tau": None, "kendall_p": None}

    spearman_rho, spearman_p = stats.spearmanr(human_scores, auto_score_list)
    kendall_tau, kendall_p = stats.kendalltau(human_scores, auto_score_list)

    return {
        "spearman_rho": spearman_rho,
        "spearman_p": spearman_p,
        "kendall_tau": kendall_tau,
        "kendall_p": kendall_p,
        "n_samples": len(human_scores)
    }

# =====================
# 主分析函数
# =====================
def analyze_task(task_id: int, evaluations: List[Dict]) -> Dict[str, Any]:
    """
    分析单个任务的评价结果
    """
    if not evaluations:
        return {"error": "No evaluations found"}

    results = {
        "task_id": task_id,
        "task_name": TASKS.get(task_id, {}).get("name", f"Task {task_id}"),
        "n_evaluations": len(evaluations)
    }

    # 提取排序数据
    rankings = [e.get("ranking", {}) for e in evaluations if e.get("ranking")]
    case_ids = [e.get("case_id") for e in evaluations]

    # 1. Bradley-Terry分析
    comparisons = rankings_to_pairwise_comparisons(rankings)
    if comparisons:
        bt_params = bradley_terry_simple(comparisons)
        win_rates = calculate_win_rates(comparisons)
        results["bradley_terry"] = {
            "params": bt_params,
            "win_rates": win_rates,
            "n_comparisons": len(comparisons)
        }
    else:
        results["bradley_terry"] = {"error": "Insufficient comparisons"}

    # 2. 计算胜率统计
    model_first_place_count = defaultdict(int)
    for ranking in rankings:
        best_rank = min(ranking.values()) if ranking else 999
        for model, rank in ranking.items():
            if rank == best_rank:
                model_first_place_count[model] += 1

    results["first_place_counts"] = dict(model_first_place_count)

    # 3. 评价者一致性（需要按case分组）
    by_case = load_evaluations_by_case()
    case_evaluations = {k: v for k, v in by_case.items() if k[0] == task_id}

    # 提取每个case的多评价者排序
    multi_rater_cases = []
    for (tid, cid), evals in case_evaluations.items():
        if len(evals) >= 2:  # 至少2个评价者
            multi_rater_cases.append((cid, evals))

    if multi_rater_cases:
        # 准备Kendall's W数据
        # 每个rater对所有model的平均排名
        rater_rankings_for_models = defaultdict(list)

        for cid, evals in multi_rater_cases:
            for e in evals:
                doctor_id = e.get("doctor_id")
                ranking = e.get("ranking", {})
                for model in MODELS:
                    rank = ranking.get(model, 4)  # 默认最差
                    rater_rankings_for_models[doctor_id].append((model, rank))

        results["multi_rater_cases"] = len(multi_rater_cases)
    else:
        results["multi_rater_cases"] = 0

    # 4. 与自动评测对比
    has_embedded_scores = any(e.get("auto_eval_scores") for e in evaluations)
    if has_embedded_scores:
        correlation = calculate_embedded_auto_correlation(evaluations)
        results["auto_correlation"] = correlation
    else:
        auto_scores = load_auto_scores(task_id)
        if auto_scores:
            correlation = calculate_correlation_with_auto(rankings, auto_scores, case_ids)
            results["auto_correlation"] = correlation
        else:
            results["auto_correlation"] = {"note": "No auto scores found"}

    return results

def generate_report(results: Dict[int, Dict[str, Any]]) -> str:
    """
    生成分析报告
    """
    report = []
    report.append("=" * 60)
    report.append("医学AI评测分析报告")
    report.append("=" * 60)
    report.append("")

    for task_id, task_results in results.items():
        report.append(f"## Task {task_id}: {task_results.get('task_name', '')}")
        report.append(f"评价数: {task_results.get('n_evaluations', 0)}")
        report.append("")

        # Bradley-Terry结果
        bt = task_results.get("bradley_terry", {})
        if "params" in bt:
            report.append("### Bradley-Terry模型参数（能力值，越大越好）")
            params = bt["params"]
            sorted_params = sorted(params.items(), key=lambda x: -x[1])
            for model, param in sorted_params:
                report.append(f"  {model}: {param:.4f}")
            report.append("")

        # 第一名次数
        first_counts = task_results.get("first_place_counts", {})
        if first_counts:
            report.append("### 排名第一次数")
            for model, count in sorted(first_counts.items(), key=lambda x: -x[1]):
                report.append(f"  {model}: {count}次")
            report.append("")

        # 与自动评测相关性
        auto_corr = task_results.get("auto_correlation", {})
        if auto_corr.get("spearman_rho") is not None:
            report.append("### 与自动评测的相关性")
            report.append(f"  Spearman ρ: {auto_corr['spearman_rho']:.4f} (p={auto_corr['spearman_p']:.4f})")
            report.append(f"  Kendall τ: {auto_corr['kendall_tau']:.4f} (p={auto_corr['kendall_p']:.4f})")
            report.append(f"  样本数: {auto_corr.get('n_samples', 0)}")
            report.append("")

        report.append("-" * 40)
        report.append("")

    return "\n".join(report)

def main():
    print("加载评价数据...")
    by_task = load_evaluations_by_task()

    if not by_task:
        print("未找到评价数据。请确保医生已完成至少部分评价。")
        print(f"评价目录: {EVALUATIONS_DIR}")
        return

    print(f"找到 {len(by_task)} 个任务的评价数据")

    all_results = {}
    for task_id, evaluations in by_task.items():
        print(f"\n分析 Task {task_id} ({len(evaluations)} 条评价)...")
        results = analyze_task(task_id, evaluations)
        all_results[task_id] = results

    # 生成报告
    report = generate_report(all_results)
    print("\n" + report)

    # 保存结果
    output_dir = os.path.join(DATA_DIR, "analysis")
    os.makedirs(output_dir, exist_ok=True)

    # JSON结果
    json_path = os.path.join(output_dir, "analysis_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存到: {json_path}")

    # 文本报告
    report_path = os.path.join(output_dir, "analysis_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"报告已保存到: {report_path}")

if __name__ == "__main__":
    main()
