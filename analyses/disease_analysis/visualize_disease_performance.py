#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
疾病维度性能可视化脚本
生成Nature风格的图表
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path

# Nature风格配置 - 使用系统默认字体
plt.rcParams['font.size'] = 8
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['axes.labelsize'] = 8
plt.rcParams['axes.titlesize'] = 9
plt.rcParams['xtick.labelsize'] = 7
plt.rcParams['ytick.labelsize'] = 7
plt.rcParams['legend.fontsize'] = 7

# 色盲友好配色
COLORS = {
    'CHEESE': '#E69F00',      # 橙色 - 我们的模型
    'GPT-5.1': '#56B4E9',     # 蓝色
    'DeepSeek-R1': '#009E73', # 绿色
    'Qwen3': '#F0E442',       # 黄色
    'Gemini': '#0072B2',      # 深蓝色
    'Kimi': '#D55E00',        # 红褐色
    'Llama': '#CC79A7',       # 粉色
}

MODEL_DISPLAY_NAMES = {
    'bone-14B-RL-v2': 'CHEESE',
    'gpt-5.1': 'GPT-5.1',
    'deepseek-r1': 'DeepSeek-R1',
    'Qwen3-235B-A22B-Instruct-2507': 'Qwen3-235B',
    'Gemini-2.5-flash': 'Gemini-2.5',
    'kimi-k2-0905-preview': 'Kimi-k2',
    'llama-4-maverick': 'Llama-4',
}

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/figures"


def load_data():
    """加载数据"""
    disease_overall = pd.read_csv(os.path.join(INPUT_DIR, "disease_overall_scores.csv"))
    category_level = pd.read_csv(os.path.join(INPUT_DIR, "category_level_scores.csv"))
    task_type = pd.read_csv(os.path.join(INPUT_DIR, "task_type_scores.csv"))
    model_task = pd.read_csv(os.path.join(INPUT_DIR, "model_task_scores.csv"))
    return disease_overall, category_level, task_type, model_task


def plot_task_type_comparison(task_type_df):
    """绘制封闭式/开放式任务对比图"""
    fig, ax = plt.subplots(figsize=(4, 3))

    # 过滤数据
    closed_data = task_type_df[task_type_df['task_type'] == 'closed'].set_index('model')
    open_data = task_type_df[task_type_df['task_type'] == 'open'].set_index('model')

    models = ['bone-14B-RL-v2', 'gpt-5.1', 'deepseek-r1', 'Qwen3-235B-A22B-Instruct-2507',
              'Gemini-2.5-flash', 'kimi-k2-0905-preview', 'llama-4-maverick']

    x = np.arange(len(models))
    width = 0.35

    closed_scores = [closed_data.loc[m, 'mean_score'] if m in closed_data.index else 0 for m in models]
    open_scores = [open_data.loc[m, 'mean_score'] if m in open_data.index else 0 for m in models]

    bars1 = ax.bar(x - width/2, closed_scores, width, label='封闭式任务 (Task 1-4)', color='#0072B2')
    bars2 = ax.bar(x + width/2, open_scores, width, label='开放式任务 (Task 5-11)', color='#D55E00')

    ax.set_xlabel('模型')
    ax.set_ylabel('平均准确率/覆盖率')
    ax.set_title('各模型在封闭式 vs 开放式任务上的性能')
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISPLAY_NAMES.get(m, m) for m in models], rotation=45, ha='right')
    ax.legend(loc='upper right', frameon=False)
    ax.set_ylim(0, 1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'task_type_comparison.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(OUTPUT_DIR, 'task_type_comparison.pdf'), bbox_inches='tight')
    plt.close()
    print("已保存: task_type_comparison.png/pdf")


def plot_domain_rare_heatmap(category_df):
    """绘制域内/域外、罕见/非罕见热力图"""
    # 仅使用CHEESE模型的数据
    cheese_data = category_df[category_df['model'] == 'bone-14B-RL-v2'].copy()

    # 创建域内/域外 vs 罕见/非罕见的汇总
    summary = cheese_data.groupby(['domain', 'is_rare'])['mean_score'].mean().unstack()

    fig, ax = plt.subplots(figsize=(3, 2.5))

    im = ax.imshow(summary.values, cmap='RdYlGn', aspect='auto', vmin=0.4, vmax=0.8)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['非罕见病', '罕见病'])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['域内 (ID)', '域外 (OOD)'])

    # 添加数值标注
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, f'{summary.values[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=9)

    ax.set_title('CHEESE模型在不同类别上的性能')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('平均准确率')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'domain_rare_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(OUTPUT_DIR, 'domain_rare_heatmap.pdf'), bbox_inches='tight')
    plt.close()
    print("已保存: domain_rare_heatmap.png/pdf")


