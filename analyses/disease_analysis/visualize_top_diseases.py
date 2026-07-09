#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top 10 罕见病和非罕见病对比可视化
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/figures_complete"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载数据
df = pd.read_csv(os.path.join(INPUT_DIR, "disease_overall_scores.csv"))

# 模型颜色配置
COLORS = {
    'OrthoPilot': '#E69F00',
    'CHEESE': '#56B4E9',
    'GPT-5.1': '#009E73',
    'DeepSeek-R1': '#F0E442',
    'MedGemma-27B': '#0072B2',
}

models = ['OrthoPilot', 'CHEESE', 'GPT-5.1', 'DeepSeek-R1', 'MedGemma-27B']

# 获取OrthoPilot数据
ortho = df[df['model_display'] == 'OrthoPilot'].copy()

# Top 10 罕见病 (按OrthoPilot得分)
rare_top10_codes = ortho[ortho['is_rare'] == True].nlargest(10, 'overall_score')['disease_code'].tolist()

# Top 10 非罕见病 (按OrthoPilot得分)
non_rare_top10_codes = ortho[ortho['is_rare'] == False].nlargest(10, 'overall_score')['disease_code'].tolist()

def get_disease_data(disease_codes, is_rare):
    """获取指定疾病的所有模型数据"""
    data = []
    for code in disease_codes:
        disease_df = df[df['disease_code'] == code]
        name = disease_df[disease_df['model_display'] == 'OrthoPilot']['disease_name'].values[0]
        
        scores = {}
        for model in models:
            score = disease_df[disease_df['model_display'] == model]['overall_score'].values
            if len(score) > 0:
                scores[model] = score[0]
            else:
                scores[model] = 0
        
        # 获取domain信息
        domain = disease_df[disease_df['model_display'] == 'OrthoPilot']['domain'].values[0]
        
        data.append({
            'code': code,
            'name': name,
            'scores': scores,
            'domain': domain,
            'is_rare': is_rare
        })
    return data

rare_data = get_disease_data(rare_top10_codes, True)
non_rare_data = get_disease_data(non_rare_top10_codes, False)

# ========== 图1: Top 10 罕见病 ==========
fig, ax = plt.subplots(figsize=(14, 10))

n_diseases = len(rare_data)
n_models = len(models)
bar_height = 0.6
group_height = n_models * bar_height + 0.3
total_height = n_diseases * group_height

y_positions = []
y_labels = []

for i, disease in enumerate(rare_data):
    group_base = total_height - (i + 1) * group_height + 0.3
    
    for j, model in enumerate(models):
        y = group_base + j * bar_height
        y_positions.append(y)
        score = disease['scores'][model]
        
        color = COLORS[model]
        alpha = 1.0 if model == 'OrthoPilot' else 0.6
        
        ax.barh(y, score, height=bar_height, color=color, alpha=alpha, edgecolor='none')
        
        # 数值标签
        text_color = 'white' if model in ['OrthoPilot', 'MedGemma-27B'] else 'black'
        ax.text(score + 0.01, y, f'{score:.2f}', va='center', ha='left', fontsize=8, color=text_color)
    
    # 疾病名称 (y轴标签)
    label_y = group_base + (n_models * bar_height) / 2 - bar_height/2
    y_labels.append((label_y, f"{disease['name']}\n({disease['code']}) [{disease['domain']}]"))

# 设置y轴
for y, label in y_labels:
    ax.text(-0.02, y, label, va='center', ha='right', fontsize=11)

ax.set_ylim(-0.5, total_height + 0.5)
ax.set_xlim(0, 1.1)
ax.set_xlabel('Mean Score', fontsize=16)
ax.set_title('Top 10 Rare Diseases: Model Performance Comparison', fontsize=16, fontweight='bold', pad=20)

# 图例
from matplotlib.patches import Patch
legend_patches = [Patch(facecolor=COLORS[m], label=m, alpha=0.8) for m in models]
ax.legend(handles=legend_patches, loc='lower right', frameon=False, fontsize=12)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=12)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'top10_rare_diseases.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'top10_rare_diseases.pdf'), bbox_inches='tight')
plt.close()
print("已保存: top10_rare_diseases.png/pdf")

