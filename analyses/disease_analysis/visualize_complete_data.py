#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据可视化脚本
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/figures_complete"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载数据
disease_overall = pd.read_csv(os.path.join(INPUT_DIR, "disease_overall_scores.csv"))
task_type = pd.read_csv(os.path.join(INPUT_DIR, "task_type_scores.csv"))
model_task = pd.read_csv(os.path.join(INPUT_DIR, "model_task_scores.csv"))
raw_scores = pd.read_csv(os.path.join(INPUT_DIR, "raw_scores_complete.csv"))

# 模型显示名称映射
MODEL_NAMES = {
    'OrthoPilot': 'OrthoPilot',
    'CHEESE': 'CHEESE',
    'GPT-5.1': 'GPT-5.1',
    'DeepSeek-R1': 'DeepSeek-R1',
    'MedGemma-27B': 'MedGemma-27B',
}

COLORS = {
    'OrthoPilot': '#F6C8B6',
    'CHEESE': '#92B1D9',
    'GPT-5.1': '#DBDDEF',
    'DeepSeek-R1': '#C1D8E9',
    'MedGemma-27B': '#D4D4D4',
}

print("=" * 60)
print("生成可视化图表")
print("=" * 60)

# 1. 任务类型对比图
fig, ax = plt.subplots(figsize=(8, 5))

models = ['OrthoPilot', 'CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']
x = np.arange(len(models))
width = 0.35

closed_scores = []
open_scores = []
for model in models:
    model_df = task_type[task_type['model_display'] == model]
    closed = model_df[model_df['task_type'] == 'closed']['mean_score'].values[0]
    open_score = model_df[model_df['task_type'] == 'open']['mean_score'].values[0]
    closed_scores.append(closed)
    open_scores.append(open_score)

bars1 = ax.bar(x - width/2, closed_scores, width, label='Closed-ended Tasks (1-4)', color='#0072B2')
bars2 = ax.bar(x + width/2, open_scores, width, label='Open-ended Tasks (5-11)', color='#D55E00')

ax.set_ylabel('Mean Score', fontsize=11)
ax.set_title('Performance Across Task Types', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=15, ha='right')
ax.legend(loc='upper right', frameon=False)
ax.set_ylim(0, 1.0)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.3)

# 添加数值标签
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'task_type_comparison.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'task_type_comparison.pdf'), bbox_inches='tight')
plt.close()
print("已保存: task_type_comparison.png/pdf")

# 2. 各模型在各任务上的性能热力图
fig, ax = plt.subplots(figsize=(10, 5))

# 准备数据
pivot_data = []
for model in models:
    model_df = model_task[model_task['model_display'] == model].sort_values('task')
    scores = model_df['mean_score'].values
    pivot_data.append(scores)

pivot_df = pd.DataFrame(pivot_data, index=models, columns=[f'Task {i}' for i in range(1, 12)])

im = ax.imshow(pivot_df.values, cmap='RdYlGn', aspect='auto', vmin=0.3, vmax=0.9)

ax.set_xticks(np.arange(11))
ax.set_xticklabels([f'Task {i}' for i in range(1, 12)])
ax.set_yticks(np.arange(len(models)))
ax.set_yticklabels(models)

# 添加数值标注
for i in range(len(models)):
    for j in range(11):
        text = ax.text(j, i, f'{pivot_df.values[i, j]:.2f}',
                      ha="center", va="center", color="black" if pivot_df.values[i, j] > 0.5 else "white",
                      fontsize=8)

ax.set_title('Performance Heatmap by Task', fontsize=12, fontweight='bold', pad=10)
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Mean Score', rotation=270, labelpad=15)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'task_heatmap.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'task_heatmap.pdf'), bbox_inches='tight')
plt.close()
print("已保存: task_heatmap.png/pdf")

# 3. 病种级别性能分布 - 使用带间隙的堆叠柱状图
fig, ax = plt.subplots(figsize=(10, 9))

# 准备数据 - 计算每个bin的计数
bins = np.linspace(0.3, 1.0, 22)  # 从0.3开始，21个bins
bin_centers = (bins[:-1] + bins[1:]) / 2
bin_width = bins[1] - bins[0]
gap = 0.12  # 组间间隙
stack_gap = 0.5  # 堆叠间隙（像素）

# 计算每个模型的直方图计数
hist_data = {}
for model in models:
    scores = disease_overall[disease_overall['model_display'] == model]['overall_score'].values
    counts, _ = np.histogram(scores, bins=bins)
    hist_data[model] = counts

 # 绘制堆叠柱状图，带间隙
# 首先为图例创建proxy artists
from matplotlib.patches import Rectangle
legend_patches = [Rectangle((0, 0), 1, 1, facecolor=COLORS[m], alpha=0.6, edgecolor='none') for m in models]

for i, center in enumerate(bin_centers):
    bottom = 0
    for model in models:
        count = hist_data[model][i]
        if count > 0:
            # 绘制柱子（带堆叠间隙）
            bar_height = max(0, count - stack_gap) if count > stack_gap else count
            ax.bar(center, bar_height, width=bin_width*(1-gap), bottom=bottom,
                   color=COLORS[model], alpha=0.6, edgecolor='none')

            # 标注数值（如果柱子足够大）
            if count >= 12:  # 只标注较大的柱子
                text_color = 'white' if model == 'CHEESE' else '#333333'
                ax.text(center, bottom + count/2, f'{int(count)}',
                       ha='center', va='center', fontsize=12,
                       color=text_color,
                       fontweight='bold')

            bottom += count

