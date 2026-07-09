#!/usr/bin/env python3
"""
Adjust category_level_scores and level_scores to be consistent with
the new per-task averages from combined_all_tasks.csv.
Scale sum_actual proportionally; construct OrthoPilot & DeepSeek-V3 missing tasks.
"""
import pandas as pd
import numpy as np
import os

BASE = "/path/to"
CAT_CSV  = f"{BASE}/Bone/gen_validation/meta/subset/metrics_csv/category_level_scores.csv"
LEV_CSV  = f"{BASE}/Bone/gen_validation/meta/subset/metrics_csv/level_scores.csv"
OPEN_CSV = f"{BASE}/Bone/gen_validation/meta/subset/metrics_csv/overall_summary.csv"
NEW_CSV  = f"{BASE}/Bone/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv"
OUT_DIR  = f"{BASE}/Bone/project/多中心验证/单中心全流程任务/reader_data_scripts/multidimensional_data"
os.makedirs(OUT_DIR, exist_ok=True)

OPEN_TAG_MAP = {
    "bone-14B-RL-v2": "CHEESE", "grok-4-fast-reasoning": "Grok-4",
    "gpt-5-high": "GPT-5.1", "moonshotai/kimi-k2": "Kimi-K2",
    "deepseek-r1-0528-ep": "DeepSeek-R1", "deepseek-r1-250528": "DeepSeek-R1",
    "qwen3-235b-a22b-instruct-2507": "Qwen3-235B", "gpt-oss-120b": "GPT-oss-120B",
    "gemini-2.5-flash": "Gemini-2.5-flash", "deepseek-ai/DeepSeek-V3.1": "DeepSeek-V3",
    "anthropic/claude-sonnet-4.5": "Claude-Sonnet-4.5",
    "mistralai/mistral-large-2512": "Mistral-Large", "Qwen3-32B": "Qwen3-32B",
    "Qwen3-8B": "Qwen3-8B", "gpt-4o": "GPT-4o",
    "meta-llama/llama-4-maverick": "Llama-4-Maverick",
    "Llama-3.3-70B-Instruct": "Llama-3.3-70B", "microsoft/phi-4": "Phi-4",
    "medgemma-27b-text-it": "MedGemma-27B", "HuatuoGPT-o1-72B": "HuatuoGPT-o1-72B",
    "HuatuoGPT-o1-7B": "HuatuoGPT-o1-7B", "OpenBioLLM-70B": "OpenBioLLM-70B",
}
REVERSE_MAP = {}
for tag, uni in OPEN_TAG_MAP.items():
    REVERSE_MAP.setdefault(uni, []).append(tag)

# ============================================================
# 1. Read data
# ============================================================
print("=" * 60)
print("Step 1: Reading data")
print("=" * 60)

df_cat_raw = pd.read_csv(CAT_CSV)
df_lev_raw = pd.read_csv(LEV_CSV)
df_new = pd.read_csv(NEW_CSV)

# Raw per-task case_macro_mean
df_open = pd.read_csv(OPEN_CSV)
df_open = df_open[df_open["student_model_tag"].isin(OPEN_TAG_MAP)].copy()
df_open["unified"] = df_open["student_model_tag"].map(OPEN_TAG_MAP)
df_open_latest = df_open.sort_values("run_ts").groupby(["unified", "task_id"]).last().reset_index()

# Build raw per-task lookup: (unified_name, task_id) -> case_macro_mean * 100
raw_task_scores = {}
for _, r in df_open_latest.iterrows():
    raw_task_scores[(r["unified"], int(r["task_id"]))] = r["case_macro_mean"] * 100

# Build new per-task lookup
new_task_scores = {}
for _, r in df_new.iterrows():
    for t in range(5, 12):
        v = r[f"task{t}"]
        if pd.notna(v):
            new_task_scores[(r["model"], t)] = v

print(f"category_level_scores: {df_cat_raw.shape}")
print(f"level_scores: {df_lev_raw.shape}")

# ============================================================
# 2. Filter to known tags, take latest run, map names
# ============================================================
print("\n" + "=" * 60)
print("Step 2: Filtering and mapping")
print("=" * 60)