# ========== 图2: Top 10 非罕见病 ==========
fig, ax = plt.subplots(figsize=(14, 10))

n_diseases = len(non_rare_data)
group_height = n_models * bar_height + 0.3
total_height = n_diseases * group_height

y_labels = []

for i, disease in enumerate(non_rare_data):
    group_base = total_height - (i + 1) * group_height + 0.3
    
    for j, model in enumerate(models):
        y = group_base + j * bar_height
        score = disease['scores'][model]
        
        color = COLORS[model]
        alpha = 1.0 if model == 'OrthoPilot' else 0.6
        
        ax.barh(y, score, height=bar_height, color=color, alpha=alpha, edgecolor='none')
        
        # 数值标签
        text_color = 'white' if model in ['OrthoPilot', 'MedGemma-27B'] else 'black'
        ax.text(score + 0.01, y, f'{score:.2f}', va='center', ha='left', fontsize=8, color=text_color)
    
    # 疾病名称
    label_y = group_base + (n_models * bar_height) / 2 - bar_height/2
    y_labels.append((label_y, f"{disease['name']}\n({disease['code']}) [{disease['domain']}]"))

# 设置y轴
for y, label in y_labels:
    ax.text(-0.02, y, label, va='center', ha='right', fontsize=11)

ax.set_ylim(-0.5, total_height + 0.5)
ax.set_xlim(0, 1.1)
ax.set_xlabel('Mean Score', fontsize=16)
ax.set_title('Top 10 Non-Rare Diseases: Model Performance Comparison', fontsize=16, fontweight='bold', pad=20)

# 图例
ax.legend(handles=legend_patches, loc='lower right', frameon=False, fontsize=12)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.tick_params(axis='x', labelsize=12)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'top10_non_rare_diseases.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'top10_non_rare_diseases.pdf'), bbox_inches='tight')
plt.close()
print("已保存: top10_non_rare_diseases.png/pdf")

# ========== 图3: 壮观全景图 - 所有疾病 (1000个) ==========
print("\n正在生成全景图...")

# 对所有疾病按OrthoPilot得分排序
all_ortho = ortho.sort_values('overall_score', ascending=False).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(20, 30))

n_diseases = len(all_ortho)
bar_height = 0.4
group_height = n_models * bar_height + 0.15

# 只显示前200个疾病，否则太密集
display_count = min(200, n_diseases)

for i in range(display_count):
    code = all_ortho.iloc[i]['disease_code']
    name = all_ortho.iloc[i]['disease_name']
    domain = all_ortho.iloc[i]['domain']
    is_rare = all_ortho.iloc[i]['is_rare']
    
    disease_df = df[df['disease_code'] == code]
    
    group_base = (display_count - i - 1) * group_height
    
    for j, model in enumerate(models):
        y = group_base + j * bar_height
        score = disease_df[disease_df['model_display'] == model]['overall_score'].values[0]
        
        color = COLORS[model]
        alpha = 1.0 if model == 'OrthoPilot' else 0.5
        
        ax.barh(y, score, height=bar_height, color=color, alpha=alpha, edgecolor='none')
    
    # 只在左侧显示疾病名称
    if i % 2 == 0:  # 隔行显示，避免太密集
        label = f"{name} ({code})"
        if len(label) > 25:
            label = label[:22] + "..."
        ax.text(-0.02, group_base + (n_models * bar_height) / 2, label, 
                va='center', ha='right', fontsize=6, alpha=0.7)

ax.set_ylim(-1, display_count * group_height + 1)
ax.set_xlim(0, 1.05)
ax.set_xlabel('Mean Score', fontsize=14)
ax.set_title(f'Top {display_count} Diseases by OrthoPilot Performance\n(All Models Comparison)', 
             fontsize=16, fontweight='bold', pad=20)

# 图例
ax.legend(handles=legend_patches, loc='lower right', frameon=False, fontsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)
ax.grid(axis='x', alpha=0.2)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'panorama_top_diseases.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(OUTPUT_DIR, 'panorama_top_diseases.pdf'), bbox_inches='tight')
plt.close()
print("已保存: panorama_top_diseases.png/pdf")

print("\n所有图表生成完成!")
