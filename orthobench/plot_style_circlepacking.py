#!/usr/bin/env python3
"""
OrthoBench Main Figure — two separate panels:

Left:  Simplified circular dendrogram (chapter arcs + rare/non-rare band only).
Right: Horizontal bar chart (disease count per chapter, no icons).
"""

import os, csv, math
import numpy as np
from collections import defaultdict, OrderedDict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
from matplotlib.colors import to_rgba
import matplotlib.patheffects as pe

# ── Nature-style font (Liberation Sans ≡ Arial metrics) ──
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Liberation Sans', 'Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['mathtext.fontset'] = 'custom'
plt.rcParams['mathtext.rm'] = 'Liberation Sans'

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT_STATS = os.path.join(BASE, "gen_validation", "test_final", "split_stats_by_code.csv")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Palette ──
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
RARE_COLOR = '#B088C4'
NONRARE_COLOR = '#D0D4D8'


def load_data():
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
                'category': code[:3],
                'domain': domain,
                'is_rare': row['is_rare'].strip() == 'True',
                'patients': max(1, float(row['test_patient_count'])),
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


# ═══════════════════════════════════════════════════════════════
# LEFT: Simplified circular dendrogram
# ═══════════════════════════════════════════════════════════════

def draw_left(codes, tree):
    """Circular dendrogram: chapter arcs + rare/non-rare band only.
    No ID/OOD band, no leaf dots/branches."""

    total_leaves = sum(len(v) for d in tree.values() for v in d.values())
    n_rare = sum(1 for c in codes if c['is_rare'])

    # ── Angular layout ──
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

    # ── Radial layers (simplified: chapter arc + rare band only) ──
    r_ch_in  = 0.28
    r_ch_out = 0.48
    r_rr_in  = 0.51
    r_rr_out = 0.64

    # ── Figure ──
    fig_w = 100 / 25.4
    fig_h = 120 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.90], projection='polar')

    # ── Chapter arc bands ──
    for ch, (sa, ea) in ch_ranges.items():
        c = CHAPTER_COLORS.get(ch, '#999')
        n = max(60, int((ea - sa) * 120))
        th = np.linspace(sa, ea, n)

        # Faint background fill extending to rare band
        ax.fill_between(th, r_ch_in, r_rr_out + 0.005,
                        color=to_rgba(c, 0.04), edgecolor='none')
        # Solid chapter arc
        ax.fill_between(th, r_ch_in, r_ch_out,
                        color=to_rgba(c, 0.70), edgecolor='none')
        ax.plot(th, [r_ch_out]*n, color=c, lw=0.8)
        ax.plot(th, [r_ch_in]*n, color=c, lw=0.4)
        ax.plot([sa, sa], [r_ch_in, r_ch_out], color=c, lw=0.5, alpha=0.7)
        ax.plot([ea, ea], [r_ch_in, r_ch_out], color=c, lw=0.5, alpha=0.7)

        # Chapter label — name only, no numbers
        mid = (sa + ea) / 2
        span = math.degrees(ea - sa)
        lr = (r_ch_in + r_ch_out) / 2
        ad = math.degrees(mid)
        ch_name = CHAPTER_NAMES.get(ch, ch)
        rot = ad + 180 if 90 < ad < 270 else ad
        if span > 18:
            ax.text(mid, lr, ch_name,
                    fontsize=6, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rot,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=2.5, foreground=c)])
        elif span > 8:
            ax.text(mid, lr, ch_name,
                    fontsize=4.5, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rot,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=2, foreground=c)])
        elif span > 3:
            ax.text(mid, lr, ch, fontsize=5, fontweight='bold',
                    color='white', ha='center', va='center',
                    rotation=rot, rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=1.8, foreground=c)])

    # ── Rare/Non-rare band ──
    bw = 2 * math.pi / total_leaves * 0.9
    for a, ci in leaf_pos:
        c = RARE_COLOR if ci['is_rare'] else NONRARE_COLOR
        ax.bar(a, r_rr_out - r_rr_in, width=bw, bottom=r_rr_in,
               color=c, alpha=0.80, edgecolor='none')

    # Thin reference circles
    ref_th = np.linspace(0, 2 * math.pi, 300)
    ax.plot(ref_th, [r_rr_in]*300, color='#cccccc', lw=0.3, alpha=0.5)
    ax.plot(ref_th, [r_rr_out]*300, color='#cccccc', lw=0.3, alpha=0.5)

    # ── Center text ──
    ax.text(0, 0, 'OrthoBench',
            ha='center', va='center', fontsize=13, fontweight='bold',
            color='#333333',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])

    # ── Styling ──
    ax.set_ylim(0, 0.74)
    ax.set_yticks([]); ax.set_xticks([])
    ax.spines['polar'].set_visible(False)
    ax.grid(False)

    # ── Legend: only rare/non-rare, below the circle ──
    ax_leg = fig.add_axes([0.10, 0.02, 0.80, 0.04])
    ax_leg.set_xlim(0, 10)
    ax_leg.set_ylim(0, 1.2)
    ax_leg.axis('off')

    leg_items = [
        (RARE_COLOR, f'Rare disease ({n_rare})'),
        (NONRARE_COLOR, f'Non-rare disease ({total_leaves - n_rare})'),
    ]
    x_positions = [2.0, 6.0]
    for idx, (col, label) in enumerate(leg_items):
        cx = x_positions[idx]
        rect = plt.Rectangle((cx - 0.3, 0.3), 0.55, 0.55,
                              facecolor=col, edgecolor='none', alpha=0.8)
        ax_leg.add_patch(rect)
        ax_leg.text(cx + 0.5, 0.57, label, fontsize=5.5, va='center',
                    color='#444444')

    # ── Save ──
    for ext in ['png', 'pdf']:
        p = os.path.join(OUT_DIR, f'circlepacking_left.{ext}')
        fig.savefig(p, dpi=400, bbox_inches='tight', pad_inches=0.05,
                    facecolor='white')
        print(f"Saved: {p}")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# RIGHT: Horizontal bar chart (no icons)
