#!/usr/bin/env python3
"""
Main Figure for OrthoBench — Nature-quality compact circular dendrogram.
Visually striking overview with chapter arcs, ID/OOD + Rare/Non-rare bands,
key statistics, and integrated legend. No individual disease name labels.

Designed as a standalone single-panel figure.
Width: 183 mm (Nature double-column).
"""

import os
import sys
import csv
import math
import numpy as np
from collections import defaultdict, OrderedDict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import to_rgba
import matplotlib.patheffects as pe

# ── Paths ─────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT_STATS = os.path.join(BASE, "gen_validation", "test_final", "split_stats_by_code.csv")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────
CHAPTER_COLORS = {
    'M': '#E8918C', 'S': '#7DBAD5', 'D': '#6DBFA0', 'C': '#F2C572',
    'T': '#7A9ABF', 'Q': '#A8B0CB', 'R': '#A3D5C9', 'G': '#C4B49E',
    'L': '#A8897A', 'A': '#E07070', 'Z': '#7B89B8', 'E': '#E88FB8',
    'I': '#9473A8', 'J': '#5DAF7E', 'K': '#5DA8A6', 'F': '#C89BA3',
}
CHAPTER_NAMES = {
    'M': 'Musculoskeletal', 'S': 'Injuries', 'D': 'Neoplasms',
    'C': 'Malignant neoplasms', 'T': 'Trauma & complications',
    'Q': 'Congenital', 'R': 'Symptoms', 'G': 'Nervous system',
    'L': 'Skin', 'A': 'Infectious', 'Z': 'Health services',
    'E': 'Endocrine', 'I': 'Circulatory', 'J': 'Respiratory',
    'K': 'Digestive', 'F': 'Mental',
}
ID_COLOR   = '#7DBAD5'
OOD_COLOR  = '#E8918C'
RARE_COLOR = '#B088C4'
NONRARE_COLOR = '#D0D4D8'


