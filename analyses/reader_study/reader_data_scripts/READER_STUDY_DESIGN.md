# OrthoPilot Human-AI Comparative Reader Study

## Overview

7-arm, washout-crossover comparative study evaluating clinical decision quality across physician experience tiers with and without OrthoPilot AI assistance, across 11 full-pathway orthopaedic tasks (4 closed-ended diagnostic + 7 open-ended management).

---

## 1. Cohort Selection (307 patients)

**Source**: Ruijin Hospital longitudinal orthopaedic cohort (2004-2024) (180,000 patients)

**Exclusion criteria**:
- Patients in OrthoBench (n=5,905)
- Patients in CHEESE training set (SFT+RL)
- Incomplete EHR (missing >2 pathway tasks)
- Paediatric (<14y)

**Inclusion criteria**:
- Complete 11-task pathway records
- Surgical with perioperative data
- Confirmed diagnosis
- Admission 2018-01 to 2023-12

**Stratified sampling** (proportional by disease category):
| Category | Proportion | N patients |
|----------|-----------|-----------|
| Trauma & fractures | 35% | ~107 |
| Degenerative joint disease | 20% | ~61 |
| Spine disorders | 18% | ~55 |
| Sports injuries | 10% | ~31 |
| Bone & soft-tissue tumours | 8% | ~25 |
| Congenital & developmental | 5% | ~15 |
| Other | 4% | ~12 |

---

## 2. Study Arms (7 arms)

### Phase 1 — Physician Alone (Month 1)
| Arm | Description | N physicians |
|-----|-------------|-------------|
| **Expert** | ≥25 years experience | 27 |
| **Specialist** | 10–24 years | 27 |
| **Resident** | 1–9 years | 27 |

### 1-Month Washout Period

### Phase 2 — AI-Assisted (Month 3)
Same physicians, same 307 cases, with OrthoPilot output provided as reference.
| Arm | Description | N physicians |
|-----|-------------|-------------|
| **AI+Expert** | Expert physicians with OrthoPilot | 27 |
| **AI+Specialist** | Specialist physicians with OrthoPilot | 27 |
| **AI+Resident** | Resident physicians with OrthoPilot | 27 |

### AI Alone
| Arm | Description |
|-----|-------------|
| **OrthoPilot** | CHEESE + Tool Plaza agent (no human input) |

**Total**: 81 physicians; each physician completed all 307 patients in both phases; 550,451 total evaluations.

---

## 3. Evaluation Metrics

| Tasks | Type | Metric | Range |
|-------|------|--------|-------|
| T1–T4 | Closed-ended diagnosis | Accuracy | 0 or 1 |
| T5–T11 | Open-ended management | ORACLE score | 0.0–1.0 |

---

## 4. Key Results

### 4a. Overall Performance by Arm

| Arm | Mean (%) | SD (%) | 95% CI |
|-----|---------|--------|--------|
| **OrthoPilot** | 83.0 | 8.9 | 82.0–84.0 |
| AI+Expert | 75.9 | 5.1 | 75.3–76.5 |
| AI+Specialist | 74.6 | 5.3 | 74.0–75.2 |
| AI+Resident | 72.5 | 5.3 | 72.0–73.1 |
| Expert | 64.0 | 5.2 | 63.4–64.5 |
| Specialist | 59.6 | 5.4 | 59.0–60.2 |
| Resident | 56.0 | 5.4 | 55.5–56.6 |

### 4b. Key Pairwise Comparisons

