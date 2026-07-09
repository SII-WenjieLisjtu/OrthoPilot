#!/usr/bin/env python3
"""
Heatmap for open-ended tasks (5–11) — Nature journal style (horizontal).
Rows = 7 tasks + Average, Columns = models grouped by category.
All fonts: black Arial. Bold labels, larger scores with %, bold = best per task.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec

# ── Global style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':       'sans-serif',
    'font.sans-serif':   ['Arial', 'Liberation Sans', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'text.color':        'black',
    'axes.labelcolor':   'black',
    'xtick.color':       'black',
    'ytick.color':       'black',
})

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_FILE = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv'
OUT_DIR   = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/figure/task_grouping'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load & filter ────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_FILE)
df = df[~df['model'].isin(['Qwen3-8B', 'HuatuoGPT-o1-7B'])].copy()

# ── Task definitions (full names) ────────────────────────────────────────────
open_tasks  = [f'task{i}' for i in range(5, 12)]
task_labels = [
    'Perioperative risk assessment',
    'Surgical approach selection',
    'Operative note generation',
    'Postoperative order writing',
    'Discharge summary generation',
    'Rehabilitation planning',
    'Multidisciplinary consultation',
]

# ── Category config ──────────────────────────────────────────────────────────
cat_order  = ['Ours', 'Reasoning LLMs', 'General LLMs', 'Medical LLMs']
cat_colors = {
    'Ours':            '#1565C0',
    'Reasoning LLMs':  '#6A1B9A',
    'General LLMs':    '#2E7D32',
    'Medical LLMs':    '#C62828',
}

# ── Order models: by category, then open_avg desc ────────────────────────────
ordered_models = []
cat_bounds     = []

for cat in cat_order:
    cat_df = df[df['category'] == cat].sort_values('open_avg', ascending=False)
    start  = len(ordered_models)
    ordered_models.extend(cat_df['model'].tolist())
    cat_bounds.append((start, len(ordered_models), cat))

n_models = len(ordered_models)
n_tasks  = len(open_tasks)

# ── Build transposed data: rows=tasks, cols=models ──────────────────────────
mat = np.zeros((n_tasks, n_models))
for j, model in enumerate(ordered_models):
    row = df[df['model'] == model].iloc[0]
    for i, t in enumerate(open_tasks):
        mat[i, j] = row[t]

avg_row    = mat.mean(axis=0, keepdims=True)
data       = np.vstack([mat, avg_row])
n_rows     = n_tasks + 1
row_labels = task_labels + ['Average']

# ── Best per task (row-wise argmax) ─────────────────────────────────���────────
best_per_row = np.argmax(data, axis=1)

# ── Colormap: light-to-medium blue (black text always readable) ──────────────
cmap = LinearSegmentedColormap.from_list('nature_blue', [
    '#F7FBFF', '#DEEBF7', '#C6DBEF', '#9ECAE1',
    '#6BAED6', '#4292C6', '#2B8CBE'], N=256)
VMIN, VMAX = 15, 92

# ── Figure with GridSpec: category bar on top + heatmap + colorbar ───────────
fig = plt.figure(figsize=(17, 7.2))
gs  = GridSpec(2, 2, figure=fig,
               height_ratios=[0.055, 1],
               width_ratios=[1, 0.018],
               hspace=0.025, wspace=0.012)

ax_cat  = fig.add_subplot(gs[0, 0])
ax_main = fig.add_subplot(gs[1, 0])
ax_cbar = fig.add_subplot(gs[1, 1])

# ═══════════════════════════════════════════════════════════════════════════════
# Category colour bar (top strip)
# ═══════════════════════════════════════════════════════════════════════════════
ax_cat.set_xlim(-0.5, n_models - 0.5)
ax_cat.set_ylim(0, 1)
for start, end, cat in cat_bounds:
    w = end - start
    rect = mpatches.FancyBboxPatch(
        (start - 0.42, 0.08), w - 0.16, 0.84,
        boxstyle='round,pad=0.04',
        facecolor=cat_colors[cat], alpha=0.16,
        edgecolor=cat_colors[cat], linewidth=2.0)
    ax_cat.add_patch(rect)
    mid = (start + end - 1) / 2
    ax_cat.text(mid, 0.50, cat, ha='center', va='center',
                fontsize=10.5, fontweight='bold', color='black')
ax_cat.axis('off')

# ═══════════════════════════════════════════════════════════════════════════════
# Main heatmap
# ═══════════════════════════════════════════════════════════════════════════════
im = ax_main.imshow(data, cmap=cmap, aspect='auto', vmin=VMIN, vmax=VMAX)

# ── Cell annotations (% sign, bold = best) ──────────────────────────────────
for i in range(n_rows):
    for j in range(n_models):
        val     = data[i, j]
        is_best = (j == best_per_row[i])
        ax_main.text(j, i, f'{val:.1f}%',
                     ha='center', va='center',
                     fontsize=9.3,
                     fontweight='bold' if is_best else 'normal',
                     color='black')

# ── White grid ───────────────────────────────────────────────────────────────
for i in range(n_rows + 1):
    ax_main.axhline(y=i - 0.5, color='white', lw=1.6, zorder=2)
for j in range(n_models + 1):
    ax_main.axvline(x=j - 0.5, color='white', lw=1.6, zorder=2)

# ── Category vertical separators ────────────────────────────────────────────
for start, end, cat in cat_bounds:
    if start > 0:
        ax_main.axvline(x=start - 0.5, color='#444444', lw=1.8, zorder=4)

# ── Average row separator ───────────────────────────────────────────────────
ax_main.axhline(y=n_tasks - 0.5, color='#444444', lw=1.8, zorder=4)

# ── Y-axis: full task names, bold ────────────────────────────────────────────
ax_main.set_yticks(range(n_rows))
ax_main.set_yticklabels(row_labels, fontsize=11, fontweight='bold',
                        color='black')
ax_main.tick_params(axis='y', length=0, pad=10)

# ── X-axis: model names, bold, rotated 45° ──────────────────────────────────
display_names = []
for m in ordered_models:
    if m == 'OrthoPilot':
        display_names.append('OrthoPilot (agent)')
    else:
        display_names.append(m)

ax_main.set_xticks(range(n_models))
ax_main.set_xticklabels(display_names, fontsize=9.8, fontweight='bold',
                        color='black', rotation=45, ha='right',
                        rotation_mode='anchor')
ax_main.tick_params(axis='x', length=0, pad=4)

# ── Spines off ───────────────────────────────────────────────────────────────
for spine in ax_main.spines.values():
    spine.set_visible(False)

# ═══════════════════════════════════════════════════════════════════════════════
# Colorbar (legend)
# ═══════════════════════════════════════════════════════════════════════════════
cb = plt.colorbar(im, cax=ax_cbar)
cb.set_label('ORACLE Score (%)', fontsize=11, fontweight='bold',
             color='black', labelpad=12)
cb.ax.tick_params(labelsize=9.5, width=0.6, color='black')
for lbl in cb.ax.get_yticklabels():
    lbl.set_color('black')
cb.outline.set_linewidth(0.6)

# ── Save ─────────────────────────────────────────────────────────────────────
plt.savefig(f'{OUT_DIR}/open_tasks_heatmap.pdf', dpi=300,
            bbox_inches='tight', format='pdf')
plt.savefig(f'{OUT_DIR}/open_tasks_heatmap.png', dpi=300,
            bbox_inches='tight')
plt.close()
print('✓ Saved: open_tasks_heatmap.pdf / .png')
print(f'  → {OUT_DIR}/')
