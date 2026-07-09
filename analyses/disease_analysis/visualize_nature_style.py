#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nature正刊风格可视化
使用点图(Dot Plot)展示Top 10罕见病和非罕见病
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 设置中文字体
plt.rcParams['font.family'] = ['DejaVu Sans']

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/figures_complete"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Nature配色方案 (色盲友好)
COLORS = {
    'OrthoPilot': '#CC79A7',  # 粉红
    'CHEESE': '#009E73',       # 绿色
    'GPT-5.1': '#0072B2',      # 蓝色
    'DeepSeek-R1': '#E69F00',  # 橙色
    'MedGemma-27B': '#56B4E9', # 浅蓝
}

# 加载数据
df = pd.read_csv(os.path.join(INPUT_DIR, "disease_overall_scores.csv"))
mapping_df = pd.read_csv('disease_name_mapping.csv')

# 创建映射字典
disease_info = mapping_df.set_index('code').to_dict('index')

models = ['OrthoPilot', 'CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']

# 获取Top 10数据
def get_top10_data(is_rare):
    top_codes = mapping_df[mapping_df['is_rare'] == is_rare].head(10)['code'].tolist()
    
    data = []
    for code in top_codes:
        info = disease_info[code]
        scores = {}
        for model in models:
            score = df[(df['disease_code'] == code) & (df['model_display'] == model)]['overall_score'].values
            scores[model] = score[0] if len(score) > 0 else 0
        
        data.append({
            'code': code,
            'name': info['english_name'],
            'patient_count': info['patient_count'],
            'scores': scores,
            'domain': info['domain'],
            'is_rare': is_rare
        })
    return data

rare_data = get_top10_data(True)
non_rare_data = get_top10_data(False)

# ==================== 图1: Top 10 Rare Diseases - Cleveland Dot Plot ====================
fig, ax = plt.subplots(figsize=(12, 10))

y_positions = np.arange(len(rare_data))
marker_size = 80
offset = 0.12

for i, disease in enumerate(rare_data):
    y_base = y_positions[len(rare_data)-1-i]
    
    # 绘制患者数量背景条 (右侧小条)
    patient_bar_width = disease['patient_count'] / 500 * 0.15  # 缩放
    ax.barh(y_base - 0.35, patient_bar_width, height=0.08, color='#CCCCCC', alpha=0.5, left=1.02)
    
    for j, model in enumerate(models):
        score = disease['scores'][model]
        x_offset = (j - 2) * offset
        
        color = COLORS[model]
        alpha = 1.0
        size = marker_size
        
        # OrthoPilot更大更突出
        if model == 'OrthoPilot':
            size = marker_size * 1.5
            marker = 'D'  # 菱形
            zorder = 10
        else:
            marker = 'o'
            zorder = 5
            alpha = 0.8
        
        ax.scatter(score, y_base + x_offset, s=size, c=color, alpha=alpha, 
                   marker=marker, edgecolors='white', linewidths=1, zorder=zorder)

# 添加疾病名称 (右侧)
for i, disease in enumerate(rare_data):
    y = y_positions[len(rare_data)-1-i]
    name = disease['name']
    if len(name) > 35:
        name = name[:32] + "..."
    
    label_text = f"{name}"
    count_text = f"n={disease['patient_count']}"
    
    ax.text(-0.08, y, label_text, ha='right', va='center', fontsize=10)
    ax.text(1.15, y, count_text, ha='left', va='center', fontsize=8, color='#666666')

# 绘制连接OrthoPilot和次高分的线
for i, disease in enumerate(rare_data):
    y = y_positions[len(rare_data)-1-i]
    ortho_score = disease['scores']['OrthoPilot']
    
    # 找到第二高分
    other_scores = [(m, disease['scores'][m]) for m in models if m != 'OrthoPilot']
    best_other = max(other_scores, key=lambda x: x[1])
    
    # 画虚线连接
    ax.plot([best_other[1], ortho_score], [y, y], 'k--', alpha=0.3, linewidth=1, zorder=1)

ax.set_xlim(-0.15, 1.25)
ax.set_ylim(-0.8, len(rare_data) - 0.2)
ax.set_xlabel('Mean Score', fontsize=14, fontweight='bold')
ax.set_title('Top 10 Rare Diseases\nOrthoPilot Performance Advantage', fontsize=16, fontweight='bold', pad=20)

# 图例
legend_elements = [
    Line2D([0], [0], marker='D', color='w', markerfacecolor=COLORS['OrthoPilot'], 
           markersize=12, label='OrthoPilot', markeredgecolor='white'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['GPT-5.1'], 
           markersize=10, label='GPT-5.1', markeredgecolor='white'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['CHEESE'], 
           markersize=10, label='CHEESE', markeredgecolor='white'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['DeepSeek-R1'], 
           markersize=10, label='DeepSeek-R1', markeredgecolor='white'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['MedGemma-27B'], 
           markersize=10, label='MedGemma-27B', markeredgecolor='white'),
]
ax.legend(handles=legend_elements, loc='lower right', frameon=False, fontsize=10)

# Nature风格网格
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=11)
ax.grid(axis='x', alpha=0.2, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

# 添加患者数量说明
ax.text(1.15, -0.5, 'Patient\ncount', ha='left', va='center', fontsize=8, color='#666666')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_top10_rare.png'), dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_top10_rare.pdf'), bbox_inches='tight', facecolor='white')
plt.close()
print("已保存: nature_top10_rare.png/pdf")

# ==================== 图2: Top 10 Non-Rare Diseases ====================
fig, ax = plt.subplots(figsize=(12, 10))

y_positions = np.arange(len(non_rare_data))

