#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nature正刊风格 - Top疾病可视化
使用棒棒糖图和Cleveland点图
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# 设置中文字体
plt.rcParams['font.family'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/figures_complete"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Nature配色方案 - 色盲友好
COLORS = {
    'OrthoPilot': '#CC79A7',      # 粉紫色 - 突出
    'CHEESE': '#56B4E9',          # 天蓝色
    'GPT-5.1': '#009E73',         # 蓝绿色
    'DeepSeek-R1': '#E69F00',     # 橙色
    'MedGemma-27B': '#0072B2',    # 深蓝色
}

# 背景色和网格色
NATURE_BG = '#FAFAFA'
GRID_COLOR = '#E0E0E0'

models = ['OrthoPilot', 'CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']
model_order = ['MedGemma-27B', 'DeepSeek-R1', 'CHEESE', 'GPT-5.1', 'OrthoPilot']  # 从低到高

# 加载数据
df = pd.read_csv(os.path.join(INPUT_DIR, "disease_overall_scores.csv"))
ortho = df[df['model_display'] == 'OrthoPilot'].copy()

# 获取Top 10
def get_top_diseases(is_rare, n=10):
    codes = ortho[ortho['is_rare'] == is_rare].nlargest(n, 'overall_score')['disease_code'].tolist()
    data = []
    for code in codes:
        disease_df = df[df['disease_code'] == code]
        name = disease_df[disease_df['model_display'] == 'OrthoPilot']['disease_name'].values[0]
        domain = disease_df[disease_df['model_display'] == 'OrthoPilot']['domain'].values[0]
        scores = {m: disease_df[disease_df['model_display'] == m]['overall_score'].values[0] for m in models}
        data.append({'code': code, 'name': name, 'domain': domain, 'scores': scores})
    return data

rare_data = get_top_diseases(True)
non_rare_data = get_top_diseases(False)

# 简化疾病名称（英文缩写）
def simplify_name(name, code):
    """简化疾病名称用于显示"""
    # 如果名字太长，使用code
    if len(name) > 12:
        return code
    return name

# ==================== 图1: 棒棒糖图 - Top 10 罕见病 ====================
fig, ax = plt.subplots(figsize=(10, 12))
fig.patch.set_facecolor(NATURE_BG)
ax.set_facecolor(NATURE_BG)

n_diseases = len(rare_data)
y_spacing = 1.5

for i, disease in enumerate(rare_data):
    y_base = (n_diseases - i - 1) * y_spacing
    
    # 绘制每个模型的棒棒糖
    for j, model in enumerate(model_order):
        score = disease['scores'][model]
        y_pos = y_base + j * 0.25
        
        # 线条
        ax.plot([0, score], [y_pos, y_pos], color=COLORS[model], 
                linewidth=2, alpha=0.6, zorder=1)
        
        # 圆点
        size = 80 if model == 'OrthoPilot' else 50
        edge_width = 2 if model == 'OrthoPilot' else 1
        ax.scatter(score, y_pos, s=size, c=COLORS[model], 
                  edgecolors='white', linewidths=edge_width, zorder=3)
        
        # 数值标签（仅OrthoPilot）
        if model == 'OrthoPilot':
            ax.text(score + 0.02, y_pos, f'{score:.2f}', 
                   va='center', ha='left', fontsize=9, fontweight='bold', color=COLORS[model])
    
    # 疾病标签
    label = f"{disease['name']} [{disease['domain']}]"
    ax.text(-0.05, y_base + 0.5, label, va='center', ha='right', fontsize=10)

# 添加参考线
for x in np.arange(0.2, 1.1, 0.2):
    ax.axvline(x=x, color=GRID_COLOR, linestyle='-', linewidth=0.5, zorder=0)

ax.set_xlim(-0.1, 1.15)
ax.set_ylim(-0.5, n_diseases * y_spacing)
ax.set_xlabel('Mean Performance Score', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Rare Diseases\nModel Performance Comparison', 
             fontsize=14, fontweight='bold', pad=20)

# 图例
legend_elements = [plt.scatter([], [], s=60, c=COLORS[m], edgecolors='white', linewidths=1, label=m) 
                   for m in model_order]
ax.legend(handles=legend_elements, loc='lower right', frameon=False, 
          fontsize=10, title='Models', title_fontsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_lollipop_rare.png'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_lollipop_rare.pdf'), bbox_inches='tight', facecolor=NATURE_BG)
plt.close()
print("✓ nature_lollipop_rare.png/pdf")

# ==================== 图2: 棒棒糖图 - Top 10 非罕见病 ====================
fig, ax = plt.subplots(figsize=(10, 12))
fig.patch.set_facecolor(NATURE_BG)
ax.set_facecolor(NATURE_BG)

n_diseases = len(non_rare_data)