def load_benchmark_data():
    codes = []
    with open(SPLIT_STATS, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain_by_class'].strip()
            if domain not in ('ID', 'OOD'):
                continue
            code = row['code'].strip()
            codes.append({
                'code': code, 'chapter': code[0].upper(),
                'category': code[:3], 'domain': domain,
                'is_rare': row['is_rare'].strip() == 'True',
                'patients': float(row['test_patient_count']),
            })
    return codes


def build_hierarchy(codes):
    tree = OrderedDict()
    chapter_counts = defaultdict(int)
    for c in codes:
        chapter_counts[c['chapter']] += 1
    for ch in sorted(chapter_counts, key=lambda k: -chapter_counts[k]):
        ch_codes = [c for c in codes if c['chapter'] == ch]
        cat_counts = defaultdict(int)
        for c in ch_codes:
            cat_counts[c['category']] += 1
        tree[ch] = OrderedDict()
        for cat in sorted(cat_counts, key=lambda k: -cat_counts[k]):
            tree[ch][cat] = sorted(
                [c for c in ch_codes if c['category'] == cat],
                key=lambda c: -c['patients'])
    return tree


def draw_main_figure(tree):
    total_leaves = sum(len(v) for d in tree.values() for v in d.values())

    # ── Figure ──
    fig_w = 183 / 25.4
    fig_h = 190 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h))

    # Circular tree takes main area; leave right margin for legend
    ax = fig.add_axes([0.02, 0.05, 0.72, 0.93], projection='polar')

    # ── Angular layout ──
    # Start at top (90°) so the largest chapter (M) is at top-right
    start_angle = 90.0
    gap_ch = 5.0
    gap_cat = 0.3
    n_ch = len(tree)
    n_cat = sum(len(d) for d in tree.values())
    avail = 360.0 - gap_ch * n_ch - gap_cat * (n_cat - n_ch)

    leaf_pos = []
    ch_ranges = {}
    cur = start_angle
    for ch, ch_data in tree.items():
        ch_n = sum(len(v) for v in ch_data.values())
        ch_start = cur
        cat_off = 0.0
        for i_cat, (cat, cat_codes) in enumerate(ch_data.items()):
            cn = len(cat_codes)
            cs = (cn / total_leaves) * avail
            cat_s = ch_start + cat_off
            for j, ci in enumerate(cat_codes):
                a = cat_s + (j + 0.5) * (cs / cn)
                leaf_pos.append((math.radians(a), ci))
            cat_off += cs
            if i_cat < len(ch_data) - 1:
                cat_off += gap_cat
        ch_end = ch_start + cat_off
        ch_ranges[ch] = (math.radians(ch_start), math.radians(ch_end))
        cur = ch_end + gap_ch

    # ── Radial layers (compact, no label ring) ──
    r_ch_in  = 0.30
    r_ch_out = 0.42
    r_cat    = 0.45
    r_br     = 0.46
    r_leaf   = 0.68
    r_id_in  = 0.71
    r_id_out = 0.80
    r_rr_in  = 0.82
    r_rr_out = 0.91

    # ── Chapter arc bands ──
    for ch, (sa, ea) in ch_ranges.items():
        c = CHAPTER_COLORS.get(ch, '#999')
        n = max(60, int((ea - sa) * 120))
        th = np.linspace(sa, ea, n)

        # Faint background fill
        ax.fill_between(th, r_ch_in, r_leaf + 0.005,
                        color=to_rgba(c, 0.05), edgecolor='none')
        # Solid arc
        ax.fill_between(th, r_ch_in, r_ch_out,
                        color=to_rgba(c, 0.70), edgecolor='none')
        ax.plot(th, [r_ch_out]*n, color=c, lw=0.8)
        ax.plot(th, [r_ch_in]*n, color=c, lw=0.4)
        # Radial edges
        ax.plot([sa, sa], [r_ch_in, r_ch_out], color=c, lw=0.5, alpha=0.7)
        ax.plot([ea, ea], [r_ch_in, r_ch_out], color=c, lw=0.5, alpha=0.7)

        # Chapter label — only on arcs large enough to avoid overlap
        mid = (sa + ea) / 2
        span = math.degrees(ea - sa)
        lr = (r_ch_in + r_ch_out) / 2
        ad = math.degrees(mid)
        ch_name = CHAPTER_NAMES.get(ch, ch)
        ch_n = sum(len(v) for v in tree[ch].values())
        rot = ad + 180 if 90 < ad < 270 else ad
        if span > 18:
            ax.text(mid, lr, f'{ch_name}\n({ch_n})',
                    fontsize=6.5, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rot,
                    rotation_mode='anchor', linespacing=1.1,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground=c)])
        elif span > 8:
            ax.text(mid, lr, f'{ch} ({ch_n})',
                    fontsize=5.5, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rot,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=2, foreground=c)])
        elif span > 3:
            ax.text(mid, lr, ch, fontsize=5, fontweight='bold',
                    color='white', ha='center', va='center',
                    rotation=rot, rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=1.8, foreground=c)])

    # ── Branches + leaf dots ──
    for a, ci in leaf_pos:
        c = CHAPTER_COLORS.get(ci['chapter'], '#999')
        ax.plot([a, a], [r_br, r_leaf], color=c, lw=0.25, alpha=0.35)
        ns = max(1, min(10, 1 + ci['patients'] * 0.2))
        ax.scatter(a, r_leaf, s=ns, c=c, alpha=0.55, edgecolors='none', zorder=3)

    # ── ID/OOD band ──
    bw = 2 * math.pi / total_leaves * 0.9
    for a, ci in leaf_pos:
        c = ID_COLOR if ci['domain'] == 'ID' else OOD_COLOR
        ax.bar(a, r_id_out - r_id_in, width=bw, bottom=r_id_in,
               color=c, alpha=0.80, edgecolor='none')

    # ── Rare/Non-rare band ──
    for a, ci in leaf_pos:
        c = RARE_COLOR if ci['is_rare'] else NONRARE_COLOR
        ax.bar(a, r_rr_out - r_rr_in, width=bw, bottom=r_rr_in,
               color=c, alpha=0.80, edgecolor='none')

    # ── Band labels — draw thin reference arcs + labels at fixed angle ──
    # Place labels using fig text near the outer edge of the polar plot
    # Draw thin grey reference lines at the boundary of ID/OOD and Rare bands
    ref_th = np.linspace(0, 2 * math.pi, 300)
    ax.plot(ref_th, [r_id_in] * 300, color='#cccccc', lw=0.3, alpha=0.5)
    ax.plot(ref_th, [r_id_out] * 300, color='#cccccc', lw=0.3, alpha=0.5)
    ax.plot(ref_th, [r_rr_in] * 300, color='#cccccc', lw=0.3, alpha=0.5)
    ax.plot(ref_th, [r_rr_out] * 300, color='#cccccc', lw=0.3, alpha=0.5)

    # ── Center text ──
    ax.text(0, 0, 'OrthoBench',
            ha='center', va='center', fontsize=14, fontweight='bold',
            color='#333333',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])
    ax.text(0, -0.08, '1,000 diseases\n5,905 patients\n11 clinical tasks',
            ha='center', va='center', fontsize=7.5, color='#666666',
            linespacing=1.4,
            path_effects=[pe.withStroke(linewidth=2, foreground='white')])

    # ── Styling ──
    ax.set_ylim(0, 1.0)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines['polar'].set_visible(False)
    ax.grid(False)

    # ════════════════════════════════════════════════════════════════
    #  Right-side legend panel (non-polar axes)
    # ════════════════════════════════════════════════════════════════
    ax_leg = fig.add_axes([0.73, 0.08, 0.26, 0.88])
    ax_leg.set_xlim(0, 10)
    ax_leg.set_ylim(0, 100)
    ax_leg.axis('off')

    # ── ICD-10 Chapter Legend ──
    ax_leg.text(0.5, 97, 'ICD-10 Chapters', fontsize=8, fontweight='bold',
                color='#333333', va='top')
    y = 94
    for ch in tree.keys():
        c = CHAPTER_COLORS.get(ch, '#999')
        n = sum(len(v) for v in tree[ch].values())
        nm = CHAPTER_NAMES.get(ch, ch)
        rect = plt.Rectangle((0.5, y - 1.2), 1.2, 1.6, facecolor=c,
                              edgecolor='none')
        ax_leg.add_patch(rect)
        ax_leg.text(2.2, y - 0.4, f'{ch}: {nm} ({n})',
                    fontsize=5.5, va='center', color='#444444')
        y -= 3.2

    # ── Stratification Legend ──
    y -= 3
    ax_leg.text(0.5, y, 'Stratification Bands', fontsize=8,
                fontweight='bold', color='#333333', va='top')
    y -= 2.5
    ax_leg.text(0.5, y, 'Inner ring: ID / OOD', fontsize=5, va='center',
                color='#888888', style='italic')
    y -= 2.5
    strat_id = [
        (ID_COLOR, 'In-distribution (ID)'),
        (OOD_COLOR, 'Out-of-distribution (OOD)'),
    ]
    for c, lab in strat_id:
        rect = plt.Rectangle((0.5, y - 1.2), 1.2, 1.6, facecolor=c,
                              edgecolor='none')
        ax_leg.add_patch(rect)
        ax_leg.text(2.2, y - 0.4, lab, fontsize=5.5, va='center',
                    color='#444444')
        y -= 3.0
    y -= 1
    ax_leg.text(0.5, y, 'Outer ring: Rare / Non-rare', fontsize=5,
                va='center', color='#888888', style='italic')
    y -= 2.5
    strat_rr = [
        (RARE_COLOR, 'Rare disease'),
        (NONRARE_COLOR, 'Non-rare disease'),
    ]
    for c, lab in strat_rr:
        rect = plt.Rectangle((0.5, y - 1.2), 1.2, 1.6, facecolor=c,
                              edgecolor='none')
        ax_leg.add_patch(rect)
        ax_leg.text(2.2, y - 0.4, lab, fontsize=5.5, va='center',
                    color='#444444')
        y -= 3.0

    # ── Key Statistics ──
    y -= 3
    ax_leg.text(0.5, y, 'Key Statistics', fontsize=8,
                fontweight='bold', color='#333333', va='top')
    y -= 3
    stats = [
        ('180,000', 'patient cohort (2004-2024)'),
        ('1,000', 'ICD-10 disease codes'),
        ('16', 'ICD-10 chapters'),
        ('5,905', 'test patients'),
        ('135,745', 'evaluation instances'),
        ('11', 'clinical tasks'),
        ('3', 'question types'),
    ]
    for num, desc in stats:
        ax_leg.text(0.5, y, num, fontsize=7, fontweight='bold',
                    color='#E8918C', va='center')
        ax_leg.text(3.5, y, desc, fontsize=5, va='center', color='#666666')
        y -= 2.8

    # ── Save ──
    for ext in ['pdf', 'png']:
        p = os.path.join(OUT_DIR, f'main_figure.{ext}')
        fig.savefig(p, dpi=400, bbox_inches='tight', pad_inches=0.1,
                    facecolor='white')
        print(f"Saved: {p}")
    plt.close(fig)


def main():
    print("Loading benchmark data...")
    codes = load_benchmark_data()
    print(f"Loaded {len(codes)} codes")
    tree = build_hierarchy(codes)
    print("Drawing main figure...")
    draw_main_figure(tree)
    print("Done!")


if __name__ == '__main__':
    main()
