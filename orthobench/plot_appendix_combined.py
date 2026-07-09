#!/usr/bin/env python3
"""
Combined Appendix Figure: OrthoBench Benchmark Statistics (Extended Data)
Layout: 2 rows × 3 columns (a–f).

Row 1: (a) Task samples, (b) ID/OOD × Rare/Non-rare, (c) ICD chapter distribution
Row 2: (d) Long-tail frequency, (e) ID vs OOD by chapter, (f) Rare vs Non-rare by chapter

Style: soft pink/blue colour scheme matching the manuscript's main figures.
Output: figures/ext_fig_benchmark_combined.pdf and .png
"""

import matplotlib
matplotlib.use('Agg')

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

# ── Colour scheme ─────────────────────────────────────────────────────
DIAGNOSTIC = '#92B1D9'
MANAGEMENT = '#F6C8B6'
CODES = '#7FA6C8'
PATIENTS = '#D9B7CA'
ID_COLOR = '#A8C6DD'
OOD_COLOR = '#E8A49A'
NONRARE_COLOR = '#C1D8E9'
RARE_COLOR = '#DBDDEF'
CHAPTER_PALETTE = ['#92B1D9', '#C1D8E9', '#DBDDEF', '#F6C8B6', '#D4D4D4']
GOLD      = '#B89B2E'
GREY      = '#999999'
DARK      = '#333333'

# ── Font setup ────────────────────────────────────────────────────────
for _font in ['Arial', 'DejaVu Sans']:
    try:
        matplotlib.font_manager.findfont(_font, fallback_to_default=False)
        FONT_FAMILY = _font
        break
    except Exception:
        continue
else:
    FONT_FAMILY = 'DejaVu Sans'

plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.sans-serif':    [FONT_FAMILY, 'DejaVu Sans', 'Arial'],
    'font.size':          10.2,
    'axes.titlesize':     11.0,
    'axes.labelsize':     10.8,
    'xtick.labelsize':    9.2,
    'ytick.labelsize':    9.2,
    'legend.fontsize':    9.0,
    'axes.linewidth':     0.65,
    'xtick.major.width':  0.55,
    'ytick.major.width':  0.55,
    'xtick.major.size':   3.2,
    'ytick.major.size':   3.2,
    'lines.linewidth':    0.9,
    'pdf.fonttype':       42,
    'ps.fonttype':        42,
    'savefig.dpi':        600,
    'savefig.bbox':       'tight',
    'savefig.pad_inches': 0.04,
})

MM = 1 / 25.4

# ── Data ──────────────────────────────────────────────────────────────
TASKS = {
    'Task 1':  {'samples': 17713, 'cat': 'Diagnostic', 'desc': 'Admission diagnosis'},
    'Task 2':  {'samples': 17715, 'cat': 'Diagnostic', 'desc': 'Preoperative diagnosis'},
    'Task 3':  {'samples': 17400, 'cat': 'Diagnostic', 'desc': 'Postoperative diagnosis'},
    'Task 4':  {'samples': 17712, 'cat': 'Diagnostic', 'desc': 'Discharge diagnosis'},
    'Task 5':  {'samples': 20464, 'cat': 'Management', 'desc': 'Perioperative assessment'},
    'Task 6':  {'samples':  8154, 'cat': 'Management', 'desc': 'Surgical planning'},
    'Task 7':  {'samples':  5875, 'cat': 'Management', 'desc': 'Preoperative orders'},
    'Task 8':  {'samples': 13665, 'cat': 'Management', 'desc': 'Postoperative orders'},
    'Task 9':  {'samples':  5866, 'cat': 'Management', 'desc': 'Discharge summary'},
    'Task 10': {'samples':  5618, 'cat': 'Management', 'desc': 'Rehabilitation planning'},
    'Task 11': {'samples':  5563, 'cat': 'Management', 'desc': 'Multidisciplinary consultation'},
}

QUADRANT = {
    'ID\nNon-rare':  {'codes': 321, 'patients': 3051},
    'ID\nRare':      {'codes':  62, 'patients':  274},
    'OOD\nNon-rare': {'codes': 417, 'patients': 2220},
    'OOD\nRare':     {'codes': 200, 'patients':  360},
}

CHAPTERS = ['M', 'S', 'D', 'C', 'T', 'Q', 'R', 'G', 'L', 'A',
            'Z', 'E', 'I', 'Other']