for i, disease in enumerate(non_rare_data):
    y_base = y_positions[len(non_rare_data)-1-i]
    
    # 患者数量条
    patient_bar_width = disease['patient_count'] / 500 * 0.15
    ax.barh(y_base - 0.35, patient_bar_width, height=0.08, color='#CCCCCC', alpha=0.5, left=1.02)
    
    for j, model in enumerate(models):
        score = disease['scores'][model]
        x_offset = (j - 2) * offset
        
        color = COLORS[model]
        alpha = 1.0
        size = marker_size
        
        if model == 'OrthoPilot':
            size = marker_size * 1.5
            marker = 'D'
            zorder = 10
        else:
            marker = 'o'
            zorder = 5
            alpha = 0.8
        
        ax.scatter(score, y_base + x_offset, s=size, c=color, alpha=alpha, 
                   marker=marker, edgecolors='white', linewidths=1, zorder=zorder)

# 疾病名称
for i, disease in enumerate(non_rare_data):
    y = y_positions[len(non_rare_data)-1-i]
    name = disease['name']
    if len(name) > 35:
        name = name[:32] + "..."
    
    label_text = f"{name}"
    count_text = f"n={disease['patient_count']}"
    
    ax.text(-0.08, y, label_text, ha='right', va='center', fontsize=10)
    ax.text(1.15, y, count_text, ha='left', va='center', fontsize=8, color='#666666')

# 连接线
for i, disease in enumerate(non_rare_data):
    y = y_positions[len(non_rare_data)-1-i]
    ortho_score = disease['scores']['OrthoPilot']
    
    other_scores = [(m, disease['scores'][m]) for m in models if m != 'OrthoPilot']
    best_other = max(other_scores, key=lambda x: x[1])
    
    ax.plot([best_other[1], ortho_score], [y, y], 'k--', alpha=0.3, linewidth=1, zorder=1)

ax.set_xlim(-0.15, 1.25)
ax.set_ylim(-0.8, len(non_rare_data) - 0.2)
ax.set_xlabel('Mean Score', fontsize=14, fontweight='bold')
ax.set_title('Top 10 Non-Rare Diseases\nOrthoPilot Performance Advantage', fontsize=16, fontweight='bold', pad=20)

ax.legend(handles=legend_elements, loc='lower right', frameon=False, fontsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=11)
ax.grid(axis='x', alpha=0.2, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

ax.text(1.15, -0.5, 'Patient\ncount', ha='left', va='center', fontsize=8, color='#666666')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_top10_non_rare.png'), dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_top10_non_rare.pdf'), bbox_inches='tight', facecolor='white')
plt.close()
print("已保存: nature_top10_non_rare.png/pdf")

# ==================== 图3: 壮观全景图 - 所有疾病 (按患者数量排序) ====================
print("\n正在生成壮观全景图...")

# 按患者数量排序的前100个疾病
top_by_count = mapping_df.nlargest(100, 'patient_count').copy()

fig, ax = plt.subplots(figsize=(14, 24))

y_positions = np.arange(len(top_by_count))
marker_size_small = 40
offset_small = 0.08

for idx, (_, row) in enumerate(top_by_count.iterrows()):
    code = row['code']
    y_base = y_positions[len(top_by_count)-1-idx]
    
    # 获取该疾病的所有模型分数
    for j, model in enumerate(models):
        score = df[(df['disease_code'] == code) & (df['model_display'] == model)]['overall_score'].values
        if len(score) == 0:
            continue
        score = score[0]
        x_offset = (j - 2) * offset_small
        
        color = COLORS[model]
        
        if model == 'OrthoPilot':
            size = marker_size_small * 1.3
            marker = 'D'
            alpha = 1.0
            zorder = 10
        else:
            size = marker_size_small
            marker = 'o'
            alpha = 0.6
            zorder = 5
        
        ax.scatter(score, y_base + x_offset, s=size, c=color, alpha=alpha,
                   marker=marker, edgecolors='white', linewidths=0.5, zorder=zorder)
    
    # 疾病名称 (每5个显示一个)
    if idx % 3 == 0:
        name = row['english_name']
        if len(name) > 30:
            name = name[:27] + "..."
        count_text = f"n={int(row['patient_count'])}"
        ax.text(-0.05, y_base, f"{name} ({count_text})", ha='right', va='center', fontsize=7, alpha=0.8)

ax.set_xlim(-0.1, 1.05)
ax.set_ylim(-1, len(top_by_count))
ax.set_xlabel('Mean Score', fontsize=14, fontweight='bold')
ax.set_title('Top 100 Diseases by Patient Volume\nOrthoPilot vs. Baseline Models', 
             fontsize=16, fontweight='bold', pad=20)

# 简化图例
legend_elements_small = [
    Line2D([0], [0], marker='D', color='w', markerfacecolor=COLORS['OrthoPilot'], 
           markersize=10, label='OrthoPilot'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['GPT-5.1'], 
           markersize=8, label='GPT-5.1'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['CHEESE'], 
           markersize=8, label='CHEESE'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['DeepSeek-R1'], 
           markersize=8, label='DeepSeek-R1'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['MedGemma-27B'], 
           markersize=8, label='MedGemma-27B'),
]
ax.legend(handles=legend_elements_small, loc='lower right', frameon=False, fontsize=9, ncol=2)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=10)
ax.grid(axis='x', alpha=0.15, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_panorama_top100.png'), dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(os.path.join(OUTPUT_DIR, 'nature_panorama_top100.pdf'), bbox_inches='tight', facecolor='white')
plt.close()
print("已保存: nature_panorama_top100.png/pdf")

print("\n所有Nature风格图表生成完成!")