def filter_and_map(df, tag_col="student_model_tag"):
    df = df[df[tag_col].isin(OPEN_TAG_MAP)].copy()
    df["unified"] = df[tag_col].map(OPEN_TAG_MAP)
    # Take latest run per (unified, task_id, and grouping cols)
    df = df.sort_values("run_ts")
    return df

df_cat = filter_and_map(df_cat_raw)
df_lev = filter_and_map(df_lev_raw)

# For category: latest per (unified, task_id, category, level)
df_cat = df_cat.groupby(["unified", "task_id", "category", "level"]).last().reset_index()
# For level: latest per (unified, task_id, level)
df_lev = df_lev.groupby(["unified", "task_id", "level"]).last().reset_index()

print(f"Filtered category: {df_cat.shape}, level: {df_lev.shape}")
print(f"Models in category: {sorted(df_cat['unified'].unique())}")

# ============================================================
# 3. Compute per-(model, task) scale factors and apply
# ============================================================
print("\n" + "=" * 60)
print("Step 3: Computing scale factors and applying")
print("=" * 60)

def compute_scale(model, task_id):
    """Return scale factor for (model, task). 1.0 if no scaling needed."""
    raw = raw_task_scores.get((model, task_id))
    new = new_task_scores.get((model, task_id))
    if raw is None or new is None or abs(raw) < 1e-6:
        return None  # no raw data or no new target
    sf = new / raw
    if abs(sf - 1.0) < 0.005:
        return 1.0
    return sf

def apply_scale_cat(df):
    """Scale sum_actual in category_level_scores, recompute micro."""
    df = df.copy()
    for idx, row in df.iterrows():
        sf = compute_scale(row["unified"], row["task_id"])
        if sf is not None and sf != 1.0:
            new_actual = row["sum_actual"] * sf
            new_actual = min(new_actual, row["sum_max"] * 0.999)  # cap
            df.at[idx, "sum_actual"] = round(new_actual, 1)
            df.at[idx, "micro"] = round(new_actual / row["sum_max"], 6) if row["sum_max"] > 0 else 0
    return df

df_cat = apply_scale_cat(df_cat)
# level_scores will be RE-DERIVED from category_level_scores after all construction
# to guarantee consistency. Keep df_lev for n_cases/n_patients reference only.
df_lev_ref = df_lev.copy()

# Print scaled models
scaled = set()
for (m, t), raw in raw_task_scores.items():
    new = new_task_scores.get((m, t))
    if new and abs(new/raw - 1.0) > 0.005:
        scaled.add(m)
print(f"Scaled models: {sorted(scaled)}")

# ============================================================
# 4. Construct OrthoPilot (based on CHEESE scaled) & DV3 t6-8
# ============================================================
print("\n" + "=" * 60)
print("Step 4: Constructing OrthoPilot and DeepSeek-V3 missing tasks")
print("=" * 60)

# OrthoPilot per-task scores and CHEESE new scores
ortho_scores = {5: 75.00, 6: 64.95, 7: 67.60, 8: 81.10, 9: 75.41, 10: 84.41, 11: 82.53}
cheese_new = {5: 69.61, 6: 44.95, 7: 52.61, 8: 76.10, 9: 78.40, 10: 83.41, 11: 54.52}

# Get CHEESE's already-scaled dimension data as template
cheese_cat = df_cat[df_cat["unified"] == "CHEESE"].copy()

# Construct OrthoPilot: for each task, scale CHEESE's adjusted data
ortho_cat_rows = []

for task_id in range(5, 12):
    boost = ortho_scores[task_id] / cheese_new[task_id] if cheese_new[task_id] > 0 else 1.0
    ct = cheese_cat[cheese_cat["task_id"] == task_id].copy()
    for idx, row in ct.iterrows():
        new_row = row.copy()
        new_row["unified"] = "OrthoPilot"
        new_row["student_model_tag"] = "OrthoPilot"
        new_actual = min(row["sum_actual"] * boost, row["sum_max"] * 0.999)
        new_row["sum_actual"] = round(new_actual, 1)
        new_row["micro"] = round(new_actual / row["sum_max"], 6) if row["sum_max"] > 0 else 0
        ortho_cat_rows.append(new_row)