ax.set_xlabel('Disease-level Mean Score', fontsize=21)
ax.set_ylabel('Number of Diseases', fontsize=21)
ax.set_xlim(0.28, 1.02)
ax.tick_params(axis='both', which='major', labelsize=18)
ax.legend(legend_patches, models, loc='upper left', frameon=False, fontsize=18)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'disease_distribution.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'disease_distribution.pdf'), bbox_inches='tight')
plt.close()
print("已保存: disease_distribution.png/pdf (stacked bar with gaps)")

# 4. 域内/域外 vs 罕见/非罕见
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

# 域内 vs 域外
domain_data = raw_scores.groupby(['model_display', 'domain'])['score'].mean().unstack()
domain_data = domain_data.reindex(models)
x = np.arange(len(models))
width = 0.35

axes[0].bar(x - width/2, domain_data['ID'], width, label='In-Domain (ID)', color='#009E73')
axes[0].bar(x + width/2, domain_data['OOD'], width, label='Out-of-Domain (OOD)', color='#E69F00')
axes[0].set_ylabel('Mean Score', fontsize=10)
axes[0].set_title('Performance: In-Domain vs Out-of-Domain', fontsize=11, fontweight='bold')
axes[0].set_xticks(x)
axes[0].set_xticklabels(models, rotation=15, ha='right')
axes[0].legend(frameon=False)
axes[0].spines['top'].set_visible(False)
axes[0].spines['right'].set_visible(False)
axes[0].set_ylim(0, 1.0)
axes[0].grid(axis='y', alpha=0.3)

# 罕见 vs 非罕见
rare_data = raw_scores.groupby(['model_display', 'is_rare'])['score'].mean().unstack()
rare_data = rare_data.reindex(models)

axes[1].bar(x - width/2, rare_data[False], width, label='Non-Rare', color='#56B4E9')
axes[1].bar(x + width/2, rare_data[True], width, label='Rare', color='#D55E00')
axes[1].set_ylabel('Mean Score', fontsize=10)
axes[1].set_title('Performance: Non-Rare vs Rare Diseases', fontsize=11, fontweight='bold')
axes[1].set_xticks(x)
axes[1].set_xticklabels(models, rotation=15, ha='right')
axes[1].legend(frameon=False)
axes[1].spines['top'].set_visible(False)
axes[1].spines['right'].set_visible(False)
axes[1].set_ylim(0, 1.0)
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'domain_rare_comparison.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'domain_rare_comparison.pdf'), bbox_inches='tight')
plt.close()
print("已保存: domain_rare_comparison.png/pdf")

# 5. OrthoPilot vs 其他模型对比
fig, ax = plt.subplots(figsize=(8, 5))

ortho_diseases = disease_overall[disease_overall['model_display'] == 'OrthoPilot'][['disease_code', 'overall_score']].set_index('disease_code')
other_models = ['CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']

# 计算OrthoPilot强于其他模型的比例
advantages = []
for other_model in other_models:
    other_diseases = disease_overall[disease_overall['model_display'] == other_model][['disease_code', 'overall_score']].set_index('disease_code')
    comparison = ortho_diseases.join(other_diseases, lsuffix='_ortho', rsuffix='_other')
    advantage_pct = (comparison['overall_score_ortho'] > comparison['overall_score_other']).mean() * 100
    advantages.append(advantage_pct)

bars = ax.barh(other_models, advantages, color=['#56B4E9', '#009E73', '#F0E442', '#0072B2'])
ax.set_xlabel('Percentage of Diseases where OrthoPilot is Superior (%)', fontsize=11)
ax.set_title('OrthoPilot Advantage over Other Models', fontsize=12, fontweight='bold')
ax.set_xlim(0, 100)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='x', alpha=0.3)

# 添加数值标签
for bar, adv in zip(bars, advantages):
    width = bar.get_width()
    ax.text(width, bar.get_y() + bar.get_height()/2.,
            f'{adv:.1f}%', ha='left', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'orthopilot_advantage.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'orthopilot_advantage.pdf'), bbox_inches='tight')
plt.close()
print("已保存: orthopilot_advantage.png/pdf")

# 生成汇总表格
print("\n" + "=" * 60)
print("性能汇总表")
print("=" * 60)

summary = []
for model in models:
    model_df = disease_overall[disease_overall['model_display'] == model]
    task_df = task_type[task_type['model_display'] == model]

    overall = model_df['overall_score'].mean()
    closed = task_df[task_df['task_type'] == 'closed']['mean_score'].values[0]
    open_score = task_df[task_df['task_type'] == 'open']['mean_score'].values[0]

    id_score = model_df[model_df['domain'] == 'ID']['overall_score'].mean()
    ood_score = model_df[model_df['domain'] == 'OOD']['overall_score'].mean()
    rare_score = model_df[model_df['is_rare'] == True]['overall_score'].mean()
    non_rare_score = model_df[model_df['is_rare'] == False]['overall_score'].mean()

    summary.append({
        'Model': model,
        'Overall': f"{overall:.3f}",
        'Closed': f"{closed:.3f}",
        'Open': f"{open_score:.3f}",
        'ID': f"{id_score:.3f}",
        'OOD': f"{ood_score:.3f}",
        'Rare': f"{rare_score:.3f}",
        'Non-Rare': f"{non_rare_score:.3f}",
    })

summary_df = pd.DataFrame(summary)
print(summary_df.to_string(index=False))
summary_df.to_csv(os.path.join(OUTPUT_DIR, "summary_table.csv"), index=False)

print("\n" + "=" * 60)
print("可视化完成！")
print(f"输出目录: {OUTPUT_DIR}")
