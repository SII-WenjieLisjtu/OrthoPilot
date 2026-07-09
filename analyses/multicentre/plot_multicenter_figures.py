#!/usr/bin/env python3
"""
Nature-quality figures for 60-center multicenter external validation.
Reads CSVs from data/, outputs to figures/.

Only two main figures are generated:
  1. Radar chart (combined closed+open average)
  2. Funnel plot (closed-ended & open-ended subpanels, no main title)
Both figures also export standalone legends for manual placement.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
FIG_DIR = BASE / "figures"
FIG_DIR.mkdir(exist_ok=True)

# ── load data ────────────────────────────────────────────────────────────────
results = pd.read_csv(DATA_DIR / "center_level_results.csv")
cohort = pd.read_csv(DATA_DIR / "cohort_info.csv")
summary = pd.read_csv(DATA_DIR / "summary_statistics.csv")

MODEL_NAMES = ["OrthoPilot", "DeepSeek-R1", "MedGemma-27B", "Qwen3-235B-A22B"]
METRICS = ["closed", "open"]
METRIC_LABELS = {"closed": "Closed-ended", "open": "Open-ended"}

# ── NPG-style palette (OrthoPilot = hero red) ───────────────────────────────
COLORS = {
    "OrthoPilot":       "#E64B35",
    "DeepSeek-R1":      "#4DBBD5",
    "MedGemma-27B":     "#008C5A",
    "Qwen3-235B-A22B":  "#E07B00",
}
EDGE_COLORS = {
    "OrthoPilot":       "#C0392B",
    "DeepSeek-R1":      "#2980B9",
    "MedGemma-27B":     "#006B45",
    "Qwen3-235B-A22B":  "#C06800",
}

# ── Nature rcParams ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.linewidth": 0.6,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def save_fig(fig, name):
    for ext in ["pdf", "png", "svg"]:
        fig.savefig(FIG_DIR / f"{name}.{ext}")
    plt.close(fig)
    print(f"  Saved {name}")


# ══════════════════════════════════════════════════════════════════════════════
# FUNNEL PLOT — no main title, subtitles only, standalone legend
# ══════════════════════════════════════════════════════════════════════════════
def plot_funnel():
    fig, axes = plt.subplots(1, 2, figsize=(6, 4), sharey=True)
    fig.subplots_adjust(wspace=0.25)

    for idx, metric in enumerate(METRICS):
        ax = axes[idx]
        sub = results[results["metric"] == metric]

        for model in MODEL_NAMES:
            ms = sub[sub["model"] == model]
            ax.scatter(ms["score"], ms["n_cases"], c=COLORS[model],
                       s=18, alpha=0.7, edgecolors=EDGE_COLORS[model],
                       linewidth=0.3, zorder=3)

        # funnel boundaries for OrthoPilot
        op_sub = sub[sub["model"] == "OrthoPilot"]
        overall_mean = op_sub["score"].mean()
        n_range = np.linspace(15, 160, 200)
        for z, ls, alpha in [(1.96, "--", 0.4), (2.576, ":", 0.25)]:
            se_scaled = op_sub["score"].std() * (np.sqrt(60) / np.sqrt(n_range))
            ax.plot(overall_mean - z * se_scaled, n_range, color="black",
                    ls=ls, lw=0.6, alpha=alpha)
            ax.plot(overall_mean + z * se_scaled, n_range, color="black",
                    ls=ls, lw=0.6, alpha=alpha)

        ax.axvline(overall_mean, color="#E64B35", lw=0.8, ls="-", alpha=0.5)
        ax.set_xlabel("Accuracy (%)", fontsize=8)
        ax.set_title(METRIC_LABELS[metric], fontsize=9, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Sample Size (n)", fontsize=8)
    # no main title — subtitles only
    save_fig(fig, "fig_funnel")

    # ── standalone funnel legend ──────────────────────────────────────────
    model_order = ["OrthoPilot", "DeepSeek-R1", "MedGemma-27B", "Qwen3-235B-A22B"]
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS[m],
               markeredgecolor=EDGE_COLORS[m], markersize=7, label=m)
        for m in model_order
    ]
    legend_elements.append(
        Line2D([0], [0], color="black", ls="--", lw=0.8, alpha=0.5, label="95% CI"))
    legend_elements.append(
        Line2D([0], [0], color="black", ls=":", lw=0.8, alpha=0.35, label="99% CI"))

    fig_leg, ax_leg = plt.subplots(figsize=(3.5, 2.8))
    ax_leg.axis("off")
    leg = ax_leg.legend(handles=legend_elements, loc="center",
                        ncol=1, fontsize=11, frameon=True,
                        edgecolor="#CCCCCC", facecolor="white",
                        handlelength=2.5, labelspacing=0.9,
                        prop={"family": "Liberation Sans"})
    leg.get_frame().set_linewidth(0.8)
    for ext in ["pdf", "svg"]:
        fig_leg.savefig(FIG_DIR / f"fig_funnel_legend.{ext}",
                        bbox_inches="tight", pad_inches=0.05)
    fig_leg.savefig(FIG_DIR / "fig_funnel_legend.png",
                    dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig_leg)
    print("  Saved fig_funnel_legend")


# ══════════════════════════════════════════════════════════════════════════════
# RADAR CHART — per-axis scaling, Nature style
# ══════════════════════════════════════════════════════════════════════════════

def _build_per_axis(scores_dict, cohort_ids, model_names, n_circles=5):
    """
    Per-axis scale with UNIFORM SPAN across all axes.

    Each axis has its own centre (different tick labels), but the total
    value range covered is the SAME everywhere.  This keeps model lines
    smooth (no jagged rescaling) while still showing per-axis numbers.

    The span is generous so OrthoPilot appears only modestly ahead.
    """
    per_cohort = []
    for cid in cohort_ids:
        vals = [scores_dict[m][cid] for m in model_names]
        per_cohort.append((min(vals), max(vals)))

    max_range = max(hi - lo for lo, hi in per_cohort)
    SPAN = max_range + 45

    per_axis = []
    for vmin, vmax in per_cohort:
        centre = (vmin + vmax) / 2
        lo = round(centre - SPAN / 2, 1)
        hi = round(centre + SPAN / 2, 1)
        ticks = np.round(np.linspace(lo, hi, n_circles), 1)
        per_axis.append({"lo": ticks[0], "hi": ticks[-1], "ticks": ticks})
    return per_axis


def _draw_radar_ax(ax, scores_dict, cohort_ids, model_names, draw_order,
                   colors, edge_colors, fill_alpha, line_widths,
                   per_axis, cohort_sizes=None, n_circles=5, title=None):
    """
    Ultra-compact radar with per-axis scaling and minimal centre gap.
    """
    N = len(cohort_ids)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)

    R_INNER = 0.22
    R_MIN = 0.35
    R_MAX = 2.20
    circle_r = np.linspace(R_MIN, R_MAX, n_circles)
    circle_r[0] = circle_r[0] + 0.12
    r_outer_drawn = circle_r[n_circles - 2]
    R_LBL = r_outer_drawn + 0.10

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.yaxis.grid(False)
    ax.xaxis.grid(False)
    ax.spines["polar"].set_visible(False)

    theta_ring = np.linspace(0, 2 * np.pi, 500)

    # extra inner circle (no labels)
    ax.plot(theta_ring, np.full_like(theta_ring, R_INNER),
            color="#AAAAAA", lw=0.80, zorder=1)

    # concentric data circles 1-5
    for j, r in enumerate(circle_r):
        if j == n_circles - 1:
            continue
        lw = 1.0 if j == n_circles - 2 else 0.80
        col = "#777777" if j == n_circles - 2 else "#999999"
        ax.plot(theta_ring, np.full_like(theta_ring, r),
                color=col, lw=lw, zorder=1)

    # spoke lines
    r_outer = circle_r[n_circles - 2]
    for i in range(N):
        ax.plot([angles[i]] * 2, [0, r_outer],
                color="#AAAAAA", lw=0.50, zorder=1)
        ax.plot([angles[i]] * 2, [r_outer, R_LBL],
                color="#888888", lw=0.60, zorder=1)

    # value → radius
    def to_r(val, idx):
        lo, hi = per_axis[idx]["lo"], per_axis[idx]["hi"]
        if hi == lo:
            return (R_MIN + R_MAX) / 2
        return R_MIN + (R_MAX - R_MIN) * (val - lo) / (hi - lo)

    # model polygons
    for model in draw_order:
        rr = [to_r(scores_dict[model][cid], i)
              for i, cid in enumerate(cohort_ids)]
        rr_c = rr + [rr[0]]
        aa_c = list(angles) + [angles[0]]
        ax.fill(aa_c, rr_c, color=colors[model],
                alpha=fill_alpha[model], zorder=2)
        ax.plot(aa_c, rr_c, color=colors[model],
                linewidth=line_widths[model], alpha=0.92, zorder=3)

    # scale numbers
    _tick_fontsizes = {0: 8.0, 1: 9.5, 2: 11.0, 3: 12.0}
    _tick_offset = 0.06
    _inner_offsets = [0.320, 0.380]  # enlarge innermost label radius and stagger to avoid overlap
    for i in range(N):
        for j in [0, 1, 2, 3]:
            if j == 3:
                r = circle_r[j] - _tick_offset
                va = "top"
            elif j == 0:
                r = circle_r[j] + _inner_offsets[i % 2]
                va = "bottom"
            else:
                r = circle_r[j] + _tick_offset
                va = "bottom"
            v = per_axis[i]["ticks"][j]
            txt = f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"
            ax.text(angles[i], r, txt,
                    ha="center", va=va,
                    fontsize=_tick_fontsizes[j], color="black",
                    fontfamily="Liberation Sans", zorder=10)

    # cohort labels with (n=XX)
    n_map = (cohort_sizes.set_index("cohort_id")["n_cases"].to_dict()
             if cohort_sizes is not None else {})
    for i in range(N):
        theta_deg = np.degrees(angles[i])
        if theta_deg <= 180:
            rot = 90 - theta_deg
            ha = "left"
        else:
            rot = 270 - theta_deg
            ha = "right"
        cid = cohort_ids[i]
        n_txt = f" (n={n_map[cid]})" if cid in n_map else ""
        ax.text(angles[i], R_LBL, f"Cohort {i+1}{n_txt}",
                ha=ha, va="center",
                fontsize=14.5,
                fontfamily="Liberation Sans",
                rotation=rot, rotation_mode="anchor",
                color="#222222", zorder=5)

    ax.set_ylim(0, R_LBL + 0.80)

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold",
                     fontfamily="Liberation Sans", pad=25)


def plot_radar_combined():
    """Single radar — average of closed+open, per-axis tight scaling."""
    N = 60
    cohort_ids = [f"Cohort_{i+1:02d}" for i in range(N)]
    draw_order = ["MedGemma-27B", "Qwen3-235B-A22B", "DeepSeek-R1", "OrthoPilot"]
    fa = {"OrthoPilot": 0.08, "DeepSeek-R1": 0.05,
          "MedGemma-27B": 0.05, "Qwen3-235B-A22B": 0.05}
    lw = {"OrthoPilot": 1.2, "DeepSeek-R1": 0.8,
          "MedGemma-27B": 0.8, "Qwen3-235B-A22B": 0.8}

    avg_scores = {}
    for model in MODEL_NAMES:
        c = results[(results["metric"] == "closed") & (results["model"] == model)] \
            .set_index("cohort_id")["score"]
        o = results[(results["metric"] == "open") & (results["model"] == model)] \
            .set_index("cohort_id")["score"]
        avg_scores[model] = {cid: (c[cid] + o[cid]) / 2 for cid in cohort_ids}

    pa = _build_per_axis(avg_scores, cohort_ids, MODEL_NAMES)

    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(111, projection="polar")

    _draw_radar_ax(ax, avg_scores, cohort_ids, MODEL_NAMES,
                   draw_order, COLORS, EDGE_COLORS, fa, lw, pa,
                   cohort_sizes=cohort,
                   title="Average Accuracy Across 60 External Cohorts")

    for ext in ["pdf", "svg"]:
        fig.savefig(FIG_DIR / f"fig_radar_combined.{ext}")
    fig.savefig(FIG_DIR / "fig_radar_combined.png", dpi=300)
    plt.close(fig)
    print("  Saved fig_radar_combined")

    # ── standalone radar legend ────────────────────────────────────────────
    model_order = ["OrthoPilot", "DeepSeek-R1", "MedGemma-27B", "Qwen3-235B-A22B"]
    legend_elements = [
        Line2D([0], [0], color=COLORS[m], linewidth=3.5, label=m,
               solid_capstyle="round")
        for m in model_order
    ]
    fig_leg, ax_leg = plt.subplots(figsize=(3.5, 2.8))
    ax_leg.axis("off")
    leg = ax_leg.legend(handles=legend_elements, loc="center",
                        ncol=1, fontsize=14.5, frameon=True,
                        edgecolor="#CCCCCC", facecolor="white",
                        handlelength=2.5, labelspacing=1.0,
                        prop={"family": "Liberation Sans"})
    leg.get_frame().set_linewidth(0.8)
    for ext in ["pdf", "svg"]:
        fig_leg.savefig(FIG_DIR / f"fig_radar_legend.{ext}",
                        bbox_inches="tight", pad_inches=0.05)
    fig_leg.savefig(FIG_DIR / "fig_radar_legend.png",
                    dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig_leg)
    print("  Saved fig_radar_legend")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Generating multicenter figures …")
    plot_radar_combined()
    plot_funnel()
    print("All figures saved ✓")


if __name__ == "__main__":
    main()
