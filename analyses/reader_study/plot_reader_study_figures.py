#!/usr/bin/env python3
"""
Reader Study Figures — Nature style
====================================
Palette: #92B1D9, #C1D8E9, #DBDDEF, #F6C8B6, #D4D4D4
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.stats import gaussian_kde
from pathlib import Path

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 11,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.08,
})

BASE = Path(__file__).resolve().parent / '数据'
FIG_DIR = Path(__file__).resolve().parent / 'figures'
FIG_DIR.mkdir(exist_ok=True)

task_arm = pd.read_csv(BASE / 'summary_task_arm.csv')
raw = pd.read_csv(BASE / 'reader_study_raw_data.csv')

CLOSED_TASKS = [1, 2, 3, 4]
OPEN_TASKS = [5, 6, 7, 8, 9, 10, 11]

TASK_FULL = {
    1: 'Admission\ndiagnosis',
    2: 'Preoperative\ndiagnosis',
    3: 'Intraoperative\ndiagnosis',
    4: 'Discharge\ndiagnosis',
    5: 'Perioperative\nassessment',
    6: 'Surgical\nplanning',
    7: 'Preoperative\norders',
    8: 'Postoperative\norders',
    9: 'Discharge\nsummary',
    10: 'Rehabilitation\nplanning',
    11: 'Multidisciplinary\nconsultation',
}

C1 = '#92B1D9'
C2 = '#C1D8E9'
C3 = '#DBDDEF'
C4 = '#F6C8B6'
C5 = '#D4D4D4'

BAR_COLORS = {'Resident': C2, 'Specialist': C3, 'Expert': C1, 'OrthoPilot': C4}
BAR_EDGE = {'Resident': '#8AAFCC', 'Specialist': '#B0B5D4', 'Expert': '#6E8CB8', 'OrthoPilot': '#D4957E'}

DOT_COLORS = {
    'Resident':   '#D4957E',
    'Specialist': '#92B1D9',
    'Expert':     '#6E7CBB',
}

TIER_BASE = {
    'Resident':   '#E8D8D0',
    'Specialist': '#D6DDE8',
    'Expert':     '#B8C8DD',
}
TIER_ACCENT = {
    'Resident':   '#D4957E',
    'Specialist': '#92B1D9',
    'Expert':     '#6E7CBB',
}

SAVE_FORMATS = ['pdf', 'png']


def save_fig(fig, stem):
    for fmt in SAVE_FORMATS:
        fig.savefig(FIG_DIR / f'{stem}.{fmt}', dpi=300)
    print(f'  Saved {stem}.pdf / .png')


def get_phy_task_mean(arm, tid):
    sub = raw[(raw['task_id'] == tid) & (raw['arm'] == arm)]
    return sub.groupby('physician_id')['score'].mean()


def get_orthopilot_mean(tid):
    sub = raw[(raw['task_id'] == tid) & (raw['arm'] == 'OrthoPilot')]
    return sub['score'].mean()


# ===========================================================================
# BAR CHARTS
# ===========================================================================

def make_bar_chart(task_ids, title, ylabel, stem):
    human_arms = ['Resident', 'Specialist', 'Expert']
    ai_arms = ['OrthoPilot']
    all_arms = human_arms + ai_arms

    means, ci_lows, ci_highs = {}, {}, {}
    for arm in all_arms:
        sub = task_arm[(task_arm['task_id'].isin(task_ids)) & (task_arm['arm'] == arm)]
        means[arm] = sub['mean'].mean()
        ci_lows[arm] = sub['ci_low'].mean()
        ci_highs[arm] = sub['ci_high'].mean()

    fig, ax = plt.subplots(figsize=(5.0, 4.5))
    n_human = len(human_arms)
    x_human = np.arange(n_human)
    x_ai = np.array([n_human + 0.7])
    x_all = np.concatenate([x_human, x_ai])
    labels = human_arms + ai_arms

    colors = [BAR_COLORS[a] for a in labels]
    edge_colors = [BAR_EDGE[a] for a in labels]
    vals = [means[a] for a in labels]
    errs_low = [means[a] - ci_lows[a] for a in labels]
    errs_high = [ci_highs[a] - means[a] for a in labels]

    ax.bar(x_all, vals, width=0.62, color=colors,
           edgecolor=edge_colors, linewidth=0.8, zorder=3)
    ax.errorbar(x_all, vals, yerr=[errs_low, errs_high],
                fmt='none', ecolor='#333333', elinewidth=1.0,
                capsize=4, capthick=0.8, zorder=4)
    for x, v, eh in zip(x_all, vals, errs_high):
        ax.text(x, v + eh + 0.012, f'{v:.3f}',
                ha='center', va='bottom', fontsize=10.5, fontweight='bold')

    sep_x = n_human - 0.5 + 0.35
    ax.axvline(sep_x, color='#AAAAAA', linestyle=':', linewidth=1.0, zorder=1)
    ylim_top = max(vals) + max(errs_high) + 0.07
    ax.set_ylim(0.35, ylim_top)
    y_section = ylim_top - 0.008
    ax.text((x_human[0] + x_human[-1]) / 2, y_section, 'Human',
            ha='center', va='top', fontsize=12, fontweight='normal', color='#555555')
    ax.text(x_ai[0], y_section, 'AI',
            ha='center', va='top', fontsize=12, fontweight='normal', color='#555555')

    ax.set_xticks(x_all)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    save_fig(fig, stem)
    plt.close(fig)


# ===========================================================================
# BOXPLOTS (closed-ended tasks)
# ===========================================================================

def make_boxplot_single(task_ids, task_type_label, arms, panel_title, stem):
    """Single-panel boxplot for one condition (alone or assisted)."""
    tier_from_arm = {
        'Expert': 'Expert', 'Specialist': 'Specialist', 'Resident': 'Resident',
        'AI+Expert': 'Expert', 'AI+Specialist': 'Specialist', 'AI+Resident': 'Resident',
    }

    def get_physician_scores(arms_list, tid):
        sub = raw[(raw['task_id'] == tid) & (raw['arm'].isin(arms_list))]
        phy_mean = sub.groupby(['physician_id', 'arm'])['score'].mean().reset_index()
        phy_mean['tier'] = phy_mean['arm'].map(tier_from_arm)
        return phy_mean

    n_tasks = len(task_ids)
    fig_w = max(5.5, n_tasks * 1.3 + 1.5)
    fig_h = 5.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    rng = np.random.default_rng(42)
    box_spacing = 1.05
    positions = np.arange(n_tasks) * box_spacing

    box_data_list, tier_data_list = [], []
    for tid in task_ids:
        phy = get_physician_scores(arms, tid)
        box_data_list.append(phy['score'].values)
        tier_data_list.append(phy['tier'].values)

    ax.boxplot(
        box_data_list, positions=positions, widths=0.60,
        patch_artist=True, showfliers=False,
        boxprops=dict(facecolor='white', edgecolor='#555555', linewidth=0.8),
        whiskerprops=dict(color='#555555', linewidth=0.8),
        capprops=dict(color='#555555', linewidth=0.8),
        medianprops=dict(color='#C0392B', linewidth=1.3),
    )
    for i, (scores, tiers) in enumerate(zip(box_data_list, tier_data_list)):
        jitter = rng.uniform(-0.14, 0.14, len(scores))
        for s, t, j in zip(scores, tiers, jitter):
            ax.scatter(positions[i] + j, s, color=DOT_COLORS[t], s=20,
                       alpha=0.70, edgecolors='none', zorder=5)

    ax.set_xticks(positions)
    ax.set_xticklabels([TASK_FULL[t] for t in task_ids], fontsize=10,
                       linespacing=1.2)
    ax.set_title(panel_title, fontsize=12, fontweight='bold', pad=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylabel(task_type_label, fontsize=12)

    all_vals = []
    for tid in task_ids:
        phy = get_physician_scores(arms, tid)
        all_vals.extend(phy['score'].values)
    y_min = min(all_vals) - 0.03
    y_max = max(all_vals) + 0.03
    y_top = y_max + (y_max - y_min) * 0.28
    ax.set_ylim(y_min, y_top)

    for i, tid in enumerate(task_ids):
        phy = get_physician_scores(arms, tid)
        scores = phy['score'].values
        m, sd = scores.mean(), scores.std(ddof=1)
        tier_idx = i % 3
        y_offsets = [0.02, 0.10, 0.18]
        y_annot = y_max + (y_max - y_min) * y_offsets[tier_idx]
        ax.annotate(
            f'Mean \u00b1 s.d.\n{m:.3f} \u00b1 {sd:.3f}',
            xy=(positions[i], max(scores) + 0.003),
            xytext=(positions[i], y_annot),
            ha='center', va='bottom', fontsize=9, color='#333333',
            linespacing=1.1,
            arrowprops=dict(arrowstyle='-', color='#BBBBBB', lw=0.4),
        )

    fig.tight_layout()
    save_fig(fig, stem)
    plt.close(fig)


# ===========================================================================
# SLOPE + BOX + HALF-VIOLIN CHART (open-ended tasks — Nature style)
# ===========================================================================

def make_slope_chart(task_ids, stem):
    """
    Nature-inspired paired slope chart.
    Layout per task column (left→right):
      1. Alone dots (jittered)  at x=0
      2. Paired lines connecting alone→assisted
      3. Assisted dots (jittered) at x=1
      4. Box + half-violin distribution summary at x=1.6~2.2

    Box+violin shows TWO distributions overlaid:
      - Alone distribution (warm/coral fill, left half-violin + left box)
      - Assisted distribution (blue fill, right half-violin + right box)

    OrthoPilot reference: dashed line with numeric value label.
    """
    tiers = ['Resident', 'Specialist', 'Expert']
    ai_map = {'Resident': 'AI+Resident', 'Specialist': 'AI+Specialist',
              'Expert': 'AI+Expert'}

    n_tasks = len(task_ids)
    col_width = 3.2
    fig_w = n_tasks * col_width + 0.8
    fig_h = 7.0

    fig, axes = plt.subplots(1, n_tasks, figsize=(fig_w, fig_h), sharey=True)
    if n_tasks == 1:
        axes = [axes]

    # Gather global y range
    all_vals = []
    for tid in task_ids:
        for tier in tiers:
            all_vals.extend(get_phy_task_mean(tier, tid).values)
            all_vals.extend(get_phy_task_mean(ai_map[tier], tid).values)
        all_vals.append(get_orthopilot_mean(tid))
    y_lo = min(all_vals) - 0.04
    y_hi = max(all_vals) + 0.07

    # x positions within each column
    X_ALONE = 0.0
    X_ASSIST = 1.1
    X_BOX = 2.0       # center of box+violin zone
    BOX_W = 0.15
    VIOLIN_MAX_W = 0.35

    for col, tid in enumerate(task_ids):
        ax = axes[col]
        rng = np.random.default_rng(42 + tid)

        # Collect all alone and assisted scores for distribution overlay
        all_alone_scores = []
        all_assist_scores = []

        # --- Draw paired lines + dots per tier ---
        for tier in tiers:
            alone_s = get_phy_task_mean(tier, tid)
            assist_s = get_phy_task_mean(ai_map[tier], tid)
            common = alone_s.index.intersection(assist_s.index)
            color = DOT_COLORS[tier]

            alone_vals = alone_s[common].values
            assist_vals = assist_s[common].values
            all_alone_scores.extend(alone_vals)
            all_assist_scores.extend(assist_vals)

            # Jitter for dots
            jitter_a = rng.uniform(-0.18, 0.18, len(common))
            jitter_b = rng.uniform(-0.18, 0.18, len(common))

            for a_val, b_val, ja, jb in zip(alone_vals, assist_vals,
                                             jitter_a, jitter_b):
                # Connecting line
                ax.plot([X_ALONE + ja, X_ASSIST + jb], [a_val, b_val],
                        color='#BBBBBB', linewidth=0.5, alpha=0.5, zorder=2)
                # Alone dot
                ax.scatter(X_ALONE + ja, a_val, color=color, s=18,
                           alpha=0.70, edgecolors='none', zorder=4)
                # Assisted dot
                ax.scatter(X_ASSIST + jb, b_val, color=color, s=18,
                           alpha=0.70, edgecolors='none', zorder=4)

        # --- Tier mean bold lines ---
        for tier in tiers:
            alone_mean = get_phy_task_mean(tier, tid).mean()
            assist_mean = get_phy_task_mean(ai_map[tier], tid).mean()
            color = DOT_COLORS[tier]
            ax.plot([X_ALONE, X_ASSIST], [alone_mean, assist_mean],
                    color=color, linewidth=2.8, alpha=0.90, zorder=6,
                    solid_capstyle='round')
            ax.scatter([X_ALONE], [alone_mean], color=color, s=55, zorder=7,
                       edgecolors='white', linewidth=0.8)
            ax.scatter([X_ASSIST], [assist_mean], color=color, s=55, zorder=7,
                       edgecolors='white', linewidth=0.8)

        # --- OrthoPilot reference line ---
        ai_val = get_orthopilot_mean(tid)
        ax.axhline(ai_val, color='#D4957E', linewidth=1.6, linestyle='--',
                    alpha=0.80, zorder=3, xmin=0, xmax=0.78)
        # Numeric label below the dashed line
        ax.text(X_ASSIST + 0.35, ai_val - 0.008, f'{ai_val:.3f}',
                fontsize=12.5, color='#1a1a1a', va='top', ha='left',
                fontweight='normal', zorder=8)

        # --- Box + half-violin on the right ---
        alone_arr = np.array(all_alone_scores)
        assist_arr = np.array(all_assist_scores)

        # Half-violin: alone (left half) and assisted (right half)
        for scores, side, fill_c, fill_alpha in [
            (alone_arr, 'left', '#F6C8B6', 0.50),
            (assist_arr, 'right', '#92B1D9', 0.50),
        ]:
            try:
                kde = gaussian_kde(scores, bw_method=0.35)
                y_grid = np.linspace(scores.min() - 0.01,
                                     scores.max() + 0.01, 150)
                density = kde(y_grid)
                density_norm = density / density.max() * VIOLIN_MAX_W

                if side == 'left':
                    x_edge = X_BOX - density_norm
                    x_center = np.full_like(y_grid, X_BOX)
                else:
                    x_edge = X_BOX + density_norm
                    x_center = np.full_like(y_grid, X_BOX)

                ax.fill_betweenx(y_grid, x_center, x_edge,
                                 color=fill_c, alpha=fill_alpha,
                                 edgecolor='none', zorder=1)
                ax.plot(x_edge, y_grid, color=fill_c, linewidth=0.8,
                        alpha=0.7, zorder=2)
            except Exception:
                pass

        # Mini boxplots inside the violin
        for scores, bx_offset, bx_color in [
            (alone_arr, -0.07, '#D4957E'),
            (assist_arr, +0.07, '#6E8CB8'),
        ]:
            q1, med, q3 = np.percentile(scores, [25, 50, 75])
            iqr = q3 - q1
            wlo = max(scores.min(), q1 - 1.5 * iqr)
            whi = min(scores.max(), q3 + 1.5 * iqr)
            bx = X_BOX + bx_offset
            # Whisker
            ax.plot([bx, bx], [wlo, whi], color=bx_color, linewidth=1.0,
                    zorder=5)
            # Box
            ax.add_patch(plt.Rectangle((bx - BOX_W/2, q1), BOX_W, iqr,
                                        facecolor='white', edgecolor=bx_color,
                                        linewidth=1.0, zorder=6))
            # Median
            ax.plot([bx - BOX_W/2, bx + BOX_W/2], [med, med],
                    color=bx_color, linewidth=1.8, zorder=7)

        alone_mean_all = alone_arr.mean()
        assist_mean_all = assist_arr.mean()
        ax.plot([X_ALONE, X_ASSIST], [alone_mean_all, assist_mean_all],
                color='#222222', linewidth=2.4, alpha=0.85, zorder=9,
                solid_capstyle='round')
        ax.scatter([X_ALONE, X_ASSIST], [alone_mean_all, assist_mean_all],
                   marker='D', s=62, color='#222222', edgecolors='white',
                   linewidth=0.8, zorder=10)
        ax.text(X_ALONE - 0.23, alone_mean_all + 0.012, f'{alone_mean_all:.3f}',
                fontsize=11.5, color='#222222', va='bottom', ha='right',
                fontweight='normal', zorder=11)
        ax.text(X_ASSIST + 0.20, assist_mean_all - 0.018, f'{assist_mean_all:.3f}',
                fontsize=11.5, color='#222222', va='top', ha='left',
                fontweight='normal', zorder=11)

        # --- Axis formatting ---
        ax.set_xlim(-0.4, X_BOX + VIOLIN_MAX_W + 0.15)
        ax.set_ylim(y_lo, 1.05)
        ax.set_xticks([X_ALONE, X_ASSIST])
        ax.set_xticklabels(['Alone', 'AI-assisted'], fontsize=11)
        # Task name inside plot area, just below y=1.0
        x_mid = (X_ALONE + X_BOX + VIOLIN_MAX_W) / 2
        ax.text(x_mid, 0.995, TASK_FULL[tid], ha='center', va='top',
                fontsize=16, fontweight='normal', linespacing=1.3,
                color='#333333')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if col > 0:
            ax.spines['left'].set_visible(False)
            ax.tick_params(left=False)

    axes[0].set_ylabel('ORACLE Score', fontsize=13)

    # No in-figure legend — separate legend file
    fig.tight_layout()
    save_fig(fig, stem)
    plt.close(fig)


# ===========================================================================
# SEPARATE LEGEND
# ===========================================================================

def make_legend():
    """Standalone legend for both boxplot and slope chart figures."""
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    ax.set_axis_off()
    legend_handles = [
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=DOT_COLORS['Resident'], markeredgecolor='white',
               markersize=10, label='Resident (1\u20139 years)'),
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=DOT_COLORS['Specialist'], markeredgecolor='white',
               markersize=10, label='Specialist (10\u201324 years)'),
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=DOT_COLORS['Expert'], markeredgecolor='white',
               markersize=10, label='Expert (\u226525 years)'),
        Line2D([0], [0], color='#D4957E', linewidth=1.8, linestyle='--',
               label='OrthoPilot'),
        Patch(facecolor='#F6C8B6', alpha=0.55, edgecolor='none',
              label='Alone distribution'),
        Patch(facecolor='#92B1D9', alpha=0.55, edgecolor='none',
              label='+AI distribution'),
    ]
    ax.legend(handles=legend_handles, loc='center', ncol=2, fontsize=12,
              frameon=False, handletextpad=0.5, labelspacing=1.0,
              columnspacing=2.0)
    fig.tight_layout()
    save_fig(fig, 'fig_slope_legend')
    plt.close(fig)


# ===========================================================================
# Generate all figures
# ===========================================================================
print('=== Generating Reader Study Figures ===')

make_bar_chart(CLOSED_TASKS,
               'Closed-ended Diagnosis', 'Mean Accuracy',
               'fig_bar_diagnostic')
make_bar_chart(OPEN_TASKS,
               'Open-ended Management', 'Mean ORACLE Score',
               'fig_bar_open')
make_boxplot_single(CLOSED_TASKS, 'Accuracy',
                    ['Expert', 'Specialist', 'Resident'],
                    'Physician alone', 'fig_box_alone')
make_boxplot_single(CLOSED_TASKS, 'Accuracy',
                    ['AI+Expert', 'AI+Specialist', 'AI+Resident'],
                    'Physician assisted by OrthoPilot', 'fig_box_assisted')
make_slope_chart(OPEN_TASKS, 'fig_slope_open')
make_legend()

print('\n=== All figures saved to', FIG_DIR, '===')