def plot_top_bottom_diseases(disease_df):
    """绘制表现最佳和最差的病种"""
    cheese_df = disease_df[disease_df['model'] == 'bone-14B-RL-v2'].sort_values('overall_score', ascending=False)

    # 选择有代表性的top和bottom疾病（至少有一定样本量）
    cheese_df_filtered = cheese_df[cheese_df['n_cases'] >= 7]

    top_10 = cheese_df_filtered.head(10)
    bottom_10 = cheese_df_filtered.tail(10)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))

    # Top 10
    y_pos = np.arange(len(top_10))
    ax1.barh(y_pos, top_10['overall_score'], color='#009E73')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top_10['disease_name'], fontsize=6)
    ax1.set_xlabel('平均准确率')
    ax1.set_title('CHEESE表现最佳的10种疾病')
    ax1.set_xlim(0, 1)
    ax1.invert_yaxis()
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Bottom 10
    y_pos = np.arange(len(bottom_10))
    ax2.barh(y_pos, bottom_10['overall_score'], color='#D55E00')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(bottom_10['disease_name'], fontsize=6)
    ax2.set_xlabel('平均准确率')
    ax2.set_title('CHEESE表现最差的10种疾病')
    ax2.set_xlim(0, 1)
    ax2.invert_yaxis()
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'top_bottom_diseases.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(OUTPUT_DIR, 'top_bottom_diseases.pdf'), bbox_inches='tight')
    plt.close()
    print("已保存: top_bottom_diseases.png/pdf")


def plot_model_comparison_across_diseases(disease_df):
    """绘制各模型在病种上的性能对比"""
    # 计算每个模型的平均分数
    model_avg = disease_df.groupby('model')['overall_score'].mean().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(5, 3))

    models = model_avg.index.tolist()
    scores = model_avg.values.tolist()

    colors = ['#E69F00' if m == 'bone-14B-RL-v2' else '#56B4E9' for m in models]

    bars = ax.bar(range(len(models)), scores, color=colors)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([MODEL_DISPLAY_NAMES.get(m, m) for m in models], rotation=45, ha='right')
    ax.set_ylabel('平均准确率 (跨所有病种)')
    ax.set_title('各模型在病种级别的平均性能')
    ax.set_ylim(0, 1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 添加数值标注
    for bar, score in zip(bars, scores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{score:.3f}',
                ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'model_disease_comparison.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(OUTPUT_DIR, 'model_disease_comparison.pdf'), bbox_inches='tight')
    plt.close()
    print("已保存: model_disease_comparison.png/pdf")


def generate_summary_table(disease_df, category_df, task_type_df):
    """生成汇总表格"""
    summary = []

    # 按模型汇总
    for model in disease_df['model'].unique():
        model_data = disease_df[disease_df['model'] == model]

        # 整体分数
        overall = model_data['overall_score'].mean()

        # 域内/域外
        id_score = model_data[model_data['domain'] == 'ID']['overall_score'].mean()
        ood_score = model_data[model_data['domain'] == 'OOD']['overall_score'].mean()

        # 罕见/非罕见
        rare_score = model_data[model_data['is_rare'] == True]['overall_score'].mean()
        non_rare_score = model_data[model_data['is_rare'] == False]['overall_score'].mean()

        # 封闭式/开放式
        closed_row = task_type_df[(task_type_df['model'] == model) & (task_type_df['task_type'] == 'closed')]
        open_row = task_type_df[(task_type_df['model'] == model) & (task_type_df['task_type'] == 'open')]

        closed_score = closed_row['mean_score'].values[0] if len(closed_row) > 0 else np.nan
        open_score = open_row['mean_score'].values[0] if len(open_row) > 0 else np.nan

        summary.append({
            '模型': MODEL_DISPLAY_NAMES.get(model, model),
            '整体平均分': f"{overall:.3f}",
            '域内(ID)': f"{id_score:.3f}",
            '域外(OOD)': f"{ood_score:.3f}",
            '罕见病': f"{rare_score:.3f}",
            '非罕见病': f"{non_rare_score:.3f}",
            '封闭式任务': f"{closed_score:.3f}" if not np.isnan(closed_score) else "-",
            '开放式任务': f"{open_score:.3f}" if not np.isnan(open_score) else "-",
        })

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(os.path.join(OUTPUT_DIR, "summary_table.csv"), index=False, encoding='utf-8-sig')
    print("已保存: summary_table.csv")

    # 打印表格
    print("\n=== 性能汇总表 ===")
    print(summary_df.to_string(index=False))

    return summary_df


def main():
    """主函数"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("疾病维度性能可视化")
    print("=" * 60)

    # 加载数据
    print("\n加载数据...")
    disease_df, category_df, task_type_df, model_task_df = load_data()
    print(f"  疾病数据: {len(disease_df)} 行")
    print(f"  类别数据: {len(category_df)} 行")

    # 生成图表
    print("\n生成图表...")
    plot_task_type_comparison(task_type_df)
    plot_domain_rare_heatmap(category_df)
    plot_top_bottom_diseases(disease_df)
    plot_model_comparison_across_diseases(disease_df)

    # 生成汇总表
    print("\n生成汇总表...")
    summary_df = generate_summary_table(disease_df, category_df, task_type_df)

    print("\n" + "=" * 60)
    print("可视化完成！")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