| Comparison | Δ (pp) | 95% CI | P (Bonferroni) | Cohen's d |
|-----------|--------|--------|----------------|-----------|
| OrthoPilot vs Expert | +19.06 | +18.28, +19.85 | <0.0001 | +2.67 |
| OrthoPilot vs Specialist | +23.41 | +22.62, +24.18 | <0.0001 | +3.36 |
| OrthoPilot vs Resident | +26.99 | +26.21, +27.75 | <0.0001 | +3.92 |
| AI+Expert vs Expert | +11.91 | +11.62, +12.19 | <0.0001 | +4.65 |
| AI+Specialist vs Specialist | +14.95 | +14.69, +15.23 | <0.0001 | +6.03 |
| AI+Resident vs Resident | +16.49 | +16.21, +16.77 | <0.0001 | +6.51 |
| AI+Expert vs OrthoPilot | -7.15 | -7.93, -6.36 | <0.0001 | -1.02 |
| AI+Specialist vs OrthoPilot | -8.46 | -9.21, -7.69 | <0.0001 | -1.24 |
| AI+Resident vs OrthoPilot | -10.50 | -11.25, -9.72 | <0.0001 | -1.52 |
| AI+Resident vs Expert | +8.56 | +8.31, +8.83 | <0.0001 | +3.72 |
| AI+Specialist vs Expert | +10.60 | +10.32, +10.87 | <0.0001 | +4.26 |

### 4c. Inter-rater Reliability

| Tier | Shared patients | ICC(2,k) | Fleiss' κ (closed tasks) |
|------|----------------|----------|---------------------------|
| Expert | 20 | 0.884 | 0.007 |
| Specialist | 20 | 0.881 | -0.003 |
| Resident | 20 | 0.869 | -0.003 |

### 4d. AI Assistance Improvement

| Transition | Δ (pp) | Effect |
|-----------|--------|--------|
| Resident → AI+Resident | +16.49 | Largest gain; rises toward AI-alone performance |
| Specialist → AI+Specialist | +14.95 | Compresses the gap with AI-alone performance |
| Expert → AI+Expert | +11.91 | Small but significant improvement over expert-alone performance |

---

## 5. Key Narrative Conclusions

1. **OrthoPilot alone outperforms all unaided physician tiers**, including experts (+19.06 pp versus Expert; Bonferroni-adjusted P <0.0001).

2. **AI assistance compresses the experience gap**: AI+Resident (72.5%) exceeds Expert alone (64.0%), while AI+Expert (75.9%) remains within 1.5 pp of OrthoPilot alone.

3. **All three AI-assisted arms converge near OrthoPilot performance** (72.5%–75.9%), despite substantially different baseline physician experience.

4. **The least experienced physicians benefit the most from AI support**: Resident gains +16.49 pp, compared with +11.91 pp for Experts.

---

## 6. Statistical Methods

- **Bootstrap 95% CI**: 10,000 patient-level resamples for arm- and task-level estimates; 2,000 patient-level resamples for per-physician overall estimates.
- **Permutation test**: Two-sided paired sign-flip permutation test (10,000 permutations) on patient-level arm means.
- **Bonferroni correction**: Applied across 11 prespecified pairwise comparisons.
- **Cohen's d**: Reported as paired standardized mean difference (d_z).
- **ICC**: ICC(2,k) computed on the first 20 shared patients per tier using per-patient overall means across 11 tasks.
- **Fleiss' κ**: Computed on closed-ended tasks (T1–T4) across the same shared-patient subset.

---

## 7. Data Files

| File | Description |
|------|-------------|
| `reader_study_raw_data.csv` | 550,451 rows (patient × task × arm × physician) |
| `physician_profiles.csv` | 81 physician demographics with years of experience |
| `summary_arm_performance.csv` | Arm-level means with 95% CI |
| `summary_task_arm.csv` | Task × Arm performance with 95% CI |
| `summary_pairwise_comparisons.csv` | Prespecified paired comparisons with Bonferroni-adjusted P values |
| `summary_per_physician.csv` | Individual physician task means and overall CI |
| `summary_reliability.csv` | ICC(2,k) and Fleiss' κ by physician tier |
| `table_arm_summary.tex` | LaTeX arm-level summary table |
| `table_per_physician.tex` | LaTeX physician-level longtable |
| `experiment_specification.json` | Full study specification and summary metrics |
