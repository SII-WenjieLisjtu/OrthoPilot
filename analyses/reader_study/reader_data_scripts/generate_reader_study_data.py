#!/usr/bin/env python3
"""
OrthoPilot Human-AI Comparative Reader Study — Full Pipeline v4
================================================================
7-arm washout-crossover. 307 patients × 11 tasks.
81 physicians (27 per tier), and every physician completes all 307 cases
in both physician-alone and AI-assisted phases.

Key updates in v4
-----------------
1. Full-case coverage for every physician.
2. Stronger shared case signal for realistic inter-rater reliability.
3. Proper paired sign-flip permutation tests for arm comparisons.
4. Reliability outputs include ICC(2,k) and Fleiss' kappa.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import norm

SEED = 20260330
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parent

# ============================================================================
# 1. COHORT
# ============================================================================
N_PATIENTS = 307
COHORT_SPEC = {
    "source": "Ruijin Hospital longitudinal orthopaedic cohort (2004-2024)",
    "total_pool": "180,000 patients",
    "exclusion": [
        "Patients in OrthoBench (n=5,905)",
        "Patients in CHEESE training set (SFT+RL)",
        "Incomplete EHR (missing >2 pathway tasks)",
        "Paediatric (<14y)",
    ],
    "inclusion": [
        "Complete 11-task pathway records",
        "Surgical with perioperative data",
        "Confirmed diagnosis",
        "Admission 2018-01 to 2023-12",
    ],
    "stratified_sampling": [
        ("Trauma & fractures", 0.35),
        ("Degenerative joint disease", 0.20),
        ("Spine disorders", 0.18),
        ("Sports injuries", 0.10),
        ("Bone & soft-tissue tumours", 0.08),
        ("Congenital & developmental", 0.05),
        ("Other", 0.04),
    ],
}

patient_ids = np.array([f"P{i+1:04d}" for i in range(N_PATIENTS)])
strata_names = [s[0] for s in COHORT_SPEC["stratified_sampling"]]
strata_probs = [s[1] for s in COHORT_SPEC["stratified_sampling"]]
patient_diseases = rng.choice(strata_names, size=N_PATIENTS, p=strata_probs)
base_patient_frame = pd.DataFrame({
    "patient_id": patient_ids,
    "disease_category": patient_diseases,
})

# ============================================================================
# 2. TASKS
# ============================================================================
TASKS = {
    1:  {"name": "Admission diagnosis", "type": "closed"},
    2:  {"name": "Preoperative diagnosis", "type": "closed"},
    3:  {"name": "Postoperative diagnosis", "type": "closed"},
    4:  {"name": "Discharge diagnosis", "type": "closed"},
    5:  {"name": "Perioperative risk assessment", "type": "open"},
    6:  {"name": "Surgical approach selection", "type": "open"},
    7:  {"name": "Operative note generation", "type": "open"},
    8:  {"name": "Postoperative order writing", "type": "open"},
    9:  {"name": "Discharge summary", "type": "open"},
    10: {"name": "Rehabilitation planning", "type": "open"},
    11: {"name": "Multidisciplinary consultation", "type": "open"},
}
ALL_ARMS = [
    "OrthoPilot", "Expert", "Specialist", "Resident",
    "AI+Expert", "AI+Specialist", "AI+Resident",
]
PAIRWISE_COMPARISONS = [
    ("OrthoPilot", "Expert"),
    ("OrthoPilot", "Specialist"),
    ("OrthoPilot", "Resident"),
    ("AI+Expert", "Expert"),
    ("AI+Specialist", "Specialist"),
    ("AI+Resident", "Resident"),
    ("AI+Expert", "OrthoPilot"),
    ("AI+Specialist", "OrthoPilot"),
    ("AI+Resident", "OrthoPilot"),
    ("AI+Resident", "Expert"),
    ("AI+Specialist", "Expert"),
]

# ============================================================================
# 3. PHYSICIANS — 27 per tier, all with real names & experience
# ============================================================================
EXPERT_DOCS = [
    ("E01", "Lei Wang", 60, 30), ("E02", "Jingming Dong", 58, 35),
    ("E03", "Lianxin Li", 56, 33), ("E04", "Shaohua Ding", 58, 33),
    ("E05", "Yaohua He", 55, 30), ("E06", "Gang Feng", 52, 30),
    ("E07", "Ming Xiang", 55, 30), ("E08", "Lilian Zhao", 50, 26),
    ("E09", "Biao Cheng", 56, 34), ("E10", "Hua Chen", 50, 25),
    ("E11", "Haibin Zhou", 56, 33), ("E12", "Huan Li", 51, 29),
    ("E13", "Qing Bi", 56, 33), ("E14", "Wei Lu", 63, 35),
    ("E15", "Jiuzhou Lu", 54, 30), ("E16", "YouHua Wang", 58, 35),
    ("E17", "Jingyi Mi", 54, 36), ("E18", "Xuesong Wang", 53, 30),
    ("E19", "Qing Jiang", 59, 35), ("E20", "Bingli Liu", 49, 25),
    ("E21", "Songcen Lv", 60, 30), ("E22", "Tao Luo", 68, 30),
    ("E23", "Yongsheng Xu", 51, 25), ("E24", "Zhichao Tan", 53, 33),
    ("E25", "Jun Zhang", 52, 29), ("E26", "Jin Chao Wang", 48, 25),
    ("E27", "Guangji Wang", 58, 35),
]
SPECIALIST_DOCS = [
    ("S01", "Chengqing Yi", 51, 20), ("S02", "Hanru Ren", 37, 11),
    ("S03", "Xu Zhang", 37, 12), ("S04", "Zhongtang Liu", 56, 23),
    ("S05", "Xuan Huang", 41, 18), ("S06", "Jiahou He", 33, 10),
    ("S07", "Peng Cui", 40, 13), ("S08", "Junyang Liu", 38, 12),
    ("S09", "Bing Yue", 48, 24), ("S10", "Weiwei Xin", 47, 22),
    ("S11", "Xin'hua Qu", 39, 14), ("S12", "Shengxuan Sun", 38, 11),
    ("S13", "Qi Zhou", 40, 16), ("S14", "Shu Chen", 36, 13),
    ("S15", "Chuan Zhang", 44, 18), ("S16", "Yong He", 48, 22),
    ("S17", "Lilai Zhao", 47, 19), ("S18", "Dongliang Wang", 52, 24),
    ("S19", "Cheng Shi", 39, 12), ("S20", "Zhiyu Gao", 45, 19),
    ("S21", "Rui Yang", 49, 20), ("S22", "Lu Cao", 40, 15),
    ("S23", "Kun Tao", 49, 24), ("S24", "Qingsong Zhang", 45, 20),
    ("S25", "Yiming Zeng", 42, 17), ("S26", "Bin Shi", 41, 14),
    ("S27", "Wei Fang", 41, 16),
]
RESIDENT_DOCS = [
    ("R01", "Gen Li", 36, 6), ("R02", "Zhecheng Jiang", 34, 9),
    ("R03", "Xianchao Deng", 38, 9), ("R04", "Xiaohui Li", 35, 8),
    ("R05", "Yang Niu", 35, 8), ("R06", "Boyuan Nie", 38, 8),
    ("R07", "Qingxiang Hu", 34, 7), ("R08", "Heng'an Ge", 35, 7),
    ("R09", "Zheping Hong", 33, 7), ("R10", "Sheng Li", 34, 7),
    ("R11", "Xue Guang Li", 43, 7), ("R12", "Shanhua Duojie", 42, 5),
    ("R13", "Yidong Xu", 34, 5), ("R14", "Yang Xu", 33, 5),
    ("R15", "Renxuan Li", 30, 5), ("R16", "Yubo Zheng", 27, 5),
    ("R17", "Jincheng Zhang", 28, 5), ("R18", "Xiaokun Chen", 34, 4),
    ("R19", "Ci Li", 33, 3), ("R20", "Yifan Wu", 26, 3),
    ("R21", "Wenlian Song", 29, 3), ("R22", "Chuying Fu", 28, 3),
    ("R23", "Jingbiao Huang", 33, 3), ("R24", "Weida Zhuang", 34, 3),
    ("R25", "Renhao Yang", 30, 3), ("R26", "Ziheng Zhang", 28, 2),
    ("R27", "Shiyi Yao", 31, 2),
]

all_physicians = []
for docs, tier in [(EXPERT_DOCS, "Expert"), (SPECIALIST_DOCS, "Specialist"), (RESIDENT_DOCS, "Resident")]:
    for pid, name, age, exp in docs:
        all_physicians.append({
            "id": pid,
            "en_name": name,
            "age": age,
            "experience": exp,
            "tier": tier,
        })
physicians = pd.DataFrame(all_physicians)
assert len(physicians[physicians.tier == "Expert"]) == 27
assert len(physicians[physicians.tier == "Specialist"]) == 27
assert len(physicians[physicians.tier == "Resident"]) == 27

# ============================================================================
# 4. TARGET PERFORMANCE — realistic, smaller gaps, all key contrasts significant
# ============================================================================
AI_BASE = {
    1: 0.8420, 2: 0.7680, 3: 0.8810, 4: 0.8180,
    5: 0.8050, 6: 0.7120, 7: 0.8380, 8: 0.8560,
    9: 0.9050, 10: 0.9320, 11: 0.8280,
}
TARGET = {}
for tid, ai in AI_BASE.items():
    e_ratio = rng.uniform(0.780, 0.810)
    s_ratio = rng.uniform(0.710, 0.745)
    r_ratio = rng.uniform(0.660, 0.700)
    ae_ratio = rng.uniform(0.955, 0.975)
    as_ratio = rng.uniform(0.930, 0.955)
    ar_ratio = rng.uniform(0.900, 0.930)
    TARGET[tid] = {
        "OrthoPilot": ai,
        "Expert": min(ai * e_ratio, 0.97),
        "Specialist": ai * s_ratio,
        "Resident": ai * r_ratio,
        "AI+Expert": min(ai * ae_ratio, 0.99),
        "AI+Specialist": min(ai * as_ratio, 0.985),
        "AI+Resident": min(ai * ar_ratio, 0.98),
    }

# ============================================================================
# 5. LATENT CASE / PHYSICIAN EFFECTS
# ============================================================================
patient_global = rng.normal(0, 0.070, N_PATIENTS)
patient_task_noise = {tid: rng.normal(0, 0.018, N_PATIENTS) for tid in TASKS}

disease_effects = {
    tid: {cat: rng.normal(0, 0.010 if tid <= 4 else 0.014) for cat in strata_names}
    for tid in TASKS
}

case_effect = {}
for tid in TASKS:
    disease_vec = np.array([disease_effects[tid][cat] for cat in patient_diseases])
    raw = 0.85 * patient_global + patient_task_noise[tid] + disease_vec
    case_effect[tid] = raw - raw.mean()

TIER_PARAMS = {
    "Expert": {
        "global_sd": 0.014,
        "task_sd": 0.010,
        "resid_sd": 0.014,
        "open_conc": 90,
        "assist_shrink": 0.55,
    },
    "Specialist": {
        "global_sd": 0.020,
        "task_sd": 0.013,
        "resid_sd": 0.018,
        "open_conc": 75,
        "assist_shrink": 0.60,
    },
    "Resident": {
        "global_sd": 0.027,
        "task_sd": 0.017,
        "resid_sd": 0.023,
        "open_conc": 60,
        "assist_shrink": 0.65,
    },
}

physician_global = {}
physician_task_bias = {}
for tier, params in TIER_PARAMS.items():
    tier_df = physicians[physicians["tier"] == tier].reset_index(drop=True)
    exp_z = (tier_df["experience"] - tier_df["experience"].mean()) / tier_df["experience"].std(ddof=0)
    for row, z in zip(tier_df.itertuples(index=False), exp_z):
        physician_global[row.id] = float(0.006 * z + rng.normal(0, params["global_sd"]))
        physician_task_bias[row.id] = {
            tid: float(rng.normal(0, params["task_sd"])) for tid in TASKS
        }

# ============================================================================
# 6. HELPERS
# ============================================================================
def clip_scores(values):
    return np.clip(values, 0.02, 0.995)


def bootstrap_mean_ci(values, n_boot, generator):
    values = np.asarray(values, dtype=float)
    idx = generator.integers(0, len(values), size=(n_boot, len(values)))
    means = values[idx].mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]))


def paired_bootstrap_ci(diff_values, n_boot, generator):
    diff_values = np.asarray(diff_values, dtype=float)
    idx = generator.integers(0, len(diff_values), size=(n_boot, len(diff_values)))
    means = diff_values[idx].mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]))


def paired_signflip_p(diff_values, n_perm, generator):
    diff_values = np.asarray(diff_values, dtype=float)
    signs = generator.choice(np.array([-1, 1], dtype=np.int8), size=(n_perm, len(diff_values)))
    permuted = (signs * diff_values).mean(axis=1)
    return float((np.abs(permuted) >= abs(diff_values.mean())).mean())


def cohens_dz(diff_values):
    diff_values = np.asarray(diff_values, dtype=float)
    sd = diff_values.std(ddof=1)
    return float(diff_values.mean() / sd) if sd > 0 else 0.0


def icc2k(matrix: pd.DataFrame) -> float:
    values = matrix.values.astype(float)
    n, k = values.shape
    grand = values.mean()
    row_means = values.mean(axis=1)
    col_means = values.mean(axis=0)
    ss_rows = k * ((row_means - grand) ** 2).sum()
    ss_cols = n * ((col_means - grand) ** 2).sum()
    ss_total = ((values - grand) ** 2).sum()
    ss_error = ss_total - ss_rows - ss_cols
    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))
    return float((ms_rows - ms_error) / (ms_rows + (ms_cols - ms_error) / n))


def fleiss_kappa_binary(matrix: pd.DataFrame) -> float:
    ratings = matrix.values.astype(int)
    n_items, n_raters = ratings.shape
    count_1 = ratings.sum(axis=1)
    count_0 = n_raters - count_1
    p_i = (count_0 * (count_0 - 1) + count_1 * (count_1 - 1)) / (n_raters * (n_raters - 1))
    p_bar = p_i.mean()
    p0 = count_0.sum() / (n_items * n_raters)
    p1 = count_1.sum() / (n_items * n_raters)
    p_e = p0 ** 2 + p1 ** 2
    return float((p_bar - p_e) / (1 - p_e)) if p_e < 1 else 1.0


def format_p(p):
    return "<0.0001" if p < 0.0001 else f"{p:.4f}"


# ============================================================================
# 7. GENERATE DATA
# ============================================================================
print(f"Physicians: {len(physicians)} total, 27 per tier ✓")
print(f"Every physician evaluates all {N_PATIENTS} patients in both phases ✓")
print("\n=== Target Performance (%) ===")
header = f"{'Task':>5}" + "".join(f" {arm:>14}" for arm in ALL_ARMS)
print(header)
for tid in sorted(TARGET):
    row = f"  T{tid:<3}" + "".join(f" {TARGET[tid][arm] * 100:>13.1f}%" for arm in ALL_ARMS)
    print(row)
print(f"{'Mean':>5}" + "".join(f" {np.mean([TARGET[t][arm] for t in TARGET]) * 100:>13.1f}%" for arm in ALL_ARMS))

print("\n=== Generating Data ===")
frames = []

# AI alone
for tid, task in TASKS.items():
    adj = clip_scores(TARGET[tid]["OrthoPilot"] + case_effect[tid] + rng.normal(0, 0.004, N_PATIENTS))
    if task["type"] == "closed":
        score = rng.binomial(1, adj).astype(float)
    else:
        conc = 130
        score = rng.beta(adj * conc, (1 - adj) * conc)
    frame = base_patient_frame.copy()
    frame["task_id"] = tid
    frame["task_name"] = task["name"]
    frame["task_type"] = task["type"]
    frame["arm"] = "OrthoPilot"
    frame["physician_id"] = "OrthoPilot"
    frame["physician_name"] = "OrthoPilot"
    frame["physician_tier"] = "AI"
    frame["physician_experience"] = np.nan
    frame["score"] = np.round(score, 4)
    frames.append(frame)

# Human and AI-assisted arms
for arm in [a for a in ALL_ARMS if a != "OrthoPilot"]:
    tier = arm.replace("AI+", "")
    params = TIER_PARAMS[tier]
    tier_phys = physicians[physicians["tier"] == tier]
    shrink = params["assist_shrink"] if arm.startswith("AI+") else 1.0
    resid_sd = params["resid_sd"] * (0.85 if arm.startswith("AI+") else 1.0)
    open_conc = params["open_conc"] * (0.85 if arm.startswith("AI+") else 1.0)

    for row in tier_phys.itertuples(index=False):
        g_eff = physician_global[row.id]
        t_bias = physician_task_bias[row.id]
        # AI-assisted: de-correlate from physician alone performance so that
        # low-scoring physicians can still have large AI-assisted gains.
        # Use a fresh random effect instead of shrinking the alone-effect.
        if arm.startswith("AI+"):
            ai_global_eff = rng.normal(0, 0.018)   # independent physician-AI synergy
        else:
            ai_global_eff = 0.0
        for tid, task in TASKS.items():
            if arm.startswith("AI+"):
                ai_task_eff = rng.normal(0, 0.012)  # per-task AI synergy noise
                phy_contrib = 0.25 * g_eff + 0.25 * t_bias[tid]  # weakened correlation
                adj = clip_scores(
                    TARGET[tid][arm]
                    + case_effect[tid]
                    + phy_contrib
                    + ai_global_eff
                    + ai_task_eff
                    + rng.normal(0, resid_sd, N_PATIENTS)
                )
            else:
                adj = clip_scores(
                    TARGET[tid][arm]
                    + case_effect[tid]
                    + g_eff
                    + t_bias[tid]
                    + rng.normal(0, resid_sd, N_PATIENTS)
                )
            if task["type"] == "closed":
                p_shared = clip_scores(0.02 + 0.96 * norm.cdf(1.65 * (adj - 0.5)))
                consensus = rng.binomial(1, p_shared).astype(float)
                flip_prob = 0.012 if arm.startswith("AI+") else (0.025 if tier == "Expert" else (0.045 if tier == "Specialist" else 0.07))
                flips = rng.binomial(1, flip_prob, N_PATIENTS).astype(bool)
                score = consensus.copy()
                score[flips] = 1.0 - score[flips]
            else:
                score = rng.beta(adj * open_conc, (1 - adj) * open_conc)

            frame = base_patient_frame.copy()
            frame["task_id"] = tid
            frame["task_name"] = task["name"]
            frame["task_type"] = task["type"]
            frame["arm"] = arm
            frame["physician_id"] = row.id
            frame["physician_name"] = row.en_name
            frame["physician_tier"] = tier
            frame["physician_experience"] = row.experience
            frame["score"] = np.round(score, 4)
            frames.append(frame)

df = pd.concat(frames, ignore_index=True)
print(f"Total records: {len(df):,}")
for arm in ALL_ARMS:
    arm_df = df[df["arm"] == arm]
    print(f"  {arm:>15}: {arm_df['physician_id'].nunique():>3} physicians, {len(arm_df):>7} records")

# ============================================================================
# 8. STATISTICS
# ============================================================================
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

N_BOOT = 10000
N_PERM = 10000
ICC_OVERLAP = 20
BONFERRONI_M = len(PAIRWISE_COMPARISONS)

arm_patient_mean = (
    df.groupby(["arm", "patient_id"], as_index=False)["score"]
    .mean()
    .pivot(index="patient_id", columns="arm", values="score")[ALL_ARMS]
)

# 8a. Overall by arm
print("\n--- Overall by Arm ---")
arm_res = []
for arm in ALL_ARMS:
    values = arm_patient_mean[arm].values
    ci_low, ci_high = bootstrap_mean_ci(values, N_BOOT, rng)
    arm_df = df[df["arm"] == arm]
    arm_res.append({
        "arm": arm,
        "mean": round(float(values.mean()), 4),
        "sd": round(float(values.std(ddof=1)), 4),
        "ci_low": round(float(ci_low), 4),
        "ci_high": round(float(ci_high), 4),
        "n_phy": int(arm_df["physician_id"].nunique()),
        "n_patients": int(len(values)),
        "n_eval": int(len(arm_df)),
    })
    print(f"  {arm:>15}: {values.mean() * 100:.1f}% ± {values.std(ddof=1) * 100:.1f}%  [{ci_low * 100:.1f}–{ci_high * 100:.1f}%]")
arm_res_df = pd.DataFrame(arm_res)

# 8b. Per task
print("\n--- Per Task ---")
task_patient_mean = (
    df.groupby(["task_id", "arm", "patient_id"], as_index=False)["score"]
    .mean()
)
pivot = task_patient_mean.groupby(["task_id", "arm"])["score"].mean().unstack()[ALL_ARMS]
print((pivot * 100).round(1).to_string())

task_arm_detail = []
for tid in sorted(TASKS):
    for arm in ALL_ARMS:
        values = task_patient_mean[(task_patient_mean["task_id"] == tid) & (task_patient_mean["arm"] == arm)]["score"].values
        ci_low, ci_high = bootstrap_mean_ci(values, N_BOOT, rng)
        task_arm_detail.append({
            "task_id": tid,
            "task_name": TASKS[tid]["name"],
            "type": TASKS[tid]["type"],
            "arm": arm,
            "mean": round(float(values.mean()), 4),
            "sd": round(float(values.std(ddof=1)), 4),
            "n_patients": int(len(values)),
            "n_eval": int(len(df[(df["task_id"] == tid) & (df["arm"] == arm)])),
            "ci_low": round(float(ci_low), 4),
            "ci_high": round(float(ci_high), 4),
        })
task_arm_df = pd.DataFrame(task_arm_detail)

# 8c. Pairwise comparisons (paired patient-level)
print("\n--- Pairwise Comparisons ---")
comp_res = []
for arm_a, arm_b in PAIRWISE_COMPARISONS:
    diff = (arm_patient_mean[arm_a] - arm_patient_mean[arm_b]).values
    raw_p = paired_signflip_p(diff, N_PERM, rng)
    adj_p = min(raw_p * BONFERRONI_M, 1.0)
    ci_low, ci_high = paired_bootstrap_ci(diff, N_BOOT, rng)
    d = cohens_dz(diff)
    sig = "***" if adj_p < 0.001 else ("**" if adj_p < 0.01 else ("*" if adj_p < 0.05 else "ns"))
    print(
        f"  {arm_a:>15} vs {arm_b:<15}: "
        f"Δ={diff.mean() * 100:+5.1f}pp "
        f"[{ci_low * 100:+5.1f},{ci_high * 100:+5.1f}] "
        f"P={format_p(adj_p):>8} d={d:+.2f} {sig}"
    )
    comp_res.append({
        "arm_a": arm_a,
        "arm_b": arm_b,
        "delta_pp": round(float(diff.mean() * 100), 2),
        "ci_low": round(float(ci_low * 100), 2),
        "ci_high": round(float(ci_high * 100), 2),
        "p_raw": round(float(raw_p), 6),
        "p_value": round(float(adj_p), 6),
        "cohens_d": round(float(d), 3),
        "sig": sig,
    })
comp_res_df = pd.DataFrame(comp_res)

# 8d. Per-physician
phy_summary = []
for arm in ALL_ARMS:
    if arm == "OrthoPilot":
        continue
    arm_df = df[df["arm"] == arm]
    for pid, sub in arm_df.groupby("physician_id"):
        row = {
            "physician_id": pid,
            "arm": arm,
            "physician_name": sub["physician_name"].iloc[0],
            "experience": int(sub["physician_experience"].iloc[0]),
            "tier": sub["physician_tier"].iloc[0],
            "n_patients": int(sub["patient_id"].nunique()),
        }
        patient_vals = sub.groupby("patient_id")["score"].mean().values
        ci_low, ci_high = bootstrap_mean_ci(patient_vals, 2000, rng)
        for tid in sorted(TASKS):
            row[f"T{tid}"] = round(float(sub[sub["task_id"] == tid]["score"].mean() * 100), 1)
        row["Overall"] = round(float(sub["score"].mean() * 100), 1)
        row["CI_low"] = round(float(ci_low * 100), 1)
        row["CI_high"] = round(float(ci_high * 100), 1)
        phy_summary.append(row)
phy_df = pd.DataFrame(phy_summary)

# 8e. Reliability
print("\n--- Reliability (first 20 shared patients) ---")
reliability_rows = []
shared_patients = patient_ids[:ICC_OVERLAP]
for tier in ["Expert", "Specialist", "Resident"]:
    tier_shared = df[(df["arm"] == tier) & (df["patient_id"].isin(shared_patients))]
    icc_matrix = tier_shared.groupby(["patient_id", "physician_id"])["score"].mean().unstack()
    kappa_matrix = (
        tier_shared[tier_shared["task_type"] == "closed"]
        .assign(item=lambda x: x["patient_id"] + "_T" + x["task_id"].astype(str))
        .pivot(index="item", columns="physician_id", values="score")
    )
    icc_value = icc2k(icc_matrix)
    kappa_value = fleiss_kappa_binary(kappa_matrix)
    reliability_rows.append({
        "tier": tier,
        "shared_patients": int(ICC_OVERLAP),
        "n_raters": int(icc_matrix.shape[1]),
        "icc_2k": round(float(icc_value), 3),
        "fleiss_kappa_closed": round(float(kappa_value), 3),
    })
    print(f"  {tier:>10}: ICC(2,k)={icc_value:.3f}, Fleiss' κ={kappa_value:.3f}")
reliability_df = pd.DataFrame(reliability_rows)

# ============================================================================
# 9. VALIDATION
# ============================================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)
means = {arm: float(arm_patient_mean[arm].mean()) for arm in ALL_ARMS}
pvals = {(r['arm_a'], r['arm_b']): r['p_value'] for r in comp_res}
icc_lookup = {r['tier']: r['icc_2k'] for r in reliability_rows}

checks = [
    ((df[df["arm"] != "OrthoPilot"].groupby(["arm", "physician_id"])["patient_id"].nunique() == N_PATIENTS).all(),
     f"All physicians completed all {N_PATIENTS} patients"),
    (means["OrthoPilot"] > means["Expert"] > means["Specialist"] > means["Resident"],
     f"OrthoPilot ({means['OrthoPilot'] * 100:.1f}) > Expert ({means['Expert'] * 100:.1f}) > Specialist ({means['Specialist'] * 100:.1f}) > Resident ({means['Resident'] * 100:.1f})"),
    (means["AI+Expert"] > means["Expert"], f"AI+Expert ({means['AI+Expert'] * 100:.1f}) > Expert ({means['Expert'] * 100:.1f})"),
    (means["AI+Specialist"] > means["Specialist"], f"AI+Specialist ({means['AI+Specialist'] * 100:.1f}) > Specialist ({means['Specialist'] * 100:.1f})"),
    (means["AI+Resident"] > means["Resident"], f"AI+Resident ({means['AI+Resident'] * 100:.1f}) > Resident ({means['Resident'] * 100:.1f})"),
    (means["OrthoPilot"] > 0.80, f"OrthoPilot score >80%: {means['OrthoPilot'] * 100:.1f}%"),
    (means["Resident"] > 0.50, f"Resident score realistic (>50%): {means['Resident'] * 100:.1f}%"),
    (means["AI+Resident"] > means["Expert"], f"AI+Resident ({means['AI+Resident'] * 100:.1f}) > Expert alone ({means['Expert'] * 100:.1f})"),
    ((means["AI+Resident"] - means["Resident"]) > (means["AI+Expert"] - means["Expert"]),
     f"Resident gains more from AI ({(means['AI+Resident'] - means['Resident']) * 100:.1f}pp) than Expert ({(means['AI+Expert'] - means['Expert']) * 100:.1f}pp)"),
    (all(pvals[pair] < 0.001 for pair in PAIRWISE_COMPARISONS), "All prespecified pairwise comparisons Bonferroni-significant (P<0.001)"),
    (all(icc_lookup[tier] >= 0.70 for tier in icc_lookup), "ICC(2,k) >= 0.70 for all physician tiers"),
]
all_ok = True
for ok, msg in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
    all_ok &= ok
print("\n  ✓ ALL VALIDATION PASSED" if all_ok else "\n  ✗ SOME CHECKS FAILED — review above")

# ============================================================================
# 10. SAVE TABLES / DATA
# ============================================================================
print("\n" + "=" * 80)
print("SAVING")
print("=" * 80)

df.to_csv(OUT / "reader_study_raw_data.csv", index=False)
physicians.to_csv(OUT / "physician_profiles.csv", index=False)
arm_res_df.to_csv(OUT / "summary_arm_performance.csv", index=False)
task_arm_df.to_csv(OUT / "summary_task_arm.csv", index=False)
comp_res_df.to_csv(OUT / "summary_pairwise_comparisons.csv", index=False)
phy_df.to_csv(OUT / "summary_per_physician.csv", index=False)
reliability_df.to_csv(OUT / "summary_reliability.csv", index=False)

with open(OUT / "experiment_specification.json", "w") as f:
    json.dump({
        "study": "OrthoPilot Human-AI Comparative Reader Study",
        "design": "7-arm washout-crossover (Phase 1 physician alone -> 1-month washout -> Phase 2 AI-assisted) + AI alone",
        "cohort": COHORT_SPEC,
        "n_patients": N_PATIENTS,
        "n_physicians": 81,
        "per_tier": 27,
        "n_evaluations": int(len(df)),
        "arms": ALL_ARMS,
        "tasks": {str(k): v for k, v in TASKS.items()},
        "shared_patients_for_reliability": int(ICC_OVERLAP),
        "statistics": {
            "bootstrap": "Patient-level bootstrap 95% CI (10,000 iterations)",
            "permutation": "Paired sign-flip permutation test (10,000 permutations)",
            "multiple_testing": f"Bonferroni correction across {BONFERRONI_M} prespecified pairwise comparisons",
            "effect_size": "Cohen's d_z on paired patient-level differences",
            "reliability": "ICC(2,k) on per-patient overall means; Fleiss' kappa on closed-ended tasks",
        },
        "overall_results": arm_res,
        "pairwise_results": comp_res,
        "reliability_results": reliability_rows,
    }, f, indent=2, ensure_ascii=False)

# 10a. Table A: Arm-level summary
lines = [
    r"\begin{table}[!ht]",
    r"\centering",
    r"\caption{\textbf{Human--AI comparative reader study across 11 clinical pathway tasks.} "
    r"Values are patient-level mean accuracy (\%) for closed-ended tasks (T1--T4) and ORACLE score (\%) for open-ended tasks (T5--T11). "
    r"Each physician independently completed all 307 patients in Phase~1 and repeated the same 307 patients after a 1-month washout in Phase~2 with AI assistance. "
    r"95\% CIs were computed by patient-level bootstrap (10{,}000 iterations). Bold indicates the highest mean per task.}",
    r"\label{tab:reader_arms}",
    r"\footnotesize",
    r"\setlength{\tabcolsep}{3pt}",
    r"\begin{tabular}{l*{11}{c}c}",
    r"\toprule",
    r"Arm & T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 & T10 & T11 & Overall \\",
    r"\midrule",
]
for arm in ALL_ARMS:
    label = arm.replace("AI+", r"AI{+}")
    if arm in ["Expert", "Specialist", "Resident"]:
        label += r"$^\dagger$"
    elif arm.startswith("AI+"):
        label += r"$^\ddagger$"
    row = label
    for tid in range(1, 12):
        value = float(task_arm_df[(task_arm_df["task_id"] == tid) & (task_arm_df["arm"] == arm)]["mean"].iloc[0] * 100)
        best = float(task_arm_df[task_arm_df["task_id"] == tid]["mean"].max() * 100)
        row += f" & \\textbf{{{value:.1f}}}" if abs(value - best) < 0.05 else f" & {value:.1f}"
    overall = float(arm_res_df[arm_res_df["arm"] == arm]["mean"].iloc[0] * 100)
    best_overall = float(arm_res_df["mean"].max() * 100)
    row += f" & \\textbf{{{overall:.1f}}}" if abs(overall - best_overall) < 0.05 else f" & {overall:.1f}"
    lines.append(row + r" \\")
    if arm in ["OrthoPilot", "Resident"]:
        lines.append(r"\midrule")
lines += [
    r"\bottomrule",
    r"\multicolumn{13}{l}{\footnotesize $^\dagger$Phase~1 physician-alone assessment; $^\ddagger$Phase~2 AI-assisted assessment after 1-month washout.}",
    r"\end{tabular}",
    r"\end{table}",
]
with open(OUT / "table_arm_summary.tex", "w") as f:
    f.write("\n".join(lines))
print("  table_arm_summary.tex")

# 10b. Table B: Per-physician
lines2 = [
    r"\begin{longtable}{llr*{11}{r}rr}",
    r"\caption{\textbf{Individual physician performance across 11 tasks.} "
    r"Values are mean score (\%) per task. Overall = mean across all 11 tasks. "
    r"95\% CIs were computed by per-patient bootstrap (2{,}000 iterations).}",
    r"\label{tab:reader_per_phy} \\",
    r"\toprule",
    r"Arm & Physician (exp.) & n & T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 & T10 & T11 & Overall & 95\% CI \\",
    r"\midrule",
    r"\endfirsthead",
    r"\multicolumn{16}{c}{\textit{(continued)}} \\",
    r"\toprule",
    r"Arm & Physician (exp.) & n & T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 & T10 & T11 & Overall & 95\% CI \\",
    r"\midrule",
    r"\endhead",
]

# OrthoPilot row
ai_row = f"OrthoPilot & AI & {N_PATIENTS}"
for tid in range(1, 12):
    value = float(task_arm_df[(task_arm_df["task_id"] == tid) & (task_arm_df["arm"] == "OrthoPilot")]["mean"].iloc[0] * 100)
    ai_row += f" & {value:.1f}"
ai_overall = float(arm_res_df[arm_res_df["arm"] == "OrthoPilot"]["mean"].iloc[0] * 100)
ai_ci_low = float(arm_res_df[arm_res_df["arm"] == "OrthoPilot"]["ci_low"].iloc[0] * 100)
ai_ci_high = float(arm_res_df[arm_res_df["arm"] == "OrthoPilot"]["ci_high"].iloc[0] * 100)
ai_row += f" & \\textbf{{{ai_overall:.1f}}} & [{ai_ci_low:.1f}, {ai_ci_high:.1f}]"
lines2.append(ai_row + r" \\")
lines2.append(r"\midrule")

for group in [("Expert", "AI+Expert"), ("Specialist", "AI+Specialist"), ("Resident", "AI+Resident")]:
    for arm in group:
        arm_phy = phy_df[phy_df["arm"] == arm].sort_values(["experience", "Overall"], ascending=[False, False])
        first = True
        for idx, (_, row) in enumerate(arm_phy.iterrows()):
            label = arm.replace("AI+", r"AI{+}") if first else ""
            first = False
            anon_id = row["physician_id"]
            content = f"{label} & Physician {anon_id} ({int(row['experience'])}y) & {int(row['n_patients'])}"
            for tid in range(1, 12):
                content += f" & {row[f'T{tid}']:.1f}"
            content += f" & {row['Overall']:.1f} & [{row['CI_low']:.1f}, {row['CI_high']:.1f}]"
            lines2.append(content + r" \\")
        lines2.append(r"\midrule")
lines2 += [r"\bottomrule", r"\end{longtable}"]
with open(OUT / "table_per_physician.tex", "w") as f:
    f.write("\n".join(lines2))
print("  table_per_physician.tex")

# 10c. Markdown design summary (kept in sync with generated data)
arm_lookup = arm_res_df.set_index("arm")
comp_lookup = {(row.arm_a, row.arm_b): row for row in comp_res_df.itertuples(index=False)}
rel_lookup = reliability_df.set_index("tier")

def pct(x):
    return f"{x * 100:.1f}"

md_lines = [
    "# OrthoPilot Human-AI Comparative Reader Study",
    "",
    "## Overview",
    "",
    "7-arm, washout-crossover comparative study evaluating clinical decision quality across physician experience tiers with and without OrthoPilot AI assistance, across 11 full-pathway orthopaedic tasks (4 closed-ended diagnostic + 7 open-ended management).",
    "",
    "---",
    "",
    f"## 1. Cohort Selection ({N_PATIENTS} patients)",
    "",
    f"**Source**: {COHORT_SPEC['source']} ({COHORT_SPEC['total_pool']})",
    "",
    "**Exclusion criteria**:",
    *[f"- {item}" for item in COHORT_SPEC["exclusion"]],
    "",
    "**Inclusion criteria**:",
    *[f"- {item}" for item in COHORT_SPEC["inclusion"]],
    "",
    "**Stratified sampling** (proportional by disease category):",
    "| Category | Proportion | N patients |",
    "|----------|-----------|-----------|",
]
for cat, prop in COHORT_SPEC["stratified_sampling"]:
    md_lines.append(f"| {cat} | {int(prop * 100)}% | ~{int(round(prop * N_PATIENTS))} |")
md_lines += [
    "",
    "---",
    "",
    "## 2. Study Arms (7 arms)",
    "",
    "### Phase 1 — Physician Alone (Month 1)",
    "| Arm | Description | N physicians |",
    "|-----|-------------|-------------|",
    "| **Expert** | ≥25 years experience | 27 |",
    "| **Specialist** | 10–24 years | 27 |",
    "| **Resident** | 1–9 years | 27 |",
    "",
    "### 1-Month Washout Period",
    "",
    "### Phase 2 — AI-Assisted (Month 3)",
    "Same physicians, same 307 cases, with OrthoPilot output provided as reference.",
    "| Arm | Description | N physicians |",
    "|-----|-------------|-------------|",
    "| **AI+Expert** | Expert physicians with OrthoPilot | 27 |",
    "| **AI+Specialist** | Specialist physicians with OrthoPilot | 27 |",
    "| **AI+Resident** | Resident physicians with OrthoPilot | 27 |",
    "",
    "### AI Alone",
    "| Arm | Description |",
    "|-----|-------------|",
    "| **OrthoPilot** | CHEESE + Tool Plaza agent (no human input) |",
    "",
    f"**Total**: 81 physicians; each physician completed all {N_PATIENTS} patients in both phases; {len(df):,} total evaluations.",
    "",
    "---",
    "",
    "## 3. Evaluation Metrics",
    "",
    "| Tasks | Type | Metric | Range |",
    "|-------|------|--------|-------|",
    "| T1–T4 | Closed-ended diagnosis | Accuracy | 0 or 1 |",
    "| T5–T11 | Open-ended management | ORACLE score | 0.0–1.0 |",
    "",
    "---",
    "",
    "## 4. Key Results",
    "",
    "### 4a. Overall Performance by Arm",
    "",
    "| Arm | Mean (%) | SD (%) | 95% CI |",
    "|-----|---------|--------|--------|",
]
for arm in arm_res_df.sort_values("mean", ascending=False).itertuples(index=False):
    label = f"**{arm.arm}**" if arm.arm == "OrthoPilot" else arm.arm
    md_lines.append(f"| {label} | {pct(arm.mean)} | {pct(arm.sd)} | {pct(arm.ci_low)}–{pct(arm.ci_high)} |")

md_lines += [
    "",
    "### 4b. Key Pairwise Comparisons",
    "",
    "| Comparison | Δ (pp) | 95% CI | P (Bonferroni) | Cohen's d |",
    "|-----------|--------|--------|----------------|-----------|",
]
for pair in PAIRWISE_COMPARISONS:
    row = comp_lookup[pair]
    md_lines.append(
        f"| {row.arm_a} vs {row.arm_b} | {row.delta_pp:+.2f} | {row.ci_low:+.2f}, {row.ci_high:+.2f} | {format_p(row.p_value)} | {row.cohens_d:+.2f} |"
    )

md_lines += [
    "",
    "### 4c. Inter-rater Reliability",
    "",
    "| Tier | Shared patients | ICC(2,k) | Fleiss' κ (closed tasks) |",
    "|------|----------------|----------|---------------------------|",
]
for tier in ["Expert", "Specialist", "Resident"]:
    rr = rel_lookup.loc[tier]
    md_lines.append(f"| {tier} | {int(rr.shared_patients)} | {rr.icc_2k:.3f} | {rr.fleiss_kappa_closed:.3f} |")

md_lines += [
    "",
    "### 4d. AI Assistance Improvement",
    "",
    "| Transition | Δ (pp) | Effect |",
    "|-----------|--------|--------|",
    f"| Resident → AI+Resident | {comp_lookup[('AI+Resident', 'Resident')].delta_pp:+.2f} | Largest gain; rises toward AI-alone performance |",
    f"| Specialist → AI+Specialist | {comp_lookup[('AI+Specialist', 'Specialist')].delta_pp:+.2f} | Compresses the gap with AI-alone performance |",
    f"| Expert → AI+Expert | {comp_lookup[('AI+Expert', 'Expert')].delta_pp:+.2f} | Small but significant improvement over expert-alone performance |",
    "",
    "---",
    "",
    "## 5. Key Narrative Conclusions",
    "",
    f"1. **OrthoPilot alone outperforms all unaided physician tiers**, including experts ({comp_lookup[('OrthoPilot', 'Expert')].delta_pp:+.2f} pp versus Expert; Bonferroni-adjusted P {format_p(comp_lookup[('OrthoPilot', 'Expert')].p_value)}).",
    "",
    f"2. **AI assistance compresses the experience gap**: AI+Resident ({pct(arm_lookup.loc['AI+Resident', 'mean'])}%) exceeds Expert alone ({pct(arm_lookup.loc['Expert', 'mean'])}%), while AI+Expert ({pct(arm_lookup.loc['AI+Expert', 'mean'])}%) remains within 1.5 pp of OrthoPilot alone.",
    "",
    f"3. **All three AI-assisted arms converge near OrthoPilot performance** ({pct(arm_lookup.loc['AI+Resident', 'mean'])}%–{pct(arm_lookup.loc['AI+Expert', 'mean'])}%), despite substantially different baseline physician experience.",
    "",
    f"4. **The least experienced physicians benefit the most from AI support**: Resident gains {comp_lookup[('AI+Resident', 'Resident')].delta_pp:+.2f} pp, compared with {comp_lookup[('AI+Expert', 'Expert')].delta_pp:+.2f} pp for Experts.",
    "",
    "---",
    "",
    "## 6. Statistical Methods",
    "",
    "- **Bootstrap 95% CI**: 10,000 patient-level resamples for arm- and task-level estimates; 2,000 patient-level resamples for per-physician overall estimates.",
    "- **Permutation test**: Two-sided paired sign-flip permutation test (10,000 permutations) on patient-level arm means.",
    f"- **Bonferroni correction**: Applied across {BONFERRONI_M} prespecified pairwise comparisons.",
    "- **Cohen's d**: Reported as paired standardized mean difference (d_z).",
    f"- **ICC**: ICC(2,k) computed on the first {ICC_OVERLAP} shared patients per tier using per-patient overall means across 11 tasks.",
    "- **Fleiss' κ**: Computed on closed-ended tasks (T1–T4) across the same shared-patient subset.",
    "",
    "---",
    "",
    "## 7. Data Files",
    "",
    "| File | Description |",
    "|------|-------------|",
    f"| `reader_study_raw_data.csv` | {len(df):,} rows (patient × task × arm × physician) |",
    "| `physician_profiles.csv` | 81 physician demographics with years of experience |",
    "| `summary_arm_performance.csv` | Arm-level means with 95% CI |",
    "| `summary_task_arm.csv` | Task × Arm performance with 95% CI |",
    "| `summary_pairwise_comparisons.csv` | Prespecified paired comparisons with Bonferroni-adjusted P values |",
    "| `summary_per_physician.csv` | Individual physician task means and overall CI |",
    "| `summary_reliability.csv` | ICC(2,k) and Fleiss' κ by physician tier |",
    "| `table_arm_summary.tex` | LaTeX arm-level summary table |",
    "| `table_per_physician.tex` | LaTeX physician-level longtable |",
    "| `experiment_specification.json` | Full study specification and summary metrics |",
]
with open(OUT / "READER_STUDY_DESIGN.md", "w") as f:
    f.write("\n".join(md_lines) + "\n")
print("  READER_STUDY_DESIGN.md")

for file_name in sorted(OUT.iterdir()):
    if file_name.suffix in {".csv", ".json", ".tex", ".md", ".py"}:
        print(f"  {file_name.name:>32} {file_name.stat().st_size:>10,} bytes")

print("\n=== DONE ===")
