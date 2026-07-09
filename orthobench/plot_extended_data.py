#!/usr/bin/env python3
"""Extended Data figures for the manuscript (Nature style)."""

import matplotlib
matplotlib.use('Agg')

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap

# ── Nature / NPG palette ──────────────────────────────────────────────
RED     = '#E64B35'
CYAN    = '#4DBBD5'
GREEN   = '#00A087'
GOLD    = '#F39B11'
BLUE    = '#3C5488'
GREY    = '#8491B4'
LTGREEN = '#91D1C2'
BROWN   = '#B09C85'

# ── Global rcParams (Nature style) ────────────────────────────────────
plt.rcParams.update({
    'font.family':       'sans-serif',
    'font.sans-serif':   ['Arial', 'DejaVu Sans'],
    'font.size':         8,
    'axes.linewidth':    0.6,
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'lines.linewidth':   0.8,
    'savefig.dpi':       600,
    'savefig.bbox':      'tight',
    'savefig.pad_inches': 0.02,
    'pdf.fonttype':      42,   # editable text in PDF
    'ps.fonttype':       42,
})

MM = 1 / 25.4  # mm → inches

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

CSV_PATH = ('/path/to/'
            'Bone/gen_validation/test_final/split_stats_by_code.csv')

# Read CSV (utf-8-sig handles BOM)
df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
df = df[df['domain_by_class'].isin(['ID', 'OOD'])].copy()


# ======================================================================
# Figure 1 – Question‑type distribution  (Extended Data Fig. X-2)
# ======================================================================
def fig_question_types():
    tasks = ['Task 1', 'Task 2', 'Task 3', 'Task 4']
    open_vals = [5905, 5905, 5800, 5904]
    mc_vals   = [5904, 5905, 5800, 5904]
    tf_vals   = [5904, 5905, 5800, 5904]

    fig, ax = plt.subplots(figsize=(89 * MM, 70 * MM))

    y = np.arange(len(tasks))
    h = 0.55

    lefts = np.zeros(len(tasks))
    colors = [RED, CYAN, GREEN]
    labels = ['Open-ended', 'Multiple-choice', 'True-or-false']
    all_vals = [open_vals, mc_vals, tf_vals]

    for vals, color, label in zip(all_vals, colors, labels):
        bars = ax.barh(y, vals, height=h, left=lefts, color=color,
                       edgecolor='white', linewidth=0.3, label=label)
        # percentage labels inside each segment
        for i, (v, l) in enumerate(zip(vals, lefts)):
            total = open_vals[i] + mc_vals[i] + tf_vals[i]
            pct = v / total * 100
            cx = l + v / 2
            ax.text(cx, y[i], f'{pct:.1f}%', ha='center', va='center',
                    fontsize=7, color='white', fontweight='bold')
        lefts = lefts + np.array(vals)

    ax.set_yticks(y)
    ax.set_yticklabels(tasks)
    ax.set_xlabel('Number of instances', fontsize=8)
    ax.invert_yaxis()
    ax.legend(fontsize=7, loc='upper right', frameon=False,
              bbox_to_anchor=(1.0, -0.12), ncol=3)

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f'{int(x):,}'))

    for fmt in ('pdf', 'png'):
        fig.savefig(os.path.join(OUT_DIR, f'ext_fig_question_types.{fmt}'))
    plt.close(fig)
    print('  [done] ext_fig_question_types')


