#!/usr/bin/env python3
"""
Circular Disease Dendrogram (Radial Cladogram) for OrthoBench — v2.
Visualises 1,000 benchmark diseases organised by ICD-10 hierarchy:
  ICD Chapter → ICD Category (3-char) → Disease code (leaf)

Iteration 2 improvements:
  - Tighter radial layout with more space for labels
  - Better chapter name placement (outside the arc)
  - Category-level grouping lines
  - Improved label readability
  - Cleaner legend placement
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
from matplotlib.patches import Wedge
from matplotlib.colors import to_rgba
import matplotlib.patheffects as pe

# ── Paths ─────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT_STATS = os.path.join(BASE, "gen_validation", "test_final", "split_stats_by_code.csv")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icd_mapping import build_icd_mapping

# ── NPG palette ───────────────────────────────────────────────────
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

ID_COLOR  = '#7DBAD5'   # 柔蓝（reference_figures中的蓝色）
OOD_COLOR = '#E8918C'   # 柔粉（reference_figures中的粉色）
RARE_COLOR   = '#B088C4' # 柔紫
NONRARE_COLOR = '#D0D4D8' # 浅灰


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
                'code': code,
                'chapter': code[0].upper(),
                'category': code[:3],
                'domain': domain,
                'is_rare': row['is_rare'].strip() == 'True',
                'patients': float(row['test_patient_count']),
            })
    return codes


def build_hierarchy(codes):
    tree = OrderedDict()
    chapter_counts = defaultdict(int)
    for c in codes:
        chapter_counts[c['chapter']] += 1
    chapter_order = sorted(chapter_counts.keys(), key=lambda ch: -chapter_counts[ch])
    for ch in chapter_order:
        ch_codes = [c for c in codes if c['chapter'] == ch]
        cat_counts = defaultdict(int)
        for c in ch_codes:
            cat_counts[c['category']] += 1
        cat_order = sorted(cat_counts.keys(), key=lambda cat: -cat_counts[cat])
        tree[ch] = OrderedDict()
        for cat in cat_order:
            cat_codes = sorted([c for c in ch_codes if c['category'] == cat],
                               key=lambda c: -c['patients'])
            tree[ch][cat] = cat_codes
    return tree


def draw_circular_tree(tree, code_to_english):
    total_leaves = sum(len(cat_codes) for ch_data in tree.values()
                       for cat_codes in ch_data.values())
    print(f"Total leaves: {total_leaves}")

    # ── Figure setup (large canvas for high-res) ──
    fig_size_mm = 500
    fig_size_in = fig_size_mm / 25.4
    fig, ax = plt.subplots(1, 1, figsize=(fig_size_in, fig_size_in),
                           subplot_kw={'projection': 'polar'})

    # ── Layout parameters ──
    gap_chapter_deg = 3.0  # gap between chapters
    gap_category_deg = 0.3  # small gap between categories within a chapter
    n_chapters = len(tree)
    n_categories = sum(len(ch_data) for ch_data in tree.values())

    # Total angular space for gaps
    total_ch_gap = gap_chapter_deg * n_chapters
    total_cat_gap = gap_category_deg * (n_categories - n_chapters)  # no cat gap at chapter boundaries
    available_degrees = 360.0 - total_ch_gap - total_cat_gap

    # ── Assign angular positions ──
    leaf_positions = []
    chapter_ranges = {}
    category_ranges = {}

    current_angle_deg = 0.0
    for ch, ch_data in tree.items():
        ch_leaf_count = sum(len(v) for v in ch_data.values())
        ch_span_deg = (ch_leaf_count / total_leaves) * available_degrees
        ch_start = current_angle_deg

        cat_offset = 0.0
        for i_cat, (cat, cat_codes) in enumerate(ch_data.items()):
            cat_leaf_count = len(cat_codes)
            cat_span_deg = (cat_leaf_count / total_leaves) * available_degrees

            cat_start = ch_start + cat_offset
            cat_end = cat_start + cat_span_deg
            category_ranges[cat] = (math.radians(cat_start), math.radians(cat_end))

            for j, code_info in enumerate(cat_codes):
                angle_deg = cat_start + (j + 0.5) * (cat_span_deg / cat_leaf_count)
                leaf_positions.append((math.radians(angle_deg), code_info))

            cat_offset += cat_span_deg
            if i_cat < len(ch_data) - 1:
                cat_offset += gap_category_deg

        ch_end = ch_start + cat_offset
        chapter_ranges[ch] = (math.radians(ch_start), math.radians(ch_end))
        current_angle_deg = ch_end + gap_chapter_deg

    # ── Radial layers (expanded, labels pushed outward for more space) ──
    r_chapter_inner = 0.22
    r_chapter_outer = 0.32
    r_cat_tick = 0.35       # category separation tick
    r_branch_start = 0.36
    r_leaf = 0.60           # leaf nodes
    r_id_ood_inner = 0.63
    r_id_ood_outer = 0.70
    r_rare_inner = 0.71
    r_rare_outer = 0.78
    r_label = 0.83          # label start (larger radius = more circumference)

    # ── Draw chapter sector backgrounds (light fill from chapter to branches) ──
    for ch, (start_a, end_a) in chapter_ranges.items():
        color = CHAPTER_COLORS.get(ch, '#999999')
        n_arc = max(50, int((end_a - start_a) * 100))
        thetas = np.linspace(start_a, end_a, n_arc)

        # Light background fill spanning chapter arc to leaf radius
        ax.fill_between(thetas, r_chapter_inner, r_leaf + 0.005,
                        color=to_rgba(color, 0.06), edgecolor='none')

        # Solid chapter arc band
        ax.fill_between(thetas, r_chapter_inner, r_chapter_outer,
                        color=to_rgba(color, 0.65), edgecolor='none')
        ax.plot(thetas, [r_chapter_outer] * n_arc, color=color, linewidth=0.8)
        ax.plot(thetas, [r_chapter_inner] * n_arc, color=color, linewidth=0.4)

        # Radial edge lines
        ax.plot([start_a, start_a], [r_chapter_inner, r_chapter_outer],
                color=color, linewidth=0.5, alpha=0.7)
        ax.plot([end_a, end_a], [r_chapter_inner, r_chapter_outer],
                color=color, linewidth=0.5, alpha=0.7)

        # Chapter label on the arc
        theta_mid = (start_a + end_a) / 2
        ch_name = CHAPTER_NAMES.get(ch, ch)
        ch_leaf_count = sum(len(v) for v in tree[ch].values())
        arc_span_deg = math.degrees(end_a - start_a)

        label_r = (r_chapter_inner + r_chapter_outer) / 2
        angle_deg = math.degrees(theta_mid)
        if 90 < angle_deg < 270:
            rotation = angle_deg + 180
        else:
            rotation = angle_deg

        if arc_span_deg > 8:
            ax.text(theta_mid, label_r, f'{ch_name} ({ch_leaf_count})',
                    fontsize=11.0, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rotation,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=3.5, foreground=color)])
        elif arc_span_deg > 3:
            ax.text(theta_mid, label_r, f'{ch} ({ch_leaf_count})',
                    fontsize=9.0, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rotation,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=3.0, foreground=color)])
        else:
            ax.text(theta_mid, label_r, ch,
                    fontsize=8.0, fontweight='bold', color='white',
                    ha='center', va='center', rotation=rotation,
                    rotation_mode='anchor',
                    path_effects=[pe.withStroke(linewidth=3.0, foreground=color)])

    # ── Draw category separation ticks ──
    for cat, (start_a, end_a) in category_ranges.items():
        ch = cat[0].upper()
        color = CHAPTER_COLORS.get(ch, '#999999')
        # Small tick at category boundary
        ax.plot([start_a, start_a], [r_chapter_outer, r_cat_tick],
                color=color, linewidth=0.2, alpha=0.4)

    # ── Draw branches and leaf nodes ──
    for angle, code_info in leaf_positions:
        ch = code_info['chapter']
        color = CHAPTER_COLORS.get(ch, '#999999')
        patients = code_info['patients']

        # Branch line
        ax.plot([angle, angle], [r_branch_start, r_leaf],
                color=color, linewidth=0.4, alpha=0.4)

        # Leaf node
        node_size = max(1.5, min(18, 1.5 + patients * 0.35))
        ax.scatter(angle, r_leaf, s=node_size, c=color, alpha=0.6,
                   edgecolors='none', zorder=3)

    # ── ID/OOD colour band ──
    bar_w = 2 * math.pi / total_leaves * 0.9
    for angle, code_info in leaf_positions:
        color = ID_COLOR if code_info['domain'] == 'ID' else OOD_COLOR
        ax.bar(angle, r_id_ood_outer - r_id_ood_inner, width=bar_w,
               bottom=r_id_ood_inner, color=color, alpha=0.75, edgecolor='none')

    # ── Rare/Non-rare colour band ──
    for angle, code_info in leaf_positions:
        color = RARE_COLOR if code_info['is_rare'] else NONRARE_COLOR
        ax.bar(angle, r_rare_outer - r_rare_inner, width=bar_w,
               bottom=r_rare_inner, color=color, alpha=0.75, edgecolor='none')

    # ── Disease name labels (staggered to avoid overlap) ──
    r_label_inner = r_label
    r_label_outer = r_label + 0.10  # second layer for odd-indexed labels
    for idx, (angle, code_info) in enumerate(leaf_positions):
        code = code_info['code']
        name = code_to_english.get(code, code)

        ch = code_info['chapter']
        color = CHAPTER_COLORS.get(ch, '#333333')

        angle_deg = math.degrees(angle)
        if 90 < angle_deg < 270:
            rotation = angle_deg + 180
            ha = 'right'
        else:
            rotation = angle_deg
            ha = 'left'

        r_pos = r_label_outer if (idx % 2 == 1) else r_label_inner
        # Leader line from outer band edge to label
        ax.plot([angle, angle], [r_rare_outer + 0.005, r_pos - 0.005],
                color=color, linewidth=0.35, alpha=0.7)
        ax.text(angle, r_pos, name, fontsize=2.8, color=color,
                ha=ha, va='center', rotation=rotation,
                rotation_mode='anchor', alpha=1.0,
                fontfamily='DejaVu Sans', fontweight='bold')

    # ── Styling ──
    ax.set_ylim(0, 1.28)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines['polar'].set_visible(False)
    ax.grid(False)

    # ── Legends (built here, saved separately below) ──
    chapter_patches = []
    for ch in tree.keys():
        ch_count = sum(len(v) for v in tree[ch].values())
        ch_name = CHAPTER_NAMES.get(ch, ch)
        patch = mpatches.Patch(color=CHAPTER_COLORS.get(ch, '#999'),
                               label=f'{ch}: {ch_name} ({ch_count})')
        chapter_patches.append(patch)

    extra_patches = [
        mpatches.Patch(color=ID_COLOR, label='In-distribution (ID)', alpha=0.75),
        mpatches.Patch(color=OOD_COLOR, label='Out-of-distribution (OOD)', alpha=0.75),
        mpatches.Patch(color=RARE_COLOR, label='Rare disease', alpha=0.75),
        mpatches.Patch(color=NONRARE_COLOR, label='Non-rare disease', alpha=0.75),
    ]

    # ── Center text ──
    ax.text(0, 0, 'OrthoBench\n1,000 diseases\n5,905 patients',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color='#333333',
            path_effects=[pe.withStroke(linewidth=3.0, foreground='white')])

    # ── Band labels at specific angles ──
    # Find a sparse angle for band labels
    label_angle_1 = math.radians(5)
    label_angle_2 = math.radians(5)
    ax.annotate('ID / OOD', xy=(label_angle_1, (r_id_ood_inner + r_id_ood_outer) / 2),
                fontsize=8.0, ha='left', va='center', color='white', fontweight='bold',
                path_effects=[pe.withStroke(linewidth=2.5, foreground='#333333')])
    ax.annotate('Rare / Non-rare', xy=(label_angle_2, (r_rare_inner + r_rare_outer) / 2),
                fontsize=8.0, ha='left', va='center', color='white', fontweight='bold',
                path_effects=[pe.withStroke(linewidth=2.5, foreground='#333333')])

    plt.tight_layout()

    # ── Save main figure (no legend) ──
    for ext in ['pdf', 'png']:
        path = os.path.join(OUT_DIR, f'disease_tree_circular.{ext}')
        fig.savefig(path, dpi=400, bbox_inches='tight', pad_inches=0.1, facecolor='white')
        print(f"Saved: {path}")
    plt.close(fig)

    # ── Save legend as a separate figure ──
    fig_leg, ax_leg = plt.subplots(figsize=(4, 7))
    ax_leg.axis('off')
    leg1 = ax_leg.legend(handles=chapter_patches, loc='upper left',
                         bbox_to_anchor=(0.0, 1.0), fontsize=9,
                         title='ICD-10 Chapters (disease codes)', title_fontsize=10,
                         frameon=False, ncol=1, handlelength=1.5)
    ax_leg.add_artist(leg1)
    ax_leg.legend(handles=extra_patches, loc='upper left',
                  bbox_to_anchor=(0.0, 0.28), fontsize=9,
                  title='Stratification bands', title_fontsize=10,
                  frameon=False, handlelength=1.5)
    for ext in ['pdf', 'png']:
        path = os.path.join(OUT_DIR, f'disease_tree_legend.{ext}')
        fig_leg.savefig(path, dpi=600, bbox_inches='tight', facecolor='white')
        print(f"Saved: {path}")
    plt.close(fig_leg)


def main():
    print("Loading benchmark data...")
    codes = load_benchmark_data()
    print(f"Loaded {len(codes)} benchmark codes")

    print("Building ICD mapping...")
    code_to_english, _ = build_icd_mapping()
    print(f"Mapped {len(code_to_english)} codes to English")

    print("Building hierarchy...")
    tree = build_hierarchy(codes)
    for ch, ch_data in tree.items():
        n_codes = sum(len(v) for v in ch_data.values())
        print(f"  {ch}: {len(ch_data)} categories, {n_codes} codes")

    print("Drawing circular tree...")
    draw_circular_tree(tree, code_to_english)
    print("Done!")


if __name__ == '__main__':
    main()