# ═══════════════════════════════════════════════════════════════

def draw_right(codes, hierarchy, ch_order):
    """Horizontal bar chart sorted by disease count, no icons."""

    ch_disease_counts = {ch: sum(len(v) for v in hierarchy[ch].values())
                         for ch in hierarchy}
    sorted_chs = sorted(ch_order, key=lambda c: -ch_disease_counts[c])
    n_ch = len(sorted_chs)
    max_count = max(ch_disease_counts.values())

    bar_h = 0.20
    row_spacing = bar_h + 0.03  # 0.03 gap
    total_bar_height = (n_ch - 1) * row_spacing + bar_h

    fig_w = 140 / 25.4
    fig_h = 100 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h))

    ax_bar = fig.add_axes([0.26, 0.03, 0.68, 0.94])
    ax_bar.set_xlim(0, max_count * 1.10)
    ax_bar.set_ylim(-row_spacing * 0.5, total_bar_height + row_spacing * 0.3)
    ax_bar.invert_yaxis()
    for sp in ax_bar.spines.values():
        sp.set_visible(False)
    ax_bar.set_xticks([]); ax_bar.set_yticks([])

    # Draw bars
    for i, ch in enumerate(sorted_chs):
        color = CHAPTER_COLORS.get(ch, '#999')
        n = ch_disease_counts[ch]
        name = CHAPTER_NAMES.get(ch, ch)
        y_pos = i * row_spacing

        ax_bar.barh(y_pos, n, height=bar_h, color=to_rgba(color, 0.35),
                    edgecolor='none', linewidth=0)
        # Count at bar end
        ax_bar.text(n + max_count * 0.02, y_pos, str(n),
                    ha='left', va='center', fontsize=8, color='#555555')

    # Place names to the left of bars using figure coords
    fig.canvas.draw()
    for i, ch in enumerate(sorted_chs):
        name = CHAPTER_NAMES.get(ch, ch)
        y_pos = i * row_spacing

        bar_left_disp = ax_bar.transData.transform((0, y_pos))
        bar_left_fig = fig.transFigure.inverted().transform(bar_left_disp)
        fig.text(bar_left_fig[0] - 0.01, bar_left_fig[1], name,
                 ha='right', va='center', fontsize=8, color='#333333')

    # Save
    for ext in ['png', 'pdf']:
        p = os.path.join(OUT_DIR, f'circlepacking_right.{ext}')
        fig.savefig(p, dpi=400, bbox_inches='tight', pad_inches=0.05,
                    facecolor='white')
        print(f"Saved: {p}")
    plt.close(fig)


def main():
    codes = load_data()
    print(f"Loaded {len(codes)} codes")

    hierarchy = defaultdict(lambda: defaultdict(list))
    for c in codes:
        hierarchy[c['chapter']][c['category']].append(c)
    ch_totals = {ch: sum(c['patients'] for cats in hierarchy[ch].values()
                         for c in cats) for ch in hierarchy}
    ch_order = sorted(hierarchy.keys(), key=lambda k: -ch_totals[k])

    tree = build_hierarchy(codes)

    print("Drawing left figure (circular dendrogram)...")
    draw_left(codes, tree)
    print("Drawing right figure (bar chart)...")
    draw_right(codes, hierarchy, ch_order)
    print("Done!")


if __name__ == '__main__':
    main()