# ======================================================================
# Figure 2 – Disease distribution details  (Extended Data Fig. X-3)
# ======================================================================
def fig_disease_details():
    chapters = ['M', 'S', 'D', 'C', 'T', 'Q', 'R', 'G', 'L', 'A',
                'Z', 'E', 'I', 'Other']

    # (a) ID vs OOD
    id_counts  = [127, 109, 34, 39, 19, 16,  9,  7,  2,  6,  9,  4,  2,  0]
    ood_counts = [182, 145, 81, 67, 31, 31, 17, 14, 15,  8,  4,  7,  8,  7]

    # (b) Non-rare vs Rare
    nonrare = [260, 245, 55, 27, 47, 11, 26, 17, 14,  3, 13,  6,  7,  7]
    rare    = [ 49,   9, 60, 79,  3, 36,  0,  4,  3, 11,  0,  5,  3,  0]

    fig, axes = plt.subplots(1, 3, figsize=(183 * MM, 180 * MM),
                             gridspec_kw={'width_ratios': [1, 1, 0.9]})

    x = np.arange(len(chapters))
    w = 0.6

    # ── panel (a) ─────────────────────────────────────────────────────
    ax = axes[0]
    ax.bar(x, id_counts,  width=w, color=BLUE, label='ID')
    ax.bar(x, ood_counts, width=w, bottom=id_counts, color=RED, label='OOD')
    ax.set_xticks(x)
    ax.set_xticklabels(chapters, fontsize=7, rotation=45, ha='right')
    ax.set_ylabel('Number of disease codes', fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title('a', fontsize=10, fontweight='bold', loc='left', pad=6)

    # ── panel (b) ─────────────────────────────────────────────────────
    ax = axes[1]
    ax.bar(x, nonrare, width=w, color=GREY, label='Non-rare')
    ax.bar(x, rare,    width=w, bottom=nonrare, color=GOLD, label='Rare')
    ax.set_xticks(x)
    ax.set_xticklabels(chapters, fontsize=7, rotation=45, ha='right')
    ax.set_ylabel('Number of disease codes', fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title('b', fontsize=10, fontweight='bold', loc='left', pad=6)

    # ── panel (c) – 2×2 heatmap ──────────────────────────────────────
    ax = axes[2]
    codes_mat   = np.array([[321, 62], [417, 200]])
    patient_mat = np.array([[3051, 274], [2220, 360]])

    cmap = LinearSegmentedColormap.from_list(
        'light_blue', ['#D6E6F2', BLUE], N=256)
    im = ax.imshow(patient_mat, cmap=cmap, aspect='auto')

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Non-rare', 'Rare'], fontsize=8)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['ID', 'OOD'], fontsize=8)
    ax.tick_params(top=False, bottom=True, left=True, right=False)

    # restore spines for heatmap
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.6)

    # annotations in each cell
    for i in range(2):
        for j in range(2):
            c = codes_mat[i, j]
            p = patient_mat[i, j]
            # pick text color for contrast
            tc = 'white' if p > 1500 else 'black'
            ax.text(j, i - 0.12, f'{c}', ha='center', va='center',
                    fontsize=9, fontweight='bold', color=tc)
            ax.text(j, i + 0.16, f'({p:,} patients)', ha='center',
                    va='center', fontsize=6.5, color=tc)

    # marginal totals
    row_codes = codes_mat.sum(axis=1)
    row_pat   = patient_mat.sum(axis=1)
    col_codes = codes_mat.sum(axis=0)
    col_pat   = patient_mat.sum(axis=0)

    for i in range(2):
        ax.text(2.15, i, f'{row_codes[i]} / {row_pat[i]:,}',
                ha='left', va='center', fontsize=6.5, color='#333333',
                clip_on=False)
    for j in range(2):
        ax.text(j, 2.25, f'{col_codes[j]} / {col_pat[j]:,}',
                ha='center', va='top', fontsize=6.5, color='#333333',
                clip_on=False)

    ax.set_title('c', fontsize=10, fontweight='bold', loc='left', pad=6)

    # colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.08, shrink=0.6)
    cbar.set_label('Patient count', fontsize=7)
    cbar.ax.tick_params(labelsize=6)

    fig.subplots_adjust(wspace=0.45, bottom=0.10, top=0.93)

    for fmt in ('pdf', 'png'):
        fig.savefig(os.path.join(OUT_DIR, f'ext_fig_disease_details.{fmt}'))
    plt.close(fig)
    print('  [done] ext_fig_disease_details')


# ======================================================================
if __name__ == '__main__':
    print('Generating Extended Data figures …')
    fig_question_types()
    fig_disease_details()
    print('All figures saved to:', OUT_DIR)