ID_COUNTS   = [127, 109, 34, 39, 19, 16,  9,  7,  2,  6,  9,  4,  2,  0]
OOD_COUNTS  = [182, 145, 81, 67, 31, 31, 17, 14, 15,  8,  4,  7,  8,  7]
NONRARE     = [260, 245, 55, 27, 47, 11, 26, 17, 14,  3, 13,  6,  7,  7]
RARE        = [ 49,   9, 60, 79,  3, 36,  0,  4,  3, 11,  0,  5,  3,  0]

ICD_NAMES = {
    'M': 'Musculoskeletal', 'S': 'Injury', 'D': 'Neoplasms/Blood',
    'C': 'Malignant neo.', 'T': 'Trauma/Comp.',
    'Q': 'Congenital', 'R': 'Symptoms', 'G': 'Nervous sys.',
    'L': 'Skin', 'A': 'Infectious', 'Z': 'Health status',
    'E': 'Endocrine', 'I': 'Circulatory', 'Other': 'Other',
}

CSV_PATH = ('/path/to/'
            'Bone/gen_validation/test_final/split_stats_by_code.csv')
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')
os.makedirs(OUT_DIR, exist_ok=True)


def despine(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def panel_label(ax, label, x=-0.09, y=1.13):
    ax.text(x, y, label, transform=ax.transAxes,
            fontsize=18, fontweight='bold', va='top', ha='left',
            fontfamily=FONT_FAMILY)


def patch_legend(ax, items, **kwargs):
    handles = [Patch(facecolor=color, edgecolor='none', label=label) for label, color in items]
    return ax.legend(handles=handles, frameon=False, handlelength=1.3,
                     handleheight=0.75, borderaxespad=0.25, labelspacing=0.35,
                     handletextpad=0.45, **kwargs)


def main():
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    bench = df[df['domain_by_class'].isin(['ID', 'OOD'])].copy()
    bench['chapter'] = bench['code'].str[0]

    # ── Figure: 2 rows × 3 cols ──────────────────────────────────────
    fig = plt.figure(figsize=(245 * MM, 172 * MM))

    gs = gridspec.GridSpec(
        2, 3, figure=fig,
        hspace=0.56, wspace=0.72,
        left=0.145, right=0.985, top=0.94, bottom=0.115,
        width_ratios=[1.55, 1.22, 1.42],
    )

    # ═══ Panel (a): Task sample distribution ═══════════════════════
    ax_a = fig.add_subplot(gs[0, 0])

    task_labels = [f"T{k.split()[1]}: {v['desc']}" for k, v in TASKS.items()]
    samples = [v['samples'] for v in TASKS.values()]
    colors_a = [DIAGNOSTIC if v['cat'] == 'Diagnostic' else MANAGEMENT
                for v in TASKS.values()]

    y_pos = np.arange(len(TASKS))
    bars_a = ax_a.barh(y_pos, samples, color=colors_a, height=0.62,
                       edgecolor='white', linewidth=0.4)

    ax_a.set_yticks(y_pos)
    ax_a.set_yticklabels(task_labels, fontsize=9.2)
    ax_a.invert_yaxis()
    ax_a.set_xlabel('Evaluation instances')

    for bar, val in zip(bars_a, samples):
        ax_a.text(val + 220, bar.get_y() + bar.get_height() / 2,
                  f'{val:,}', va='center', ha='left', fontsize=8.4,
                  color=DARK)

    mean_val = np.mean(samples)
    ax_a.axvline(mean_val, color=GREY, linestyle='--', linewidth=0.5,
                 zorder=0)

    ax_a.set_xlim(0, max(samples) * 1.25)
    despine(ax_a)
    patch_legend(ax_a, [('Diagnostic', DIAGNOSTIC), ('Management', MANAGEMENT)],
                 loc='lower right', fontsize=9.0)
    panel_label(ax_a, 'a')

    # ═══ Panel (b): ID/OOD × Rare/Non-rare ═══════════════════════
    ax_b = fig.add_subplot(gs[0, 1])

    groups = list(QUADRANT.keys())
    code_vals = [QUADRANT[g]['codes'] for g in groups]
    patient_vals = [QUADRANT[g]['patients'] for g in groups]

    x_b = np.arange(len(groups))
    w_b = 0.30

    bars_code = ax_b.bar(x_b - w_b / 2, code_vals, w_b, color=CODES,
                         edgecolor='white', linewidth=0.4,
                         label='Disease codes')
    ax_b.set_ylabel('Disease codes', color=DARK, fontsize=9.0)
    ax_b.set_ylim(0, 560)
    ax_b.tick_params(axis='y', colors=DARK)
    despine(ax_b)

    ax_b2 = ax_b.twinx()
    bars_pat = ax_b2.bar(x_b + w_b / 2, patient_vals, w_b, color=PATIENTS,
                         edgecolor='white', linewidth=0.4,
                         label='Patients')
    ax_b2.set_ylabel('Patients', color=DARK, fontsize=9.0, labelpad=4)
    ax_b2.set_ylim(0, 3900)
    ax_b2.set_yticks([])          # hide right-axis ticks to avoid overlap with (c)
    ax_b2.spines['top'].set_visible(False)

    ax_b.set_xticks(x_b)
    ax_b.set_xticklabels(groups, fontsize=9.0)

    for bar, val in zip(bars_code, code_vals):
        ax_b.text(bar.get_x() + bar.get_width() / 2, val + 10,
                  str(val), ha='center', va='bottom', fontsize=8.3,
                  color=DARK, fontweight='normal')
    for bar, val in zip(bars_pat, patient_vals):
        ax_b2.text(bar.get_x() + bar.get_width() / 2, val + 55,
                   f'{val:,}', ha='center', va='bottom', fontsize=8.3,
                   color=DARK, fontweight='normal')

    patch_legend(ax_b, [('Disease codes', CODES), ('Patients', PATIENTS)],
                 loc='upper right', fontsize=9.0)
    panel_label(ax_b, 'b')

    # ═══ Panel (c): ICD chapter distribution ═══════════════════════
    ax_c = fig.add_subplot(gs[0, 2])

    chapter_counts = bench['chapter'].value_counts()
    major_mask = chapter_counts >= 10
    major = chapter_counts[major_mask].sort_values(ascending=True)
    minor_sum = chapter_counts[~major_mask].sum()
    if minor_sum > 0:
        major = pd.concat([pd.Series({'Other': minor_sum}), major])

    labels_c = [f"{ch} ({ICD_NAMES.get(ch, ch)})" for ch in major.index]
    values_c = major.values
    colors_c = [CHAPTER_PALETTE[i % len(CHAPTER_PALETTE)] for i in range(len(values_c))]

    y_c = np.arange(len(labels_c))
    bars_c = ax_c.barh(y_c, values_c, height=0.58, color=colors_c,
                       edgecolor='white', linewidth=0.4)
    ax_c.set_yticks(y_c)
    ax_c.set_yticklabels(labels_c, fontsize=8.4)
    ax_c.set_xlabel('Disease codes')

    for bar, val in zip(bars_c, values_c):
        ax_c.text(val + 3, bar.get_y() + bar.get_height() / 2,
                  str(int(val)), va='center', ha='left', fontsize=8.0,
                  color=DARK)

    ax_c.set_xlim(0, max(values_c) * 1.17)
    despine(ax_c)
    panel_label(ax_c, 'c')

    # ═══ Panel (d): Long-tail frequency ════════════════════════════
    ax_d = fig.add_subplot(gs[1, 0])

    bench_sorted = (bench.sort_values('test_patient_count', ascending=False)
                         .reset_index(drop=True))
    bench_sorted['rank'] = bench_sorted.index + 1

    id_mask = bench_sorted['domain_by_class'] == 'ID'
    ood_mask = bench_sorted['domain_by_class'] == 'OOD'

    ax_d.scatter(bench_sorted.loc[id_mask, 'rank'],
                 bench_sorted.loc[id_mask, 'test_patient_count'],
                 c=ID_COLOR, s=5, alpha=0.62, label='ID', zorder=2,
                 edgecolors='none')
    ax_d.scatter(bench_sorted.loc[ood_mask, 'rank'],
                 bench_sorted.loc[ood_mask, 'test_patient_count'],
                 c=OOD_COLOR, s=5, alpha=0.62, label='OOD', zorder=2,
                 edgecolors='none')

    ax_d.plot(bench_sorted['rank'], bench_sorted['test_patient_count'],
              color=GREY, linewidth=0.3, alpha=0.3, zorder=1)

    ax_d.set_yscale('log')
    ax_d.set_xlabel('Disease code rank')
    ax_d.set_ylabel('Patients (log scale)')
    ax_d.set_xlim(0, len(bench_sorted) + 10)

    median_p = bench_sorted['test_patient_count'].median()
    ax_d.axhline(median_p, color=GOLD, linestyle='--', linewidth=0.5,
                 zorder=0)
    ax_d.annotate(
        f'median = {median_p:.0f}',
        xy=(len(bench_sorted) * 0.50, median_p),
        xytext=(len(bench_sorted) * 0.56, median_p * 4),
        fontsize=9.0, color=DARK, fontweight='normal',
        arrowprops=dict(arrowstyle='->', color=GOLD, lw=0.65))

    despine(ax_d)
    patch_legend(ax_d, [('ID', ID_COLOR), ('OOD', OOD_COLOR)],
                 loc='upper right', fontsize=9.0)
    panel_label(ax_d, 'd')

    # ═══ Panel (e): ID vs OOD by chapter ═══════════════════════════
    ax_e = fig.add_subplot(gs[1, 1])

    x_e = np.arange(len(CHAPTERS))
    w_e = 0.35

    ax_e.bar(x_e - w_e / 2, ID_COUNTS, w_e, color=ID_COLOR, label='ID',
             edgecolor='white', linewidth=0.3)
    ax_e.bar(x_e + w_e / 2, OOD_COUNTS, w_e, color=OOD_COLOR, label='OOD',
             edgecolor='white', linewidth=0.3)

    ax_e.set_xticks(x_e)
    ax_e.set_xticklabels(CHAPTERS, fontsize=9.0, rotation=45, ha='right')
    ax_e.set_ylabel('Disease codes')
    ax_e.set_xlabel('ICD-10 chapter')
    despine(ax_e)

    for i in range(len(CHAPTERS)):
        if ID_COUNTS[i] >= 80:
            ax_e.text(x_e[i] - w_e / 2, ID_COUNTS[i] + 2,
                      str(ID_COUNTS[i]), ha='center', va='bottom',
                      fontsize=8.0, color=DARK)
        if OOD_COUNTS[i] >= 80:
            ax_e.text(x_e[i] + w_e / 2, OOD_COUNTS[i] + 2,
                      str(OOD_COUNTS[i]), ha='center', va='bottom',
                      fontsize=8.0, color=DARK)

    patch_legend(ax_e, [('ID', ID_COLOR), ('OOD', OOD_COLOR)],
                 loc='upper right', fontsize=9.0)
    panel_label(ax_e, 'e')

    # ═══ Panel (f): Rare vs Non-rare by chapter ═══════════════════
    ax_f = fig.add_subplot(gs[1, 2])

    ax_f.bar(x_e - w_e / 2, NONRARE, w_e, color=NONRARE_COLOR, label='Non-rare',
             edgecolor='white', linewidth=0.3)
    ax_f.bar(x_e + w_e / 2, RARE, w_e, color=RARE_COLOR, label='Rare',
             edgecolor='white', linewidth=0.3)

    ax_f.set_xticks(x_e)
    ax_f.set_xticklabels(CHAPTERS, fontsize=9.0, rotation=45, ha='right')
    ax_f.set_ylabel('Disease codes')
    ax_f.set_xlabel('ICD-10 chapter')
    despine(ax_f)

    for i in range(len(CHAPTERS)):
        if NONRARE[i] >= 100:
            ax_f.text(x_e[i] - w_e / 2, NONRARE[i] + 2,
                      str(NONRARE[i]), ha='center', va='bottom',
                      fontsize=8.0, color=DARK)
        if RARE[i] >= 70:
            ax_f.text(x_e[i] + w_e / 2, RARE[i] + 2,
                      str(RARE[i]), ha='center', va='bottom',
                      fontsize=8.0, color=DARK)

    patch_legend(ax_f, [('Non-rare', NONRARE_COLOR), ('Rare', RARE_COLOR)],
                 loc='upper right', fontsize=9.0)
    panel_label(ax_f, 'f')

    # ── Save ──────────────────────────────────────────────────────────
    for ext in ['pdf', 'png']:
        path = os.path.join(OUT_DIR, f'ext_fig_benchmark_combined.{ext}')
        fig.savefig(path, format=ext, facecolor='white')
        print(f"Saved: {path}")
    plt.close(fig)
    print("Done!")


if __name__ == '__main__':
    main()