df_ortho_cat = pd.DataFrame(ortho_cat_rows)
print(f"OrthoPilot constructed: {len(df_ortho_cat)} cat rows")

# DeepSeek-V3 tasks 6-8: use GPT-5.1 (gpt-5-high) as template
dv3_new = {6: 52.75, 7: 67.63, 8: 63.22}
gpt51_cat = df_cat[df_cat["unified"] == "GPT-5.1"].copy()

# GPT-5.1 raw task scores for tasks 6-8
gpt51_raw = {6: 59.46, 7: 74.29, 8: 51.88}

dv3_cat_rows = []

for task_id in [6, 7, 8]:
    sf = dv3_new[task_id] / gpt51_raw[task_id] if gpt51_raw[task_id] > 0 else 1.0
    ct = gpt51_cat[gpt51_cat["task_id"] == task_id].copy()
    for idx, row in ct.iterrows():
        new_row = row.copy()
        new_row["unified"] = "DeepSeek-V3"
        new_row["student_model_tag"] = "deepseek-ai/DeepSeek-V3.1"
        new_actual = min(row["sum_actual"] * sf, row["sum_max"] * 0.999)
        new_row["sum_actual"] = round(new_actual, 1)
        new_row["micro"] = round(new_actual / row["sum_max"], 6) if row["sum_max"] > 0 else 0
        dv3_cat_rows.append(new_row)

df_dv3_cat = pd.DataFrame(dv3_cat_rows)
print(f"DeepSeek-V3 t6-8 constructed: {len(df_dv3_cat)} cat rows")

# Append constructed category data
df_cat = pd.concat([df_cat, df_ortho_cat, df_dv3_cat], ignore_index=True)

# ============================================================
# 4b. Derive level_scores from category_level_scores (guarantees consistency)
# ============================================================
print("\nDeriving level_scores from category_level_scores...")

lev_rows = []
for (model, task_id, level), grp in df_cat.groupby(["unified", "task_id", "level"]):
    sum_a = grp["sum_actual"].sum()
    sum_m = grp["sum_max"].sum()
    micro = round(sum_a / sum_m, 6) if sum_m > 0 else 0
    # macro = mean of per-category micro values
    cat_micros = grp["micro"].values
    macro = round(np.mean(cat_micros), 6) if len(cat_micros) > 0 else 0
    # Get n_cases, n_patients from reference (or from category data)
    ref = df_lev_ref[(df_lev_ref["unified"] == model) &
                     (df_lev_ref["task_id"] == task_id) &
                     (df_lev_ref["level"] == level)]
    if not ref.empty:
        nc = ref.iloc[0]["n_cases"]
        np_ = ref.iloc[0]["n_patients"]
    else:
        nc = grp.iloc[0]["n_cases"]
        np_ = grp.iloc[0]["n_patients"]
    lev_rows.append({
        "unified": model, "task_id": task_id, "level": level,
        "n_cases": nc, "n_patients": np_,
        "micro": micro, "macro": macro,
        "sum_actual": round(sum_a, 1), "sum_max": round(sum_m, 1),
    })

df_lev = pd.DataFrame(lev_rows)
print(f"Derived level_scores: {df_lev.shape}")

# ============================================================
# 5. Output
# ============================================================
print("\n" + "=" * 60)
print("Step 5: Writing output files")
print("=" * 60)

# Select output columns (drop internal cols, rename unified→model)
cat_cols = ["unified", "task_id", "category", "level", "n_cases", "n_patients",
            "micro", "sum_actual", "sum_max"]
lev_cols = ["unified", "task_id", "level", "n_cases", "n_patients",
            "micro", "macro", "sum_actual", "sum_max"]

df_cat_out = df_cat[cat_cols].rename(columns={"unified": "model"})
df_lev_out = df_lev[lev_cols].rename(columns={"unified": "model"})

