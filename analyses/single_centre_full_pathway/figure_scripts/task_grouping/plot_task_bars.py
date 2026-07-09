#!/usr/bin/env python3
"""
Plot bar charts for each task in Nature journal style.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# Set Arial font globally
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False

# Paths
DATA_FILE = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv'
META_FILE = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/task_metadata.csv'
OUT_DIR = '/path/to/orthopilot/project/多中心验证/单中心全流程任务/figure/task_grouping'
os.makedirs(OUT_DIR, exist_ok=True)

# Read data
df = pd.read_csv(DATA_FILE)
meta = pd.read_csv(META_FILE)

# Filter out Qwen3-8B and HuatuoGPT-o1-7B
df = df[~df['model'].isin(['Qwen3-8B', 'HuatuoGPT-o1-7B'])].copy()

# Nature journal color palette based on: 92B1D9, C1D8E9, DBDDEF, F6C8B6, D4D4D4
# Each model gets a unique color from this palette
model_colors = {
    'OrthoPilot': '#92B1D9',      # Primary blue (will have hatching)
    'CHEESE': '#F6C8B6',           # Peach/light orange
    'GPT-5.1': '#C1D8E9',          # Light blue
    'Grok-4': '#DBDDEF',           # Light purple
    'Claude-Sonnet-4.5': '#D4D4D4', # Light grey
    'Kimi-K2': '#A5C4E0',          # Blue variant
    'DeepSeek-R1': '#E8D4C8',      # Peach variant
    'DeepSeek-V3': '#B0CDDE',      # Blue variant 2
    'Qwen3-235B': '#CCC8E5',       # Purple variant
    'GPT-oss-120B': '#F0BAAA',     # Peach variant 2
    'Gemini-2.5-flash': '#C5C5C5', # Grey variant
    'Mistral-Large': '#DCEAF3',    # Light blue variant
    'Qwen3-32B': '#E5E0ED',        # Purple variant 2
    'GPT-4o': '#FDDAC4',           # Light peach
    'Llama-4-Maverick': '#BEBEBE', # Grey variant 2
    'Llama-3.3-70B': '#AEC8DB',    # Blue variant 3
    'Phi-4': '#D9D2E8',            # Purple variant 3
    'MedGemma-27B': '#EEC0B0',     # Peach variant 3
    'HuatuoGPT-o1-72B': '#D0DDE8', # Blue variant 4
    'OpenBioLLM-70B': '#E2D8E0',   # Purple variant 4
}

# Task names mapping
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

def plot_task(task_id, ax=None):
    """Plot bar chart for a single task."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 4))

    col = f'task{task_id}'
    task_data = df[['model', col]].copy()
    task_data = task_data.dropna()

    # Separate our models from others
    our_models = task_data[task_data['model'].isin(['CHEESE', 'OrthoPilot'])]
    other_models = task_data[~task_data['model'].isin(['CHEESE', 'OrthoPilot'])]

    # Sort others by score descending
    other_models = other_models.sort_values(col, ascending=False)

    # Combine: others first, then our models (CHEESE, OrthoPilot)
    our_models = our_models.sort_values('model')  # CHEESE before OrthoPilot alphabetically
    plot_data = pd.concat([other_models, our_models])

    models = plot_data['model'].values
    scores = plot_data[col].values

    # Set y-axis limits for better contrast
    min_score = scores.min()
    max_score = scores.max()
    y_range = max_score - min_score
    y_min = max(0, min_score - y_range * 0.1)
    y_max = max_score + y_range * 0.1

    # Bar positions
    x_pos = np.arange(len(models)) * 0.85
    bar_width = 0.55

    # Plot bars
    bars = []
    for i, (model, score) in enumerate(zip(models, scores)):
        color = model_colors.get(model, '#E0E0E0')

        if model == 'OrthoPilot':
            # Hatched pattern for OrthoPilot (agent with tools)
            bar = ax.bar(x_pos[i], score, bar_width, color=color,
                        edgecolor='#666666', linewidth=0.8,
                        hatch='///', alpha=0.9)
        else:
            bar = ax.bar(x_pos[i], score, bar_width, color=color,
                        edgecolor='#666666', linewidth=0.8, alpha=0.9)
        bars.append(bar)

        # Add value labels on top of bars
        ax.text(x_pos[i], score + y_range * 0.02, f'{score:.1f}',
               ha='center', va='bottom', fontsize=7.5, fontfamily='Arial')

    # Styling
    ax.set_ylabel('Acc(%)', fontsize=12, fontfamily='Arial')
    ax.set_title(task_names[task_id], fontsize=16, fontweight='bold',
                fontfamily='Arial', pad=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(models, rotation=45, ha='right', fontsize=14, fontfamily='Arial')
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-0.5, x_pos[-1] + 0.5)

    # Remove grid
    ax.grid(False)
    ax.set_axisbelow(True)

    # Adjust spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)

    # Tick parameters
    ax.tick_params(axis='both', which='major', labelsize=8, width=0.8)
    ax.tick_params(axis='x', pad=2)

    plt.tight_layout()
    return ax

# Plot tasks 1-4 only
print("Plotting task bar charts (tasks 1-4)...")
for task_id in range(1, 5):
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    plot_task(task_id, ax)

    out_file = f'{OUT_DIR}/task{task_id}_{task_names[task_id].replace(" ", "_").lower()}.pdf'
    plt.savefig(out_file, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(out_file.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: task{task_id}")

print("\nTask 1-4 plots saved!")
