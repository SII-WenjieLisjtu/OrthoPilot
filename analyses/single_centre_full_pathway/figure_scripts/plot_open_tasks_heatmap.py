#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap for open-ended tasks (5–11) — horizontal / rotated 90° version.
Rows = tasks + Average (with a visual gap before Average)
Columns = models grouped by category, with small gaps between categories.
Color intensity represents ORACLE score (%)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ── Global style ─────────────────────────────────────────────────────────────
# 优先 Arial；若系统没有 Arial，则自动回退，避免 findfont 报错
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Liberation Sans', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.color'] = 'black'
plt.rcParams['axes.labelcolor'] = 'black'
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_FILE = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv'
OUT_DIR   = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/figure/task_grouping'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load & filter ────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_FILE)
df = df[~df['model'].isin(['Qwen3-8B', 'HuatuoGPT-o1-7B'])].copy()

# Correct model group assignments and display names used in the figure.
df.loc[df['model'] == 'Gemini-2.5-flash', 'category'] = 'General LLMs'
df.loc[df['model'] == 'Claude-Sonnet-4.5', 'category'] = 'Reasoning LLMs'
df.loc[df['model'] == 'Qwen3-32B', 'category'] = 'Reasoning LLMs'
df.loc[df['model'] == 'Qwen3-235B', 'category'] = 'General LLMs'
df.loc[df['model'] == 'Qwen3-235B', 'model'] = 'Qwen3-235B-A22B'

# ── Category order: add Agent Methods ────────────────────────────────────────

# ── Task definitions: full names ─────────────────────────────────────────────
open_tasks = [f'task{i}' for i in range(5, 12)]
task_labels = [
    'Perioperative\nRisk Assessment',
    'Surgical\nPlanning',
    'Operative Note\nGeneration',
    'Postoperative\nOrders',
    'Discharge\nSummary',
    'Rehabilitation\nPlanning',
    'Multidisciplinary\nTeam Consultation'
]

# ── Category config ──────────────────────────────────────────────────────────
cat_order = ['Ours', 'Reasoning LLMs', 'General LLMs', 'Agent Methods', 'Medical LLMs']

# 模型类别之间空隙（越小越紧）
gap_cols = 0.22

# Average 行之前的空隙
avg_gap = 0.34

# 每个小矩形宽高比约 1.3:1（宽:高）
cell_ratio = 1.3

# ── Colorbar config: 自由调节 ────────────────────────────────────────────────
cbar_width = 0.010          # 图例宽度（相对整个 figure）
cbar_pad = 0.020            # 图例与热图水平间距
cbar_height_scale = 0.96    # 图例高度比例；1.0=与热图等高
cbar_y_shift = 0.0          # 图例上下微调；正数上移，负数下移

# ── Order models by category, then by open_avg desc ─────────────────────────
ordered_models = []
cat_members = []
for cat in cat_order:
    cat_df = df[df['category'] == cat].sort_values('open_avg', ascending=False)
    models = cat_df['model'].tolist()
    cat_members.append((cat, models))
    ordered_models.extend(models)

n_models = len(ordered_models)
n_tasks = len(open_tasks)

# ── Build original matrix: rows = tasks, cols = models ──────────────────────
mat = np.zeros((n_tasks, n_models))
for j, model in enumerate(ordered_models):
    row = df[df['model'] == model].iloc[0]
    for i, t in enumerate(open_tasks):
        mat[i, j] = row[t]

avg_row = mat.mean(axis=0, keepdims=True)
base_data = np.vstack([mat, avg_row])   # 8 rows total
row_labels = task_labels + ['Average']

# ── Best-performance mask per row ────────────────────────────────────────────
best_mask = np.zeros_like(base_data, dtype=bool)
for i in range(base_data.shape[0]):
    row_max = np.nanmax(base_data[i, :])
    best_mask[i, :] = np.isclose(base_data[i, :], row_max, atol=1e-8)

# ── Colormap ─────────────────────────────────────────────────────────────────
cmap = LinearSegmentedColormap.from_list(
    'nature_contrast',
    [(0.0,  '#D1E5F0'),   # 0-40: 浅蓝（低分）
     (0.40, '#92C5DE'),   # 40
     (0.55, '#F7F7F7'),   # 55: 中性白
     (0.65, '#FDDBC7'),   # 65
     (0.75, '#F4A582'),   # 75
     (0.85, '#D6604D'),   # 85
     (1.0,  '#B2182B')],  # 100: 深红（高分）
    N=256
)
VMIN, VMAX = 0, 100

# ── Build custom x positions with small inter-category gaps ─────────────────
x_lefts = []
x_centers = []
x_labels = []
real_col_indices = []
cat_bounds = []   # (start_x, end_x, center_x, cat_name)

cur_x = 0.0
src_j = 0
for cat_idx, (cat, models) in enumerate(cat_members):
    start_x = cur_x
    for m in models:
        x_lefts.append(cur_x)
        x_centers.append(cur_x + 0.5)
        x_labels.append(m.replace('MDAgents-GPT4o', 'MDAgents (GPT-4o)').replace('MDAgents-DeepSeek', 'MDAgents(Deepseek-V3)'))
        real_col_indices.append(src_j)
        cur_x += 1.0
        src_j += 1
    end_x = cur_x
    center_x = (start_x + end_x) / 2
    cat_bounds.append((start_x, end_x, center_x, cat))
    if cat_idx < len(cat_members) - 1:
        cur_x += gap_cols