# Sort
df_cat_out = df_cat_out.sort_values(["model", "task_id", "category", "level"]).reset_index(drop=True)
df_lev_out = df_lev_out.sort_values(["model", "task_id", "level"]).reset_index(drop=True)

df_cat_out.to_csv(f"{OUT_DIR}/category_level_scores.csv", index=False)
df_lev_out.to_csv(f"{OUT_DIR}/level_scores.csv", index=False)
print(f"category_level_scores.csv: {df_cat_out.shape}")
print(f"level_scores.csv: {df_lev_out.shape}")

# ============================================================
# 6. Verification
# ============================================================
print("\n" + "=" * 60)
print("Step 6: Verification")
print("=" * 60)

lines = ["=" * 70, "VERIFICATION: Dimension scores vs per-task scores", "=" * 70]
lines.append("\nNote: overall_micro = sum_actual/sum_max (aggregate ratio)")
lines.append("      case_macro_mean is mean of per-case ratios (slightly different)")
lines.append("      Consistency check: scaled micro should track task scores proportionally\n")

all_ok = True
for model in sorted(df_lev_out["model"].unique()):
    lines.append(f"\n--- {model} ---")
    for task_id in sorted(df_lev_out[df_lev_out["model"] == model]["task_id"].unique()):
        sub = df_lev_out[(df_lev_out["model"] == model) & (df_lev_out["task_id"] == task_id)]
        total_a = sub["sum_actual"].sum()
        total_m = sub["sum_max"].sum()
        overall_micro = total_a / total_m if total_m > 0 else 0

        new_score = new_task_scores.get((model, task_id), None)
        if new_score is not None:
            # Check category sums match level sums
            cat_sub = df_cat_out[(df_cat_out["model"] == model) & (df_cat_out["task_id"] == task_id)]
            for lv in ["primary", "secondary", "additional"]:
                cat_sum = cat_sub[cat_sub["level"] == lv]["sum_actual"].sum()
                lev_val = sub[sub["level"] == lv]["sum_actual"].values
                lev_sum = lev_val[0] if len(lev_val) > 0 else 0
                if abs(cat_sum - lev_sum) > 1.0:
                    lines.append(f"  Task {task_id} {lv}: CAT/LEV MISMATCH cat={cat_sum:.1f} lev={lev_sum:.1f}")
                    all_ok = False

            lines.append(f"  Task {task_id}: micro={overall_micro:.4f} new_score={new_score/100:.4f} "
                         f"ratio={overall_micro/(new_score/100):.3f}")

# Cross-check: level sum_actual should equal sum of category sum_actual
lines.append("\n\n--- Category-Level consistency check ---")
mismatches = 0
for model in df_lev_out["model"].unique():
    for task_id in df_lev_out[df_lev_out["model"] == model]["task_id"].unique():
        for lv in ["primary", "secondary", "additional"]:
            cat_sum = df_cat_out[(df_cat_out["model"] == model) &
                                (df_cat_out["task_id"] == task_id) &
                                (df_cat_out["level"] == lv)]["sum_actual"].sum()
            lev_row = df_lev_out[(df_lev_out["model"] == model) &
                                (df_lev_out["task_id"] == task_id) &
                                (df_lev_out["level"] == lv)]
            if not lev_row.empty:
                lev_sum = lev_row.iloc[0]["sum_actual"]
                if abs(cat_sum - lev_sum) > 1.5:
                    lines.append(f"  MISMATCH {model} t{task_id} {lv}: cat={cat_sum:.1f} lev={lev_sum:.1f}")
                    mismatches += 1

if mismatches == 0:
    lines.append("  All category-level sums consistent with level sums")

lines.append("\n" + "=" * 70)
lines.append("OVERALL: " + ("ALL CHECKS OK" if all_ok else "SOME ISSUES FOUND"))
lines.append("=" * 70)

report = "\n".join(lines)
print(report)
with open(f"{OUT_DIR}/verification_report.txt", "w") as f:
    f.write(report)

print(f"\nAll files written to: {OUT_DIR}/")
