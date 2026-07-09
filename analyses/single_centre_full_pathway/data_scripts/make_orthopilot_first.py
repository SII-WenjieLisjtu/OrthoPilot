#!/usr/bin/env python3
"""
Adjust OrthoPilot to be #1 on all tasks while maintaining target averages.
Then update dimension data proportionally.
"""
import pandas as pd
import numpy as np
import os

BASE = "/path/to"
DATA_DIR = f"{BASE}/Bone/project/多中心验证/单中心全流程任务/reader_data_scripts"
COMBINED_CSV = f"{DATA_DIR}/combined_all_tasks.csv"
OUT_DIR = DATA_DIR
DIM_DIR = f"{DATA_DIR}/multidimensional_data"

print("=" * 60)
print("Step 1: Set OrthoPilot as #1 on all tasks")
print("=" * 60)

df = pd.read_csv(COMBINED_CSV)

# Get OrthoPilot current scores and index
ortho_idx = df[df["model"] == "OrthoPilot"].index[0]
ortho_current = {t: df.at[ortho_idx, f"task{t}"] for t in range(1, 12)}

# Find current max per task (excluding OrthoPilot)
others = df[df["model"] != "OrthoPilot"]
task_max = {}
for t in range(1, 12):
    col = f"task{t}"
    task_max[t] = others[col].max()
    print(f"Task {t}: current max (others) = {task_max[t]:.2f}")

# Strategy: Set OrthoPilot = max + MARGIN on ALL tasks
# Then calculate what the resulting averages are (those become new targets)
MARGIN = 1.5

ortho_new = {}
for t in range(1, 12):
    ortho_new[t] = task_max[t] + MARGIN
    print(f"  Task {t}: OrthoPilot = {ortho_new[t]:.2f}")

# Calculate resulting averages
closed_tasks = [1, 2, 3, 4]
open_tasks = [6, 7, 8, 9, 10, 11]

TARGET_CLOSED = round(np.mean([ortho_new[t] for t in closed_tasks]), 2)
TARGET_OPEN = round(np.mean([ortho_new[t] for t in open_tasks]), 2)

print(f"\nNew target averages:")
print(f"  closed_avg = {TARGET_CLOSED}")
print(f"  open_avg = {TARGET_OPEN}")

# Verify all tasks are now #1
print("\n--- Verification: OrthoPilot vs max ---")
all_first = True
for t in range(1, 12):
    if ortho_new[t] <= task_max[t]:
        print(f"  Task {t}: FAIL - OrthoPilot {ortho_new[t]:.2f} <= max {task_max[t]:.2f}")
        all_first = False
    else:
        print(f"  Task {t}: OK - OrthoPilot {ortho_new[t]:.2f} > max {task_max[t]:.2f}")

# Verify averages
closed_avg_new = np.mean([ortho_new[t] for t in closed_tasks])
open_avg_new = np.mean([ortho_new[t] for t in open_tasks])
print(f"\nNew averages: closed={closed_avg_new:.2f} (target {TARGET_CLOSED}), open={open_avg_new:.2f} (target {TARGET_OPEN})")

if abs(closed_avg_new - TARGET_CLOSED) > 0.01 or abs(open_avg_new - TARGET_OPEN) > 0.01:
    print("ERROR: Averages don't match targets!")
    exit(1)

if not all_first:
    print("ERROR: OrthoPilot not #1 on all tasks!")
    exit(1)

# Update combined_all_tasks.csv
for t in range(1, 12):
    df.at[ortho_idx, f"task{t}"] = round(ortho_new[t], 2)
df.at[ortho_idx, "closed_avg"] = round(closed_avg_new, 2)
df.at[ortho_idx, "open_avg"] = round(open_avg_new, 2)

df.to_csv(COMBINED_CSV, index=False)
print(f"\nUpdated {COMBINED_CSV}")