total_width = cur_x
n_rows = base_data.shape[0]

# ── Custom y positions with a gap before Average row ────────────────────────
y_bottoms = []
y_centers = []
cur_y = 0.0
for i in range(n_rows):
    y_bottoms.append(cur_y)
    y_centers.append(cur_y + 0.5)
    cur_y += 1.0
    if i == n_tasks - 1:   # add gap after task rows, before Average
        cur_y += avg_gap
total_height = cur_y

# ── Figure layout ────────────────────────────────────────────────────────────
fig_w = max(18, total_width * 0.54 + 3.0)
fig_h = max(7.4, total_height * 0.72 + 2.8)

fig, ax = plt.subplots(figsize=(fig_w, fig_h))

# ── Draw cells manually ──────────────────────────────────────────────────────
for j, x0 in enumerate(x_lefts):
    src_col = real_col_indices[j]
    for i in range(n_rows):
        y0 = y_bottoms[i]
        val = base_data[i, src_col]
        color = cmap((val - VMIN) / (VMAX - VMIN))
        rect = plt.Rectangle(
            (x0, y0), 1.0, 1.0,
            facecolor=color,
            edgecolor='white',
            linewidth=2.0
        )
        ax.add_patch(rect)

        # 统一黑字；若你后面想恢复自动黑白字，我也可以再给你切回去
        ax.text(
            x0 + 0.5, y0 + 0.5, f'{val:.1f}',
            ha='center', va='center',
            fontsize=12.0,
            fontweight='bold' if best_mask[i, src_col] else 'normal',
            color='black'
        )

# ── Axes settings ────────────────────────────────────────────────────────────
ax.set_xlim(0, total_width)
ax.set_ylim(total_height, -0.78)

# width:height ≈ 1.3:1
ax.set_aspect(1 / cell_ratio)

# ── X-axis: model names ──────────────────────────────────────────────────────
ax.set_xticks(x_centers)
ax.set_xticklabels(
    x_labels,
    rotation=45,
    ha='right',
    rotation_mode='anchor',
    fontsize=13,
    fontweight='normal',
    color='black'
)
ax.tick_params(axis='x', length=0, pad=10)

# ── Y-axis: task names ───────────────────────────────────────────────────────
ax.set_yticks(y_centers)
ax.set_yticklabels(
    row_labels,
    fontsize=13,
    fontweight='bold',
    color='black'
)
ax.tick_params(axis='y', length=0, pad=10)

# ── Category labels + underline ─────────────────────────────────────────────
# 让模型类型文字更贴近热图；横线与热图稍微拉开一点
top_text_y = -0.33
top_line_y = -0.14
for start_x, end_x, center_x, cat in cat_bounds:
    ax.text(
        center_x, top_text_y,
        cat,
        ha='center', va='bottom',
        fontsize=14,
        fontweight='bold',
        color='black',
        clip_on=False
    )
    ax.plot(
        [start_x + 0.06, end_x - 0.06],
        [top_line_y, top_line_y],
        color='black',
        lw=1.5,
        clip_on=False
    )

# ── Remove spines ────────────────────────────────────────────────────────────
for spine in ax.spines.values():
    spine.set_visible(False)

# ── Layout first, then add colorbar with free height ────────────────────────
plt.tight_layout(rect=[0.02, 0.03, 0.96, 0.98])

sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=VMIN, vmax=VMAX))
sm.set_array([])

ax_pos = ax.get_position()

# 自由控制图例位置和高度
cbar_h = ax_pos.height * cbar_height_scale
cbar_y = ax_pos.y0 + (ax_pos.height - cbar_h) / 2 + cbar_y_shift
cbar_x = ax_pos.x1 + cbar_pad

cax = fig.add_axes([cbar_x, cbar_y, cbar_width, cbar_h])

cbar = fig.colorbar(sm, cax=cax, orientation='vertical')
cbar.set_label(
    'ORACLE Score (%)',
    fontsize=13,
    fontweight='bold',
    color='black',
    labelpad=10
)
cbar.ax.tick_params(labelsize=11, width=0.8, colors='black')
cbar.outline.set_visible(True)
cbar.outline.set_linewidth(0.8)
cbar.outline.set_edgecolor('black')
for spine in cbar.ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(0.8)
    spine.set_edgecolor('black')

# ── Save (keep original filenames unchanged) ────────────────────────────────
pdf_path = f'{OUT_DIR}/open_tasks_heatmap.pdf'
png_path = f'{OUT_DIR}/open_tasks_heatmap.png'

plt.savefig(pdf_path, dpi=400, bbox_inches='tight', format='pdf')
plt.savefig(png_path, dpi=400, bbox_inches='tight')
plt.close()

print('✓ Saved:')
print(f'  {pdf_path}')
print(f'  {png_path}')