for i, disease in enumerate(non_rare_data):
    y_base = (n_diseases - i - 1) * y_spacing
    
    for j, model in enumerate(model_order):
        score = disease['scores'][model]
        y_pos = y_base + j * 0.25
        
        ax.plot([0, score], [y_pos, y_pos], color=COLORS[model], 
                linewidth=2, alpha=0.6, zorder=1)
        
        size = 80 if model == 'OrthoPilot' else 50
        edge_width = 2 if model == 'OrthoPilot' else 1
        ax.scatter(score, y_pos, s=size, c=COLORS[model], 
                  edgecolors='white', linewidths=edge_width, zorder=3)
        
        if model == 'OrthoPilot':
            ax.text(score + 0.02, y_pos, f'{score:.2f}', 
                   va='center', ha='left', fontsize=9, fontweight='bold', color=COLORS[model])
    
    label = f"{disease['name']} [{disease['domain']}]"
    ax.text(-0.05, y_base + 0.5, label, va='center', ha='right', fontsize=10)

for x in np.arange(0.2, 1.1, 0.2):
    ax.axvline(x=x, color=GRID_COLOR, linestyle='-', linewidth=0.5, zorder=0)

ax.set_xlim(-0.1, 1.15)
ax.set_ylim(-0.5, n_diseases * y_spacing)
ax.set_xlabel('Mean Performance Score', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Non-Rare Diseases\nModel Performance Comparison', 
             fontsize=14, fontweight='bold', pad=20)

legend_elements = [plt.scatter([], [], s=60, c=COLORS[m], edgecolors='white', linewidths=1, label=m) 
                   for m in model_order]
ax.legend(handles=legend_elements, loc='lower right', frameon=False, 
          fontsize=10, title='Models', title_fontsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_lollipop_non_rare.png'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_lollipop_non_rare.pdf'), bbox_inches='tight', facecolor=NATURE_BG)
plt.close()
print("✓ nature_lollipop_non_rare.png/pdf")

# ==================== 图3: Cleveland点图 - 罕见病 ====================
fig, ax = plt.subplots(figsize=(10, 10))
fig.patch.set_facecolor(NATURE_BG)
ax.set_facecolor(NATURE_BG)

y_positions = []
labels = []

for i, disease in enumerate(rare_data):
    y_base = (n_diseases - i - 1) * 1.2
    
    # 疾病标签位置
    labels.append((y_base + 0.4, f"{disease['name']} [{disease['domain']}]"))
    
    for j, model in enumerate(model_order):
        score = disease['scores'][model]
        y_pos = y_base + j * 0.2
        y_positions.append(y_pos)
        
        # 点的大小根据性能
        size = 100 if model == 'OrthoPilot' else 70
        ax.scatter(score, y_pos, s=size, c=COLORS[model], 
                  edgecolors='white', linewidths=1.5, zorder=3, alpha=0.9)

# 添加连接线（每个疾病内部）
for i, disease in enumerate(rare_data):
    y_base = (n_diseases - i - 1) * 1.2
    scores = [disease['scores'][m] for m in model_order]
    y_pos_list = [y_base + j * 0.2 for j in range(len(model_order))]
    
    # 连接最低和最高
    ax.plot([min(scores), max(scores)], [y_pos_list[0], y_pos_list[-1]], 
            'k-', linewidth=0.5, alpha=0.3, zorder=1)

for y, label in labels:
    ax.text(-0.03, y, label, va='center', ha='right', fontsize=10)

for x in np.arange(0.2, 1.1, 0.2):
    ax.axvline(x=x, color=GRID_COLOR, linestyle='-', linewidth=0.5, zorder=0)

ax.set_xlim(-0.1, 1.1)
ax.set_ylim(-0.5, n_diseases * 1.2)
ax.set_xlabel('Mean Performance Score', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Rare Diseases - Cleveland Dot Plot', fontsize=14, fontweight='bold', pad=20)

legend_elements = [plt.scatter([], [], s=70, c=COLORS[m], edgecolors='white', linewidths=1, label=m) 
                   for m in model_order]
ax.legend(handles=legend_elements, loc='lower right', frameon=False, fontsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_dotplot_rare.png'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_dotplot_rare.pdf'), bbox_inches='tight', facecolor=NATURE_BG)
plt.close()
print("✓ nature_dotplot_rare.png/pdf")

# ==================== 图4: 散点对比图 - OrthoPilot vs Others ====================
fig, axes = plt.subplots(2, 2, figsize=(12, 12))
fig.patch.set_facecolor(NATURE_BG)

other_models = ['CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']

