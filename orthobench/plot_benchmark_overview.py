#!/usr/bin/env python3
"""
Fig. 2: OrthoBench Overview — Nature journal-style multi-panel figure.

Panels:
  (a) Horizontal bar chart – task sample distribution
  (b) Grouped bar chart – ID/OOD × Rare/Non-rare quadrant
  (c) Donut/ring chart – ICD chapter distribution
  (d) Long-tail frequency distribution

Output: figures/fig2_benchmark_overview.pdf and .png
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

# ---------------------------------------------------------------------------
# Style setup (Nature journal)
# ---------------------------------------------------------------------------
NPG = {
    'red':        '#E64B35',
    'cyan':       '#4DBBD5',
    'green':      '#00A087',
    'gold':       '#F39B11',
    'blue':       '#3C5488',
    'grey_blue':  '#8491B4',
    'light_green':'#91D1C2',
    'brown':      '#B09C85',
}

# Try Arial first, fall back to DejaVu Sans
for font in ['Arial', 'DejaVu Sans']:
    try:
        matplotlib.font_manager.findfont(font, fallback_to_default=False)
        FONT_FAMILY = font
        break
    except Exception:
        continue
else:
    FONT_FAMILY = 'DejaVu Sans'

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': [FONT_FAMILY, 'DejaVu Sans', 'Arial'],
    'font.size': 8,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 7.5,
    'ytick.labelsize': 7.5,
    'legend.fontsize': 7,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'lines.linewidth': 0.8,
    'pdf.fonttype': 42,      # TrueType in PDF
    'ps.fonttype': 42,
    'savefig.dpi': 600,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'figure.dpi': 150,
})

# ---------------------------------------------------------------------------
# Hard-coded task data
# ---------------------------------------------------------------------------
TASKS = {
    'Task 1':  {'samples': 17713, 'cat': 'Diagnostic', 'desc': 'Admission Dx'},
    'Task 2':  {'samples': 17715, 'cat': 'Diagnostic', 'desc': 'Preoperative Dx'},
    'Task 3':  {'samples': 17400, 'cat': 'Diagnostic', 'desc': 'Postoperative Dx'},
    'Task 4':  {'samples': 17712, 'cat': 'Diagnostic', 'desc': 'Discharge Dx'},
    'Task 5':  {'samples': 20464, 'cat': 'Management', 'desc': 'Periop. assessment'},
    'Task 6':  {'samples': 8154,  'cat': 'Management', 'desc': 'Surgical plan'},
    'Task 7':  {'samples': 5875,  'cat': 'Management', 'desc': 'Operative note'},
    'Task 8':  {'samples': 13665, 'cat': 'Management', 'desc': 'Postop. orders'},
    'Task 9':  {'samples': 5866,  'cat': 'Management', 'desc': 'Discharge summary'},
    'Task 10': {'samples': 5618,  'cat': 'Management', 'desc': 'Rehab. plan'},
    'Task 11': {'samples': 5563,  'cat': 'Management', 'desc': 'Consultation'},
}

# Panel (b) hard-coded values
QUADRANT = {
    'ID\nNon-rare':  {'codes': 321, 'patients': 3051},
    'ID\nRare':      {'codes': 62,  'patients': 274},
    'OOD\nNon-rare': {'codes': 417, 'patients': 2220},
    'OOD\nRare':     {'codes': 200, 'patients': 360},
}

# ICD-10 chapter letter -> readable name
ICD_CHAPTER_NAMES = {
    'M': 'M – Musculoskeletal',
    'S': 'S – Injury',
    'D': 'D – Neoplasms / Blood',
    'C': 'C – Malignant neoplasms',
    'T': 'T – Injury / Poisoning',
    'Q': 'Q – Congenital',
    'G': 'G – Nervous system',
    'E': 'E – Endocrine',
    'L': 'L – Skin',
    'K': 'K – Digestive',
    'I': 'I – Circulatory',
    'A': 'A – Infectious',
    'N': 'N – Genitourinary',
    'R': 'R – Symptoms',
    'J': 'J – Respiratory',
    'H': 'H – Eye / Ear',
    'P': 'P – Perinatal',
    'B': 'B – Infectious',
    'F': 'F – Mental',
    'O': 'O – Pregnancy',
    'Z': 'Z – Health status',
}

# Distinct colors for ICD chapters
CHAPTER_COLORS = [
    '#E64B35', '#4DBBD5', '#00A087', '#F39B11', '#3C5488',
    '#8491B4', '#91D1C2', '#B09C85', '#DC0000', '#7E6148',
    '#20854E', '#FFDC91', '#6F99AD', '#EE4C97', '#D4A5A5',
    '#5B8FA8', '#725D68', '#A8D8EA', '#AA96DA', '#FCBAD3',
    '#C4E538',
]

# ---------------------------------------------------------------------------
# Load benchmark codes
# ---------------------------------------------------------------------------
DATA_CSV = Path('/path/to/orthopilot/gen_validation/test_final/split_stats_by_code.csv')

df = pd.read_csv(DATA_CSV, encoding='utf-8-sig')
bench = df[df['domain_by_class'].isin(['ID', 'OOD'])].copy()
bench['chapter'] = bench['code'].str[0]

print(f"Loaded {len(bench)} benchmark disease codes")

# ---------------------------------------------------------------------------
# Helper: remove top/right spines
# ---------------------------------------------------------------------------
def despine(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


# ---------------------------------------------------------------------------
# Build figure  (183 mm × 160 mm)
# ---------------------------------------------------------------------------
mm2in = 1 / 25.4
fig = plt.figure(figsize=(183 * mm2in, 165 * mm2in))

# GridSpec: 2 rows × 2 columns
gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.45,
                      left=0.09, right=0.95, top=0.95, bottom=0.06)

# ===== Panel (a): Horizontal bar chart =====
ax_a = fig.add_subplot(gs[0, 0])

task_names = list(TASKS.keys())
task_labels = [f"{k}: {v['desc']}" for k, v in TASKS.items()]
samples = [v['samples'] for v in TASKS.values()]
colors_a = [NPG['red'] if v['cat'] == 'Diagnostic' else NPG['blue']
            for v in TASKS.values()]

y_pos = np.arange(len(task_names))
bars = ax_a.barh(y_pos, samples, color=colors_a, height=0.65, edgecolor='white',
                 linewidth=0.3)

ax_a.set_yticks(y_pos)
ax_a.set_yticklabels(task_labels, fontsize=7)
ax_a.invert_yaxis()
ax_a.set_xlabel('Number of evaluation instances', fontsize=8)

# Annotate values
for i, (bar, val) in enumerate(zip(bars, samples)):
    ax_a.text(val + 200, bar.get_y() + bar.get_height() / 2,
              f'{val:,}', va='center', ha='left', fontsize=6.5)

# Mean line
mean_val = np.mean(samples)
ax_a.axvline(mean_val, color='grey', linestyle='--', linewidth=0.7, zorder=0)
ax_a.text(mean_val, len(task_names) - 0.2, f'mean={mean_val:,.0f}',
          ha='center', va='top', fontsize=6, color='grey')

ax_a.set_xlim(0, max(samples) * 1.18)
despine(ax_a)

# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=NPG['red'], label='Diagnostic'),
                   Patch(facecolor=NPG['blue'], label='Management')]
ax_a.legend(handles=legend_elements, loc='lower right', frameon=False,
            fontsize=7)

# Panel label
ax_a.text(-0.15, 1.08, '(a)', transform=ax_a.transAxes,
          fontsize=11, fontweight='bold', va='top')


# ===== Panel (b): Grouped bar chart — ID/OOD × Rare/Non-rare =====
ax_b = fig.add_subplot(gs[0, 1])

groups = list(QUADRANT.keys())
code_vals = [QUADRANT[g]['codes'] for g in groups]
patient_vals = [QUADRANT[g]['patients'] for g in groups]

x = np.arange(len(groups))
width = 0.32

bars_code = ax_b.bar(x - width / 2, code_vals, width,
                     color=NPG['blue'], label='Disease codes',
                     edgecolor='white', linewidth=0.3)
ax_b.set_ylabel('Number of disease codes', fontsize=8, color=NPG['blue'])
ax_b.set_ylim(0, 520)
ax_b.tick_params(axis='y', colors=NPG['blue'])
despine(ax_b)

ax_b2 = ax_b.twinx()
bars_pat = ax_b2.bar(x + width / 2, patient_vals, width,
                     color=NPG['red'], label='Patients',
                     edgecolor='white', linewidth=0.3)
ax_b2.set_ylabel('Number of patients', fontsize=8, color=NPG['red'])
ax_b2.set_ylim(0, 3600)
ax_b2.tick_params(axis='y', colors=NPG['red'])
ax_b2.spines['top'].set_visible(False)

ax_b.set_xticks(x)
ax_b.set_xticklabels(groups, fontsize=7)

# Annotate bars
for bar, val in zip(bars_code, code_vals):
    ax_b.text(bar.get_x() + bar.get_width() / 2, val + 10,
              str(val), ha='center', va='bottom', fontsize=6.5,
              color=NPG['blue'], fontweight='bold')
for bar, val in zip(bars_pat, patient_vals):
    ax_b2.text(bar.get_x() + bar.get_width() / 2, val + 50,
               f'{val:,}', ha='center', va='bottom', fontsize=6.5,
               color=NPG['red'], fontweight='bold')

# Combined legend
lines_b = [Patch(facecolor=NPG['blue'], label='Disease codes'),
           Patch(facecolor=NPG['red'], label='Patients')]
ax_b.legend(handles=lines_b, loc='upper right', frameon=False, fontsize=7)

ax_b.text(-0.15, 1.08, '(b)', transform=ax_b.transAxes,
          fontsize=11, fontweight='bold', va='top')


# ===== Panel (c): Donut/ring chart — ICD chapter distribution =====
ax_c = fig.add_subplot(gs[1, 0])

chapter_counts = bench['chapter'].value_counts().sort_values(ascending=False)

# Group small chapters into "Others"
THRESHOLD = 15  # chapters with fewer codes -> "Others"
major = chapter_counts[chapter_counts >= THRESHOLD]
minor_sum = chapter_counts[chapter_counts < THRESHOLD].sum()

labels_c = [ICD_CHAPTER_NAMES.get(ch, ch) for ch in major.index]
sizes_c = list(major.values)
if minor_sum > 0:
    labels_c.append('Others')
    sizes_c.append(minor_sum)

colors_c = CHAPTER_COLORS[:len(sizes_c)]

wedges, texts, autotexts = ax_c.pie(
    sizes_c, labels=None, autopct='',
    colors=colors_c, startangle=90,
    pctdistance=0.82, wedgeprops=dict(width=0.38, edgecolor='white', linewidth=0.5))

# Add percentage labels for slices ≥ 4%
total_c = sum(sizes_c)
for i, (wedge, size) in enumerate(zip(wedges, sizes_c)):
    pct = size / total_c * 100
    if pct >= 4:
        ang = (wedge.theta2 + wedge.theta1) / 2
        x_t = 0.7 * np.cos(np.radians(ang))
        y_t = 0.7 * np.sin(np.radians(ang))
        ax_c.text(x_t, y_t, f'{pct:.0f}%', ha='center', va='center',
                  fontsize=6.5, fontweight='bold', color='white')

# Center text
ax_c.text(0, 0, '1,000\ndiseases', ha='center', va='center',
          fontsize=9, fontweight='bold', color='#333333')

# Legend on the right
ax_c.legend(wedges, labels_c, loc='center left', bbox_to_anchor=(0.88, 0.5),
            fontsize=5.5, frameon=False, handlelength=0.9, handleheight=0.9,
            labelspacing=0.3)

ax_c.set_aspect('equal')
ax_c.text(-0.08, 1.08, '(c)', transform=ax_c.transAxes,
          fontsize=11, fontweight='bold', va='top')


# ===== Panel (d): Long-tail frequency distribution =====
ax_d = fig.add_subplot(gs[1, 1])

# Sort codes by patient count descending
bench_sorted = bench.sort_values('test_patient_count', ascending=False).reset_index(drop=True)
bench_sorted['rank'] = bench_sorted.index + 1

# Separate ID and OOD for coloring
id_mask = bench_sorted['domain_by_class'] == 'ID'
ood_mask = bench_sorted['domain_by_class'] == 'OOD'

# Plot as scatter (small dots) colored by domain
ax_d.scatter(bench_sorted.loc[id_mask, 'rank'],
             bench_sorted.loc[id_mask, 'test_patient_count'],
             c=NPG['blue'], s=4, alpha=0.6, label='ID', zorder=2,
             edgecolors='none')
ax_d.scatter(bench_sorted.loc[ood_mask, 'rank'],
             bench_sorted.loc[ood_mask, 'test_patient_count'],
             c=NPG['red'], s=4, alpha=0.6, label='OOD', zorder=2,
             edgecolors='none')

# Overlay a smooth line (overall trend)
ax_d.plot(bench_sorted['rank'], bench_sorted['test_patient_count'],
          color='#333333', linewidth=0.5, alpha=0.4, zorder=1)

ax_d.set_yscale('log')
ax_d.set_xlabel('Disease code rank', fontsize=8)
ax_d.set_ylabel('Number of patients (log scale)', fontsize=8)
ax_d.set_xlim(0, len(bench_sorted) + 10)

# Median
median_patients = bench_sorted['test_patient_count'].median()
median_rank = bench_sorted.loc[bench_sorted['test_patient_count'] <= median_patients, 'rank'].iloc[0]
ax_d.axhline(median_patients, color=NPG['gold'], linestyle='--', linewidth=0.7, zorder=0)
ax_d.annotate(f'median = {median_patients:.0f}',
              xy=(len(bench_sorted) * 0.55, median_patients),
              xytext=(len(bench_sorted) * 0.6, median_patients * 3),
              fontsize=6.5, color=NPG['gold'], fontweight='bold',
              arrowprops=dict(arrowstyle='->', color=NPG['gold'], lw=0.6))

despine(ax_d)
ax_d.legend(loc='upper right', frameon=False, fontsize=7, markerscale=2)

ax_d.text(-0.15, 1.08, '(d)', transform=ax_d.transAxes,
          fontsize=11, fontweight='bold', va='top')

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
out_dir = Path('/path/to/orthopilot/project/benchmark/figures')
out_dir.mkdir(parents=True, exist_ok=True)

fig.savefig(out_dir / 'fig2_benchmark_overview.pdf', format='pdf')
fig.savefig(out_dir / 'fig2_benchmark_overview.png', format='png')
plt.close(fig)

print(f"Saved to {out_dir / 'fig2_benchmark_overview.pdf'}")
print(f"Saved to {out_dir / 'fig2_benchmark_overview.png'}")
print("Done.")
