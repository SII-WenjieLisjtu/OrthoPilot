#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成Extended Data的Bradley-Terry参数图表
包含7个任务 + Overall，使用bootstrap计算置信区间
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Dict, Tuple
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import TASKS, MODELS, MODEL_LABELS_EN, DATA_DIR, EVALUATIONS_DIR

# 设置matplotlib参数
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['figure.dpi'] = 300


def compute_bt_parameters(evaluations: List[Dict]) -> Dict[str, float]:
    """
    计算Bradley-Terry参数

    使用迭代算法计算每个模型的BT参数
    """
    # 统计两两比较结果
    wins = defaultdict(lambda: defaultdict(int))

    for eval in evaluations:
        ranking = eval["ranking"]
        models = list(ranking.keys())

        # 对于每对模型，排名靠前的"赢"排名靠后的
        for i, model_i in enumerate(models):
            for j, model_j in enumerate(models):
                if i != j:
                    if ranking[model_i] < ranking[model_j]:
                        wins[model_i][model_j] += 1

    # 初始化参数
    params = {model: 1.0 for model in MODELS}

    # 迭代更新参数
    for _ in range(100):
        new_params = {}
        for model_i in MODELS:
            numerator = 0
            denominator = 0

            for model_j in MODELS:
                if model_i != model_j:
                    n_ij = wins[model_i][model_j]
                    n_ji = wins[model_j][model_i]
                    n_total = n_ij + n_ji

                    if n_total > 0:
                        numerator += n_ij
                        denominator += n_total / (params[model_i] + params[model_j])

            if denominator > 0:
                new_params[model_i] = numerator / denominator
            else:
                new_params[model_i] = params[model_i]

        params = new_params

    # 归一化使总和为1
    total = sum(params.values())
    params = {k: v/total for k, v in params.items()}

    return params


def bootstrap_bt_parameters(evaluations: List[Dict], n_bootstrap: int = 1000) -> Dict[str, Tuple[float, float, float]]:
    """
    使用bootstrap计算BT参数的置信区间

    Returns:
        {model: (mean, lower_ci, upper_ci)}
    """
    n_samples = len(evaluations)
    bootstrap_params = defaultdict(list)

    for _ in range(n_bootstrap):
        # 重采样
        bootstrap_sample = np.random.choice(evaluations, size=n_samples, replace=True)

        # 计算BT参数
        params = compute_bt_parameters(bootstrap_sample.tolist())

        for model, param in params.items():
            bootstrap_params[model].append(param)

    # 计算均值和95%置信区间
    results = {}
    for model in MODELS:
        params_array = np.array(bootstrap_params[model])
        mean = np.mean(params_array)
        lower = np.percentile(params_array, 2.5)
        upper = np.percentile(params_array, 97.5)
        results[model] = (mean, lower, upper)

    return results


def generate_bt_figure_with_ci(evaluations: List[Dict], output_dir: str):
    """
    生成包含数值标注的Bradley-Terry参数图

    布局：7个任务 + Overall，每个任务组内柱子无间隙，组间有间隙
    """
    # 按任务分组
    task_evals = defaultdict(list)
    for eval in evaluations:
        task_evals[eval["task_id"]].append(eval)

    # 计算每个任务的BT参数（不计算CI）
    task_bt_results = {}
    for task_id in sorted(TASKS.keys()):
        task_bt_results[task_id] = compute_bt_parameters(task_evals[task_id])

    # 计算Overall的BT参数
    overall_bt_results = compute_bt_parameters(evaluations)

    # 创建图表
    fig, ax = plt.subplots(figsize=(16, 6))

    # 模型和颜色
    models = ["bone-14B-v4", "gpt-5-high", "medgemma-27b-text-it", "deepseek-r1-0528-ep"]
    model_labels = [MODEL_LABELS_EN[m] for m in models]
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']

    # 任务标签
    task_labels = [TASKS[tid]["name_en"] for tid in sorted(TASKS.keys())] + ["Overall"]
    n_tasks = len(task_labels)
    n_models = len(models)

    # 柱子宽度和组间距
    bar_width = 0.8
    group_gap = 1.5

    # 计算每个柱子的x位置
    x_positions = []
    current_x = 0
    for task_idx in range(n_tasks):
        task_positions = []
        for model_idx in range(n_models):
            task_positions.append(current_x)
            current_x += bar_width
        x_positions.append(task_positions)
        current_x += group_gap  # 组间间隙

    # 绘制柱子
    for task_idx, task_id in enumerate(sorted(TASKS.keys()) + ['overall']):
        if task_id == 'overall':
            bt_results = overall_bt_results
        else:
            bt_results = task_bt_results[task_id]

        for model_idx, model in enumerate(models):
            value = bt_results[model]

            x_pos = x_positions[task_idx][model_idx]

            bar = ax.bar(x_pos, value, bar_width,
                   color=colors[model_idx], alpha=0.8,
                   edgecolor='black', linewidth=1.0)

            # 在柱子上方添加数值标注
            ax.text(x_pos, value + 0.01, f'{value:.3f}',
                   ha='center', va='bottom', fontsize=8, fontweight='normal')

    # 设置x轴刻度
    group_centers = [np.mean(positions) for positions in x_positions]
    ax.set_xticks(group_centers)
    ax.set_xticklabels(task_labels, rotation=45, ha='right', fontsize=10, fontweight='normal')

    # 设置y轴
    ax.set_ylabel('Bradley-Terry Parameter', fontsize=12, fontweight='normal')
    ax.set_ylim(0, 0.55)  # 调整上限使图表更美观
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.8)

    # 添加图例
    legend_handles = [plt.Rectangle((0,0),1,1, facecolor=colors[i], edgecolor='black', linewidth=1.0, alpha=0.8)
                     for i in range(n_models)]
    ax.legend(legend_handles, model_labels,
             loc='upper right', frameon=True, fancybox=False,
             edgecolor='black', framealpha=0.95, fontsize=10)

    # 添加垂直分隔线
    for task_idx in range(n_tasks - 1):
        separator_x = x_positions[task_idx][-1] + bar_width + group_gap / 2
        ax.axvline(x=separator_x, color='gray', linestyle=':', alpha=0.5, linewidth=1.0)

    plt.tight_layout()

    # 保存
    plt.savefig(os.path.join(output_dir, 'extended_bt_params_with_ci.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'extended_bt_params_with_ci.pdf'), bbox_inches='tight')
    plt.close()

    print("  ✓ Extended Data Figure: Bradley-Terry Parameters with CI")


def main():
    # 加载评价数据
    evaluations = []

    for fname in os.listdir(EVALUATIONS_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(EVALUATIONS_DIR, fname), 'r', encoding='utf-8') as f:
                evaluations.append(json.load(f))

    print(f"加载了 {len(evaluations)} 条评价记录")

    # 生成图表
    output_dir = os.path.join(DATA_DIR, "analysis", "figures")
    os.makedirs(output_dir, exist_ok=True)

    generate_bt_figure_with_ci(evaluations, output_dir)

    print("图表生成完成!")


if __name__ == "__main__":
    main()
