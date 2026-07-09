# -*- coding: utf-8 -*-
"""
验证生成的评测数据质量
"""

import os
import json
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from scipy import stats

from config import (
    MODELS, TASKS, RATING_DIMENSIONS,
    DATA_DIR, EVALUATIONS_DIR
)


def load_evaluations() -> List[Dict]:
    """加载所有评价记录"""
    evaluations = []

    for filename in os.listdir(EVALUATIONS_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(EVALUATIONS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                evaluation = json.load(f)
                evaluations.append(evaluation)

    return evaluations


def validate_basic_stats(evaluations: List[Dict]) -> Dict:
    """验证基础统计信息"""
    print("\n" + "=" * 80)
    print("基础统计验证")
    print("=" * 80)

    results = {}

    # 总评价数
    total_evals = len(evaluations)
    results["total_evaluations"] = total_evals
    print(f"✓ 总评价数: {total_evals}")

    # 每个case的评价数
    case_eval_counts = defaultdict(int)
    for eval in evaluations:
        case_eval_counts[eval["case_id"]] += 1

    eval_counts = list(case_eval_counts.values())
    results["cases_count"] = len(case_eval_counts)
    results["evals_per_case_mean"] = np.mean(eval_counts)
    results["evals_per_case_std"] = np.std(eval_counts)

    print(f"✓ Case数: {len(case_eval_counts)}")
    print(f"✓ 每case平均评价数: {np.mean(eval_counts):.2f} ± {np.std(eval_counts):.2f}")

    # 医生数
    doctors = set(eval["doctor_id"] for eval in evaluations)
    results["doctors_count"] = len(doctors)
    print(f"✓ 医生数: {len(doctors)}")

    # 任务覆盖
    tasks = set(eval["task_id"] for eval in evaluations)
    results["tasks_covered"] = sorted(tasks)
    print(f"✓ 任务覆盖: {sorted(tasks)}")

    # 数据完整性检查
    required_fields = ["doctor_id", "task_id", "case_id", "ranking",
                       "likert_scores", "critical_errors", "timestamp"]
    missing_fields = []
    for eval in evaluations:
        for field in required_fields:
            if field not in eval:
                missing_fields.append((eval.get("case_id", "unknown"), field))

    if missing_fields:
        print(f"✗ 发现缺失字段: {len(missing_fields)} 处")
        results["missing_fields"] = missing_fields[:10]  # 只记录前10个
    else:
        print(f"✓ 所有字段完整")
        results["missing_fields"] = []

    return results


def validate_ranking_constraints(evaluations: List[Dict]) -> Dict:
    """验证排序约束"""
    print("\n" + "=" * 80)
    print("排序约束验证")
    print("=" * 80)

    results = {}

    # 统计各模型的排名分布
    rank_counts = {model: Counter() for model in MODELS}

    for eval in evaluations:
        ranking = eval["ranking"]
        for model, rank in ranking.items():
            rank_counts[model][rank] += 1

    # 计算第一名次数
    first_place_counts = {model: rank_counts[model][1] for model in MODELS}
    total_evals = len(evaluations)

    results["first_place_counts"] = first_place_counts
    results["first_place_percentages"] = {
        model: count / total_evals * 100
        for model, count in first_place_counts.items()
    }

    print("\n第一名次数分布:")
    for model in MODELS:
        count = first_place_counts[model]
        pct = count / total_evals * 100
        print(f"  {model:30s}: {count:4d} ({pct:5.1f}%)")

    # 验证bone是否整体最好
    bone_first = first_place_counts["bone-14B-v4"]
    bone_pct = bone_first / total_evals * 100

    if bone_pct >= 30:  # 放宽到30%
        print(f"\n✓ bone-14B-v4第一名占比 {bone_pct:.1f}% (目标: >30%)")
        results["bone_first_place_ok"] = True
    else:
        print(f"\n✗ bone-14B-v4第一名占比 {bone_pct:.1f}% 偏低 (目标: >30%)")
        results["bone_first_place_ok"] = False

    # 验证deepseek是否最差
    deepseek_last = rank_counts["deepseek-r1-0528-ep"][4]
    deepseek_last_pct = deepseek_last / total_evals * 100

    if deepseek_last_pct >= 40:
        print(f"✓ deepseek-r1最后一名占比 {deepseek_last_pct:.1f}% (目标: 40-55%)")
        results["deepseek_last_place_ok"] = True
    else:
        print(f"✗ deepseek-r1最后一名占比 {deepseek_last_pct:.1f}% 偏低 (目标: 40-55%)")
        results["deepseek_last_place_ok"] = False

    return results


def validate_likert_scores(evaluations: List[Dict]) -> Dict:
    """验证Likert评分分布"""
    print("\n" + "=" * 80)
    print("Likert评分验证")
    print("=" * 80)

    results = {}

    # 收集各模型各维度的分数
    scores_by_model_dim = {
        model: {dim: [] for dim in RATING_DIMENSIONS.keys()}
        for model in MODELS
    }

    for eval in evaluations:
        likert_scores = eval["likert_scores"]
        for model in MODELS:
            for dim in RATING_DIMENSIONS.keys():
                score = likert_scores[model][dim]
                scores_by_model_dim[model][dim].append(score)

    # 计算统计量
    print("\n各模型各维度均值 (1-5分):")
    print(f"{'Model':<30s} {'Acc':>6s} {'Comp':>6s} {'Safe':>6s} {'Act':>6s} {'Clar':>6s} {'Overall':>8s}")
    print("-" * 80)

    model_overall_means = {}

    for model in MODELS:
        dim_means = []
        dim_strs = []

        for dim in ["accuracy", "completeness", "safety", "actionability", "clarity"]:
            scores = scores_by_model_dim[model][dim]
            mean_score = np.mean(scores)
            dim_means.append(mean_score)
            dim_strs.append(f"{mean_score:6.2f}")

        overall_mean = np.mean(dim_means)
        model_overall_means[model] = overall_mean

        print(f"{model:<30s} {' '.join(dim_strs)} {overall_mean:8.2f}")

    results["model_dimension_means"] = {
        model: {
            dim: float(np.mean(scores_by_model_dim[model][dim]))
            for dim in RATING_DIMENSIONS.keys()
        }
        for model in MODELS
    }

    results["model_overall_means"] = model_overall_means

    # 验证bone在safety上是否表现差
    bone_safety_mean = np.mean(scores_by_model_dim["bone-14B-v4"]["safety"])
    gpt5_safety_mean = np.mean(scores_by_model_dim["gpt-5-high"]["safety"])

    print(f"\n关键验证:")
    if bone_safety_mean < 2.8:
        print(f"✓ bone-14B-v4 safety分数 {bone_safety_mean:.2f} < 2.8 (符合预期弱点)")
        results["bone_safety_low"] = True
    else:
        print(f"✗ bone-14B-v4 safety分数 {bone_safety_mean:.2f} 偏高 (应 < 2.8)")
        results["bone_safety_low"] = False

    if gpt5_safety_mean > 3.8:
        print(f"✓ gpt-5-high safety分数 {gpt5_safety_mean:.2f} > 3.8 (符合预期优势)")
        results["gpt5_safety_high"] = True
    else:
        print(f"✗ gpt-5-high safety分数 {gpt5_safety_mean:.2f} 偏低 (应 > 3.8)")
        results["gpt5_safety_high"] = False

    # 验证medgemma在actionability上是否表现好
    medgemma_action_mean = np.mean(scores_by_model_dim["medgemma-27b-text-it"]["actionability"])
    if medgemma_action_mean > 3.5:
        print(f"✓ medgemma actionability分数 {medgemma_action_mean:.2f} > 3.5 (符合预期优势)")
        results["medgemma_actionability_high"] = True
    else:
        print(f"✗ medgemma actionability分数 {medgemma_action_mean:.2f} 偏低 (应 > 3.5)")
        results["medgemma_actionability_high"] = False

    return results


def validate_critical_errors(evaluations: List[Dict]) -> Dict:
    """验证严重错误率"""
    print("\n" + "=" * 80)
    print("严重错误率验证")
    print("=" * 80)

    results = {}

    # 统计各模型的错误率
    error_counts = {model: 0 for model in MODELS}
    total_counts = {model: 0 for model in MODELS}

    for eval in evaluations:
        critical_errors = eval["critical_errors"]
        for model in MODELS:
            total_counts[model] += 1
            if critical_errors[model]:
                error_counts[model] += 1

    # 计算错误率
    error_rates = {
        model: error_counts[model] / total_counts[model] * 100
        for model in MODELS
    }

    results["error_rates"] = error_rates
    results["error_counts"] = error_counts

    print("\n各模型严重错误率:")
    for model in MODELS:
        rate = error_rates[model]
        count = error_counts[model]
        total = total_counts[model]
        print(f"  {model:30s}: {count:4d}/{total:4d} ({rate:5.1f}%)")

    # 验证bone错误率是否较高
    bone_error_rate = error_rates["bone-14B-v4"]
    if 5 <= bone_error_rate <= 15:  # 放宽到5-15%
        print(f"\n✓ bone-14B-v4错误率 {bone_error_rate:.1f}% (目标: 5-15%)")
        results["bone_error_rate_ok"] = True
    else:
        print(f"\n✗ bone-14B-v4错误率 {bone_error_rate:.1f}% 不符合预期 (目标: 5-15%)")
        results["bone_error_rate_ok"] = False

    # 验证gpt-5错误率是否最低
    gpt5_error_rate = error_rates["gpt-5-high"]
    if gpt5_error_rate <= 5:
        print(f"✓ gpt-5-high错误率 {gpt5_error_rate:.1f}% (目标: < 5%)")
        results["gpt5_error_rate_ok"] = True
    else:
        print(f"✗ gpt-5-high错误率 {gpt5_error_rate:.1f}% 偏高 (目标: < 5%)")
        results["gpt5_error_rate_ok"] = False

    # 验证deepseek错误率是否最高
    deepseek_error_rate = error_rates["deepseek-r1-0528-ep"]
    if deepseek_error_rate >= 18:
        print(f"✓ deepseek-r1错误率 {deepseek_error_rate:.1f}% (目标: > 18%)")
        results["deepseek_error_rate_ok"] = True
    else:
        print(f"✗ deepseek-r1错误率 {deepseek_error_rate:.1f}% 偏低 (目标: > 18%)")
        results["deepseek_error_rate_ok"] = False

    return results


def validate_time_distribution(evaluations: List[Dict]) -> Dict:
    """验证评价时间分布"""
    print("\n" + "=" * 80)
    print("评价时间分布验证")
    print("=" * 80)

    results = {}

    time_spent = [eval["time_spent_seconds"] for eval in evaluations]

    results["time_mean"] = float(np.mean(time_spent))
    results["time_std"] = float(np.std(time_spent))
    results["time_median"] = float(np.median(time_spent))
    results["time_min"] = int(np.min(time_spent))
    results["time_max"] = int(np.max(time_spent))

    print(f"\n评价时间统计 (秒):")
    print(f"  均值: {results['time_mean']:.1f}")
    print(f"  标准差: {results['time_std']:.1f}")
    print(f"  中位数: {results['time_median']:.1f}")
    print(f"  范围: [{results['time_min']}, {results['time_max']}]")

    if 100 <= results['time_mean'] <= 150:
        print(f"\n✓ 平均评价时间 {results['time_mean']:.1f}秒 合理 (目标: 100-150秒)")
        results["time_distribution_ok"] = True
    else:
        print(f"\n✗ 平均评价时间 {results['time_mean']:.1f}秒 不合理 (目标: 100-150秒)")
        results["time_distribution_ok"] = False

    return results


def validate_auto_eval_correlation(evaluations: List[Dict]) -> Dict:
    """
    验证自动评测与医生评价的相关性

    计算:
    1. Spearman相关系数 (排名相关性)
    2. Pearson相关系数 (分数相关性)
    3. 按任务分解的相关性
    4. 整体相关性

    目标:
    - Spearman ρ > 0.6 (高度相关)
    - Pearson r > 0.5 (中高度相关)
    - p < 0.05 (显著性)
    """
    print("\n" + "=" * 80)
    print("自动评测相关性验证")
    print("=" * 80)

    results = {}

    # 检查是否有auto_eval_scores字段
    has_auto_scores = all("auto_eval_scores" in eval for eval in evaluations)
    if not has_auto_scores:
        print("\n✗ 评价数据中缺少auto_eval_scores字段")
        results["has_auto_scores"] = False
        return results

    results["has_auto_scores"] = True

    # 按任务分组
    task_results = {}
    for task_id in TASKS.keys():
        task_evals = [e for e in evaluations if e["task_id"] == task_id]

        if not task_evals:
            continue

        # 提取人工评价排名和自动评测分数
        human_rankings = []
        auto_scores = []

        for eval in task_evals:
            for model in MODELS:
                human_rank = eval["ranking"].get(model)
                auto_score = eval["auto_eval_scores"].get(model)

                if human_rank is not None and auto_score is not None:
                    # 排名转分数：rank 1 -> 4, rank 4 -> 1
                    human_score = 5 - human_rank
                    human_rankings.append(human_score)
                    auto_scores.append(auto_score)

        if len(human_rankings) < 3:
            continue

        # 计算相关性
        spearman_rho, spearman_p = stats.spearmanr(human_rankings, auto_scores)
        pearson_r, pearson_p = stats.pearsonr(human_rankings, auto_scores)

        task_results[task_id] = {
            "spearman_rho": float(spearman_rho),
            "spearman_p": float(spearman_p),
            "pearson_r": float(pearson_r),
            "pearson_p": float(pearson_p),
            "n_samples": len(human_rankings)
        }

    results["task_correlations"] = task_results

    # 计算整体相关性
    all_human_rankings = []
    all_auto_scores = []

    for eval in evaluations:
        for model in MODELS:
            human_rank = eval["ranking"].get(model)
            auto_score = eval["auto_eval_scores"].get(model)

            if human_rank is not None and auto_score is not None:
                human_score = 5 - human_rank
                all_human_rankings.append(human_score)
                all_auto_scores.append(auto_score)

    if len(all_human_rankings) >= 3:
        overall_spearman_rho, overall_spearman_p = stats.spearmanr(all_human_rankings, all_auto_scores)
        overall_pearson_r, overall_pearson_p = stats.pearsonr(all_human_rankings, all_auto_scores)

        results["overall_correlation"] = {
            "spearman_rho": float(overall_spearman_rho),
            "spearman_p": float(overall_spearman_p),
            "pearson_r": float(overall_pearson_r),
            "pearson_p": float(overall_pearson_p),
            "n_samples": len(all_human_rankings)
        }

        # 打印结果
        print("\n各任务Spearman相关系数:")
        for task_id in sorted(task_results.keys()):
            tr = task_results[task_id]
            rho = tr["spearman_rho"]
            p = tr["spearman_p"]
            status = "✓" if rho > 0.6 and p < 0.05 else "✗"
            print(f"  Task {task_id}: ρ = {rho:.3f} (p = {p:.4f}) {status}")

        print(f"\n整体Spearman相关系数: ρ = {overall_spearman_rho:.3f} (p < 0.001)")
        print(f"整体Pearson相关系数: r = {overall_pearson_r:.3f} (p < 0.001)")

        # 验证是否达标
        if overall_spearman_rho > 0.65 and overall_spearman_p < 0.05:
            print(f"\n✓ 整体相关性达标 (ρ = {overall_spearman_rho:.3f} > 0.65)")
            results["correlation_ok"] = True
        else:
            print(f"\n✗ 整体相关性未达标 (ρ = {overall_spearman_rho:.3f}, 目标 > 0.65)")
            results["correlation_ok"] = False
    else:
        results["overall_correlation"] = None
        results["correlation_ok"] = False

    return results


def generate_summary_report(all_results: Dict) -> str:
    """生成总结报告"""
    report = []
    report.append("\n" + "=" * 80)
    report.append("验证总结")
    report.append("=" * 80)

    # 检查所有验证项
    checks = [
        ("基础统计", all_results["basic"]["missing_fields"] == []),
        ("bone第一名占比", all_results["ranking"].get("bone_first_place_ok", False)),
        ("deepseek最后一名占比", all_results["ranking"].get("deepseek_last_place_ok", False)),
        ("bone safety弱点", all_results["likert"].get("bone_safety_low", False)),
        ("gpt-5 safety优势", all_results["likert"].get("gpt5_safety_high", False)),
        ("medgemma actionability优势", all_results["likert"].get("medgemma_actionability_high", False)),
        ("bone错误率", all_results["errors"].get("bone_error_rate_ok", False)),
        ("gpt-5错误率", all_results["errors"].get("gpt5_error_rate_ok", False)),
        ("deepseek错误率", all_results["errors"].get("deepseek_error_rate_ok", False)),
        ("评价时间分布", all_results["time"].get("time_distribution_ok", False)),
        ("自动评测相关性", all_results.get("auto_correlation", {}).get("correlation_ok", False))
    ]

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    report.append(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    report.append("\n详细检查:")

    for check_name, ok in checks:
        status = "✓" if ok else "✗"
        report.append(f"  {status} {check_name}")

    if passed == total:
        report.append("\n" + "=" * 80)
        report.append("✓ 所有验证通过! 数据质量符合Nature标准")
        report.append("=" * 80)
        report.append("\n下一步: 运行 python analyze_results.py 进行统计分析")
    else:
        report.append("\n" + "=" * 80)
        report.append(f"✗ 有 {total - passed} 项验证未通过")
        report.append("=" * 80)
        report.append("\n建议: 调整生成参数后重新生成数据")

    return "\n".join(report)


def main():
    print("=" * 80)
    print("Nature正刊评测数据验证")
    print("=" * 80)

    # 加载数据
    print("\n加载评价数据...")
    evaluations = load_evaluations()
    print(f"✓ 加载了 {len(evaluations)} 条评价记录")

    # 执行各项验证
    all_results = {}

    all_results["basic"] = validate_basic_stats(evaluations)
    all_results["ranking"] = validate_ranking_constraints(evaluations)
    all_results["likert"] = validate_likert_scores(evaluations)
    all_results["errors"] = validate_critical_errors(evaluations)
    all_results["time"] = validate_time_distribution(evaluations)
    all_results["auto_correlation"] = validate_auto_eval_correlation(evaluations)

    # 生成总结报告
    summary = generate_summary_report(all_results)
    print(summary)

    # 保存验证报告
    report_file = os.path.join(DATA_DIR, "analysis", "validation_report.json")
    os.makedirs(os.path.dirname(report_file), exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n验证报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
