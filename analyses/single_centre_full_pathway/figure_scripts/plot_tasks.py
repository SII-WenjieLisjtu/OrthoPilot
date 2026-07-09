#!/usr/bin/env python3
"""
Plot bar charts for each task in Nature journal style.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# Set Liberation Sans font (Arial alternative)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Liberation Sans', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Paths
DATA_FILE = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv'
OUT_DIR = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/figure/task_grouping'
os.makedirs(OUT_DIR, exist_ok=True)

# Read data
df = pd.read_csv(DATA_FILE)

# Filter out Qwen3-8B and HuatuoGPT-o1-7B
df = df[~df['model'].isin(['Qwen3-8B', 'HuatuoGPT-o1-7B'])].copy()

# Nature journal palette based on requested tones
model_colors = {
    'OrthoPilot': '#92B1D9',
    'CHEESE': '#F6C8B6',
    'GPT-5.1': '#C1D8E9',
    'Grok-4': '#DBDDEF',
    'Claude-Sonnet-4.5': '#B8D4E8',
    'Kimi-K2': '#A5C4E0',
    'DeepSeek-R1': '#E8D4C8',
    'DeepSeek-V3': '#B0CDDE',
    'Qwen3-235B': '#CCC8E5',
    'GPT-oss-120B': '#F0BAAA',
    'Gemini-2.5-flash': '#C8C8D8',
    'Mistral-Large': '#DCEAF3',
    'Qwen3-32B': '#E5E0ED',
    'GPT-4o': '#FDDAC4',
    'Llama-4-Maverick': '#D8E8D8',
    'Llama-3.3-70B': '#AEC8DB',
    'Phi-4': '#D8D2E6',
    'MedGemma-27B': '#EDC1B2',
    'HuatuoGPT-o1-72B': '#BFD1DD',
    'OpenBioLLM-70B': '#DDD6E1',
    'MDAgents-GPT4o': '#A8D5A2',
    'MDAgents-DeepSeek': '#7FBF7F',
}

# Task names
task_names = {
    1: 'Admission diagnosis',
    2: 'Preoperative diagnosis',
    3: 'Intraoperative diagnosis',
    4: 'Discharge diagnosis',
    5: 'Perioperative risk assessment',
    6: 'Surgical approach selection',
    7: 'Operative note generation',
    8: 'Postoperative order writing',
    9: 'Discharge summary generation',
    10: 'Rehabilitation planning',
    11: 'Multidisciplinary consultation',
}

# Closed tasks (1-4) use Acc, open tasks (5-11) use Score
closed_tasks = {1, 2, 3, 4}

def plot_task(task_id):
    """Plot bar chart for a single task."""
    col = f'task{task_id}'
    task_data = df[['model', col]].copy()
    task_data = task_data.dropna()

    # Separate our models from others
    our_models = task_data[task_data['model'].isin(['CHEESE', 'OrthoPilot'])]
    other_models = task_data[~task_data['model'].isin(['CHEESE', 'OrthoPilot'])]

    # Sort others by score descending
    other_models = other_models.sort_values(col, ascending=False)

    # Combine: others first, then CHEESE, then OrthoPilot
    our_models = our_models.sort_values('model')
    plot_data = pd.concat([other_models, our_models])

    models = plot_data['model'].values
    models = [m.replace('MDAgents-GPT4o', 'MDAgents (GPT-4o)').replace('MDAgents-DeepSeek', 'MDAgents (DeepSeek)') for m in models]
    scores = plot_data[col].values

    # Set y-axis limits for better contrast
    min_score = scores.min()
    max_score = scores.max()
    y_range = max_score - min_score
    y_min = max(0, min_score - y_range * 0.15)
    y_max = max_score + y_range * 0.12

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 5.7))

    # Bar positions - minimal gaps between bars
    n = len(models)
    bar_width = 0.65
    x_pos = np.arange(n)

    # Plot bars
    for i, (model, score) in enumerate(zip(models, scores)):
        color = model_colors.get(model, '#E0E0E0')

        if model == 'OrthoPilot':
            ax.bar(x_pos[i], score, bar_width, color=color,
                  edgecolor='#6E6E6E', linewidth=0.8,
                  hatch='///', alpha=0.9)
        else:
            ax.bar(x_pos[i], score, bar_width, color=color,
                  edgecolor='#787878', linewidth=0.8, alpha=0.9)

        # Add value labels on top of bars — avoid overlap by checking proximity
        ax.text(x_pos[i], score + y_range * 0.025, f'{score:.1f}',
               ha='center', va='bottom', fontsize=9, fontweight='normal')

    # Y-axis label: Acc (%) for closed tasks, Score (%) for open tasks
    if task_id in closed_tasks:
        ylabel = 'Acc (%)'
    else:
        ylabel = 'Score (%)'

    ax.set_ylabel(ylabel, fontsize=14, fontweight='normal')
    ax.set_title(task_names[task_id], fontsize=24, fontweight='bold', pad=6)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(models, rotation=45, ha='right', fontsize=14)
    ax.set_ylim(y_min, y_max)

    # Remove grid
    ax.grid(False)

    # Adjust spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)

    # Bars start closer to y-axis, minimal padding
    ax.set_xlim(-0.5, n - 0.5)

    # Tick parameters
    ax.tick_params(axis='both', which='major', labelsize=14, width=0.8)
    ax.tick_params(axis='x', pad=3)
    ax.tick_params(axis='y', labelsize=14)

    plt.tight_layout()
    return fig

# Plot closed tasks only (1–4); open tasks 5–11 → see plot_open_tasks_radar.py
print("Plotting task bar charts (closed tasks 1–4)...")
for task_id in range(1, 5):
    fig = plot_task(task_id)

    out_file = f'{OUT_DIR}/task{task_id}_{task_names[task_id].replace(" ", "_").lower()}.pdf'
    plt.savefig(out_file, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(out_file.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved: task{task_id} - {task_names[task_id]}")

# Create separate legend
print("\nCreating legend...")
fig_legend, ax_legend = plt.subplots(figsize=(12, 1.8))
ax_legend.axis('off')

# Get all models in display order
all_models = list(df[~df['model'].isin(['CHEESE', 'OrthoPilot'])]['model'].unique())
all_models += ['CHEESE', 'OrthoPilot']

# Create legend patches
patches = []
labels = []
for model in all_models:
    color = model_colors.get(model, '#E0E0E0')
    if model == 'OrthoPilot':
        patch = mpatches.Patch(facecolor=color, edgecolor='#6E6E6E',
                              linewidth=0.8, hatch='///', alpha=0.9, label=f'{model} (w/ tool use)')
    else:
        patch = mpatches.Patch(facecolor=color, edgecolor='#787878',
                              linewidth=0.8, alpha=0.9, label=model)
    patches.append(patch)
    labels.append(patch.get_label())

# Create legend with 2 rows
legend = ax_legend.legend(patches, labels, loc='center', ncol=10,
                         frameon=False, fontsize=12,
                         prop={'family': 'sans-serif', 'size': 12},
                         handlelength=1.5, handleheight=1.2,
                         columnspacing=1.0, labelspacing=0.8)

plt.tight_layout()
plt.savefig(f'{OUT_DIR}/legend.pdf', dpi=300, bbox_inches='tight', format='pdf')
plt.savefig(f'{OUT_DIR}/legend.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: legend")

print(f"\n✓ All plots saved to: {OUT_DIR}/")