for idx, (ax, other_model) in enumerate(zip(axes.flat, other_models)):
    ax.set_facecolor(NATURE_BG)
    
    # 获取所有疾病的分数
    ortho_scores = []
    other_scores = []
    is_rare_list = []
    
    for code in ortho['disease_code'].unique():
        disease_df = df[df['disease_code'] == code]
        ortho_score = disease_df[disease_df['model_display'] == 'OrthoPilot']['overall_score'].values[0]
        other_score = disease_df[disease_df['model_display'] == other_model]['overall_score'].values[0]
        is_rare = disease_df[disease_df['model_display'] == 'OrthoPilot']['is_rare'].values[0]
        
        ortho_scores.append(ortho_score)
        other_scores.append(other_score)
        is_rare_list.append(is_rare)
    
    # 绘制散点
    rare_mask = np.array(is_rare_list)
    ax.scatter(np.array(other_scores)[rare_mask], np.array(ortho_scores)[rare_mask], 
              c='#D55E00', alpha=0.5, s=30, label='Rare', edgecolors='none')
    ax.scatter(np.array(other_scores)[~rare_mask], np.array(ortho_scores)[~rare_mask], 
              c='#0072B2', alpha=0.3, s=20, label='Non-rare', edgecolors='none')
    
    # 对角线
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='y=x')
    
    # 标注优势区域
    ax.fill_between([0, 1], [0, 1], [1, 1], alpha=0.1, color=COLORS['OrthoPilot'], label='OrthoPilot better')
    
    ax.set_xlim(0.2, 1.0)
    ax.set_ylim(0.2, 1.0)
    ax.set_xlabel(f'{other_model} Score', fontsize=11)
    ax.set_ylabel('OrthoPilot Score', fontsize=11)
    ax.set_title(f'OrthoPilot vs {other_model}', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', frameon=False, fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')

plt.suptitle('OrthoPilot Performance Comparison Across All Diseases', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_scatter_comparison.png'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_scatter_comparison.pdf'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.close()
print("✓ nature_scatter_comparison.png/pdf")

# ==================== 图5: 综合排名变化图 (Slope Chart) ====================
fig, ax = plt.subplots(figsize=(14, 10))
fig.patch.set_facecolor(NATURE_BG)
ax.set_facecolor(NATURE_BG)

# 选取Top 20疾病展示排名变化
top20_codes = ortho.nlargest(20, 'overall_score')['disease_code'].tolist()

# 计算每个模型在这些疾病上的排名
disease_rankings = {}
for code in top20_codes:
    disease_df = df[df['disease_code'] == code]
    scores = [(m, disease_df[disease_df['model_display'] == m]['overall_score'].values[0]) 
              for m in models]
    scores.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (model, score) in enumerate(scores, 1):
        if model not in disease_rankings:
            disease_rankings[model] = []
        disease_rankings[model].append((code, rank, score))

# 绘制slope chart
y_diseases = list(range(len(top20_codes)))

for i, code in enumerate(top20_codes):
    disease_df = df[df['disease_code'] == code]
    name = disease_df[disease_df['model_display'] == 'OrthoPilot']['disease_name'].values[0]
    
    # 左侧OrthoPilot
    ortho_score = disease_df[disease_df['model_display'] == 'OrthoPilot']['overall_score'].values[0]
    
    # 右侧其他模型平均
    other_scores = [disease_df[disease_df['model_display'] == m]['overall_score'].values[0] 
                    for m in models if m != 'OrthoPilot']
    avg_other = np.mean(other_scores)
    
    # 绘制连接线
    color = COLORS['OrthoPilot'] if ortho_score > avg_other else '#999999'
    alpha = 0.8 if ortho_score > avg_other else 0.2
    
    ax.plot([0, 1], [ortho_score, avg_other], color=color, linewidth=2, alpha=alpha, zorder=1)
    
    # 标记OrthoPilot
    ax.scatter(0, ortho_score, s=100, c=COLORS['OrthoPilot'], zorder=3, edgecolors='white', linewidths=1)
    ax.scatter(1, avg_other, s=80, c='#999999', zorder=3, edgecolors='white', linewidths=1)

# 设置坐标轴
ax.set_xlim(-0.1, 1.1)
ax.set_ylim(0.3, 1.0)
ax.set_xticks([0, 1])
ax.set_xticklabels(['OrthoPilot', 'Avg of Others'], fontsize=12, fontweight='bold')
ax.set_ylabel('Performance Score', fontsize=12, fontweight='bold')
ax.set_title('OrthoPilot vs Others: Top 20 Diseases Performance Gap', fontsize=14, fontweight='bold', pad=20)

# 添加网格
for y in np.arange(0.4, 1.0, 0.1):
    ax.axhline(y=y, color=GRID_COLOR, linestyle='-', linewidth=0.5, zorder=0)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.tick_params(axis='x', which='both', bottom=False)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_slope_top20.png'), dpi=300, bbox_inches='tight', facecolor=NATURE_BG)
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_slope_top20.pdf'), bbox_inches='tight', facecolor=NATURE_BG)
plt.close()
print("✓ nature_slope_top20.png/pdf")

print("\n" + "="*50)
print("Nature风格图表生成完成！")
print("="*50)
print("\n生成的图表:")
print("  1. nature_lollipop_rare.png/pdf - 棒棒糖图(罕见病)")
print("  2. nature_lollipop_non_rare.png/pdf - 棒棒糖图(非罕见病)")
print("  3. nature_dotplot_rare.png/pdf - Cleveland点图")
print("  4. nature_scatter_comparison.png/pdf - 散点对比矩阵")
print("  5. nature_slope_top20.png/pdf - 性能差距斜率图")
print(f"\n输出目录: {OUTPUT_DIR}")