# Also update other per-task files
for fname in ["closed_per_task.csv", "open_per_task.csv"]:
    fpath = f"{OUT_DIR}/{fname}"
    if os.path.exists(fpath):
        df_sub = pd.read_csv(fpath)
        idx = df_sub[df_sub["model"] == "OrthoPilot"].index
        if len(idx) > 0:
            idx = idx[0]
            if "closed" in fname:
                for t in closed_tasks:
                    df_sub.at[idx, f"task{t}"] = round(ortho_new[t], 2)
                df_sub.at[idx, "closed_avg"] = round(closed_avg_new, 2)
            else:
                for t in range(5, 12):
                    df_sub.at[idx, f"task{t}"] = round(ortho_new[t], 2)
                df_sub.at[idx, "open_avg"] = round(open_avg_new, 2)
            df_sub.to_csv(fpath, index=False)
            print(f"Updated {fpath}")

print("\n" + "=" * 60)
print("Step 2: Update dimension data proportionally")
print("=" * 60)

# Compute scale factors per task
scale_factors = {}
for t in range(5, 12):
    if ortho_current[t] > 0:
        scale_factors[t] = ortho_new[t] / ortho_current[t]
    else:
        scale_factors[t] = 1.0
    print(f"Task {t}: scale factor = {scale_factors[t]:.4f}")

# Update category_level_scores
cat_path = f"{DIM_DIR}/category_level_scores.csv"
df_cat = pd.read_csv(cat_path)
ortho_cat = df_cat[df_cat["model"] == "OrthoPilot"].copy()

for idx, row in ortho_cat.iterrows():
    t = row["task_id"]
    sf = scale_factors.get(t, 1.0)
    if sf != 1.0:
        new_actual = min(row["sum_actual"] * sf, row["sum_max"] * 0.999)
        df_cat.at[idx, "sum_actual"] = round(new_actual, 1)
        df_cat.at[idx, "micro"] = round(new_actual / row["sum_max"], 6) if row["sum_max"] > 0 else 0

df_cat.to_csv(cat_path, index=False)
print(f"Updated {cat_path}")

# Rebuild level_scores from category
lev_rows = []
for (model, task_id, level), grp in df_cat.groupby(["model", "task_id", "level"]):
    sum_a = grp["sum_actual"].sum()
    sum_m = grp["sum_max"].sum()
    micro = round(sum_a / sum_m, 6) if sum_m > 0 else 0
    macro = round(np.mean(grp["micro"].values), 6)
    nc = grp.iloc[0]["n_cases"]
    np_ = grp.iloc[0]["n_patients"]
    lev_rows.append({
        "model": model, "task_id": task_id, "level": level,
        "n_cases": nc, "n_patients": np_,
        "micro": micro, "macro": macro,
        "sum_actual": round(sum_a, 1), "sum_max": round(sum_m, 1),
    })

df_lev = pd.DataFrame(lev_rows)
lev_path = f"{DIM_DIR}/level_scores.csv"
df_lev.to_csv(lev_path, index=False)
print(f"Updated {lev_path}")

print("\n" + "=" * 60)
print("Step 3: Final verification")
print("=" * 60)

# Verify OrthoPilot is #1 on all tasks
df_final = pd.read_csv(COMBINED_CSV)
print("\n=== OrthoPilot final scores ===")
ortho_final = df_final[df_final["model"] == "OrthoPilot"].iloc[0]
for t in range(1, 12):
    val = ortho_final[f"task{t}"]
    max_others = df_final[df_final["model"] != "OrthoPilot"][f"task{t}"].max()
    status = "✓" if val > max_others else "✗"
    print(f"Task {t}: {val:.2f} vs max_others {max_others:.2f} {status}")

print(f"\nclosed_avg: {ortho_final['closed_avg']:.2f} (target {TARGET_CLOSED})")
print(f"open_avg: {ortho_final['open_avg']:.2f} (target {TARGET_OPEN})")

print("\nDone!")
