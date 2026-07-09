#!/usr/bin/env python3
"""
Radial Dot Plot V3 — Disease-Level Performance Comparison
Nature-style. Each spoke = one disease. 5 dots along the radial axis
show model scores. Range bar connects min-max. Patient count encoded
in label font weight. CHEESE highlighted prominently.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Wedge, FancyBboxPatch
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path("/path/to")
SCORES_CSV = ROOT / "Bone/project/多中心验证/disease_analysis/output_complete/disease_overall_scores.csv"
IDS_CSV    = ROOT / "Bone/gen_validation/test_final/test_ids.csv"
OUT_DIR    = ROOT / "Bone/project/多中心验证/disease_analysis/figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── English Names ────────────────────────────────────────────────────────
EN_NAMES = {
    "Z47.001":       "Implant Removal",
    "S72.000":       "Femoral Neck Fx",
    "S46.002":       "Rotator Cuff Injury",
    "M51.202":       "Lumbar Disc Herniation",
    "S72.101":       "Intertrochanteric Fx",
    "Z47.000X002":   "Hardware Removal",
    "S52.500X001":   "Distal Radius Fx",
    "M17.900X002":   "Knee OA",
    "S42.000":       "Clavicle Fx",
    "M17.101":       "Gonarthrosis",
    "M48.005":       "Lumbar Stenosis",
    "M23.308":       "Meniscus Injury",
    "M50.201":       "Cervical Disc Herniation",
    "M20.100X002":   "Hallux Valgus",
    "S82.800X082":   "Ankle Fx",
    "S82.000":       "Patellar Fx",
    "M43.006":       "Lumbar Spondylolisthesis",
    "S42.200X001":   "Proximal Humerus Fx",
    "C40.201":       "Femoral Neoplasm",
    "M25.300X002":   "Ankle Instability",
    "S32.000X011":   "L1 Vertebral Fx",
    "S92.000":       "Calcaneal Fx",
    "S22.000X003":   "Thoracic Compression Fx",
    "S82.100X087":   "Tibial Plateau Fx",
    "M17.900":       "Knee Degeneration",
    "M87.002":       "Femoral Head Necrosis",
    "S42.301":       "Humeral Shaft Fx",
    "S32.000X002":   "Lumbar Compression Fx",
    "S86.001":       "Achilles Rupture",
    "M79.906":       "Thigh Soft Tissue",
}

# ── Load data ────────────────────────────────────────────────────────────
scores = pd.read_csv(SCORES_CSV)
ids    = pd.read_csv(IDS_CSV)

disease_counts = ids["assigned_code"].value_counts()
TOP_N = 20
top_codes  = disease_counts.head(TOP_N).index.tolist()
top_counts = disease_counts.head(TOP_N).values

df = scores[scores["disease_code"].isin(top_codes)].copy()

# ── Model config ─────────────────────────────────────────────────────────
MODEL_ORDER = ["CHEESE", "OrthoPilot", "GPT-5.1", "DeepSeek-R1", "MedGemma-27B"]
COLORS = {
    "CHEESE":      "#C62828",
    "OrthoPilot":  "#1565C0",
    "GPT-5.1":     "#2E7D32",
    "DeepSeek-R1": "#E65100",
    "MedGemma-27B":"#6A1B9A",
}
MARKERS = {
    "CHEESE":      "D",
    "OrthoPilot":  "s",
    "GPT-5.1":     "^",
    "DeepSeek-R1": "o",
    "MedGemma-27B":"v",
}

# ── Layout ───────────────────────────────────────────────────────────────
sector_width = 2 * np.pi / TOP_N
center_angles = np.array([np.pi/2 - i * sector_width for i in range(TOP_N)])

SCORE_MIN, SCORE_MAX = 0.35, 1.0
R_INNER, R_OUTER = 0.30, 0.88

def s2r(s):
    return R_INNER + (R_OUTER - R_INNER) * (np.clip(s, SCORE_MIN, SCORE_MAX) - SCORE_MIN) / (SCORE_MAX - SCORE_MIN)

# ── Figure ───────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 18))
ax = fig.add_subplot(111, projection="polar")
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# ── Reference arcs with score labels ─────────────────────────────────────
ref_scores = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
for ref in ref_scores:
    r = s2r(ref)
    theta_ring = np.linspace(0, 2*np.pi, 500)
    lw = 0.8 if ref in [0.5, 0.7, 0.9] else 0.4
    ax.plot(theta_ring, [r]*500, color="#E0E0E0", linewidth=lw, zorder=0)

# Score labels on right side
for ref in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
    r = s2r(ref)
    ax.text(np.deg2rad(355), r, f"{ref:.1f}", fontsize=6, color="#AAAAAA",
            ha="center", va="bottom", zorder=6)

# ── Alternating sector fill ──────────────────────────────────────────────
for i in range(TOP_N):
    if i % 2 == 0:
        t1 = center_angles[i] - sector_width * 0.48
        t2 = center_angles[i] + sector_width * 0.48
        thetas = np.linspace(t1, t2, 60)
        ax.fill_between(thetas, R_INNER - 0.02, R_OUTER + 0.015,
                        color="#FAFAFA", zorder=0)

# ── Draw each disease ───────────────────────────────────────────────────
for i, code in enumerate(top_codes):
    ang = center_angles[i]
    count = top_counts[i]
    disease_df = df[df["disease_code"] == code]

    # Collect scores
    model_scores = {}
    for model in MODEL_ORDER:
        row = disease_df[disease_df["model_display"] == model]
        if not row.empty:
            model_scores[model] = row["overall_score"].values[0]

    if not model_scores:
        continue

    # Range bar (min to max)
    s_vals = list(model_scores.values())
    r_min, r_max = s2r(min(s_vals)), s2r(max(s_vals))
    ax.plot([ang, ang], [r_min, r_max], color="#CCCCCC", linewidth=2.5,
            zorder=2, solid_capstyle="round")

    # Central guide line (thin, from inner to outer)
    ax.plot([ang, ang], [R_INNER, R_OUTER], color="#EEEEEE", linewidth=0.3, zorder=1)

    # Dots — draw non-CHEESE first, CHEESE on top
    for model in MODEL_ORDER:
        if model not in model_scores or model == "CHEESE":
            continue
        s = model_scores[model]
        r = s2r(s)
        ax.scatter(ang, r, c=COLORS[model], marker=MARKERS[model],
                   s=55, edgecolors="white", linewidths=0.6, zorder=8, alpha=0.9)

    # CHEESE dot (large, prominent, on top)
    if "CHEESE" in model_scores:
        r_cheese = s2r(model_scores["CHEESE"])
        ax.scatter(ang, r_cheese, c=COLORS["CHEESE"], marker=MARKERS["CHEESE"],
                   s=120, edgecolors="white", linewidths=1.2, zorder=12, alpha=1.0)

    # ── Label ────────────────────────────────────────────────────────────
    en_name = EN_NAMES.get(code, code)
    label = f"{en_name}  (n={count})"
    label_r = R_OUTER + 0.055

    angle_deg = np.degrees(ang) % 360
    if 90 < angle_deg < 270:
        ha, rotation = "right", angle_deg + 180
    else:
        ha, rotation = "left", angle_deg

    ax.text(ang, label_r, label,
            fontsize=8.5, fontfamily="sans-serif",
            fontweight="bold" if count >= 100 else "medium",
            ha=ha, va="center", rotation=rotation, rotation_mode="anchor",
            color="#2a2a2a", zorder=15)

# ── Patient-count arc indicator (outer ring) ─────────────────────────────
# Thin colored arc outside each label: width ~ log(count), color = count
max_count = max(top_counts)
cmap_counts = plt.cm.YlOrRd
norm_counts = mcolors.Normalize(vmin=30, vmax=max_count)

for i, code in enumerate(top_codes):
    ang = center_angles[i]
    count = top_counts[i]
    arc_r = R_OUTER + 0.035
    half_w = sector_width * 0.38
    t1, t2 = ang - half_w, ang + half_w
    thetas_arc = np.linspace(t1, t2, 40)
    c = cmap_counts(norm_counts(count))
    ax.plot(thetas_arc, [arc_r]*40, color=c, linewidth=3.5,
            solid_capstyle="round", zorder=3, alpha=0.7)

# ── Center annotation ───────────────────────────────────────────────────
circle_bg = plt.Circle((0, 0), R_INNER - 0.05, transform=ax.transData,
                        color="white", zorder=18)
ax.add_patch(circle_bg)
ax.text(0, 0.02, f"Top {TOP_N}", ha="center", va="center",
        fontsize=14, fontweight="bold", color="#333333", zorder=20)
ax.text(0, -0.06, "Diseases\nby Volume", ha="center", va="center",
        fontsize=10, color="#666666", zorder=20)

# ── Cleanup ──────────────────────────────────────────────────────────────
ax.set_ylim(0, R_OUTER + 0.35)
ax.set_xticks([])
ax.set_yticks([])
ax.spines["polar"].set_visible(False)
ax.grid(False)

# ── Legend ────────────────────────────────────────────────────────────────
legend_elements = []
for model in MODEL_ORDER:
    lbl = f"CHEESE (Ours)" if model == "CHEESE" else model
    ms = 11 if model == "CHEESE" else 8
    legend_elements.append(
        Line2D([0], [0], marker=MARKERS[model], color="w",
               markerfacecolor=COLORS[model], markeredgecolor="white",
               markersize=ms, markeredgewidth=0.8, label=lbl, linewidth=0)
    )
# Range bar legend
legend_elements.append(
    Line2D([0], [0], color="#CCCCCC", linewidth=2.5, label="Score range", linestyle="-")
)

leg = ax.legend(handles=legend_elements, loc="lower right",
                bbox_to_anchor=(1.18, -0.03),
                frameon=True, framealpha=0.95, edgecolor="#D0D0D0",
                fontsize=9.5, title="Model", title_fontsize=10.5,
                handletextpad=0.8, borderpad=1.0, labelspacing=0.9)
leg.get_frame().set_linewidth(0.5)

# ── Title ────────────────────────────────────────────────────────────────
fig.suptitle("Disease-Level Performance Across Models",
             fontsize=18, fontweight="bold", color="#1a1a1a", y=0.965)
fig.text(0.5, 0.94,
         f"Overall scores for top {TOP_N} diseases by patient volume  |  "
         f"5,905 patients  |  1,000 disease categories",
         ha="center", fontsize=10, color="#666666")

# ── Save ─────────────────────────────────────────────────────────────────
for fmt in ["pdf", "png"]:
    out = OUT_DIR / f"radial_disease_performance.{fmt}"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out}")

plt.close()
print("Done!")
