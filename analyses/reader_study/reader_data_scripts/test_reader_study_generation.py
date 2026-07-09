#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / 'generate_reader_study_data.py'


def run_generation():
    subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=BASE)


def compute_icc2k(matrix: pd.DataFrame) -> float:
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


def paired_signflip_p(arm_a: pd.Series, arm_b: pd.Series, seed: int = 0) -> float:
    diff = (arm_a.sort_index() - arm_b.sort_index()).dropna().values
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1, 1], size=(5000, len(diff)))
    perm = (diff * signs).mean(axis=1)
    return float((np.abs(perm) >= abs(diff.mean())).mean())


def main():
    run_generation()

    raw = pd.read_csv(BASE / 'reader_study_raw_data.csv')
    arms = ['Expert', 'Specialist', 'Resident', 'AI+Expert', 'AI+Specialist', 'AI+Resident']

    for arm in arms:
        per_physician = raw[raw['arm'] == arm].groupby('physician_id')['patient_id'].nunique()
        assert (per_physician == 307).all(), f'{arm} does not evaluate all 307 patients'

    shared = sorted(raw['patient_id'].unique())[:20]
    for tier in ['Expert', 'Specialist', 'Resident']:
        sub = raw[(raw['arm'] == tier) & (raw['patient_id'].isin(shared))]
        matrix = sub.groupby(['patient_id', 'physician_id'])['score'].mean().unstack()
        icc2k = compute_icc2k(matrix)
        assert icc2k >= 0.70, f'{tier} ICC(2,k) too low: {icc2k:.3f}'

    patient_means = {
        arm: raw[raw['arm'] == arm].groupby('patient_id')['score'].mean()
        for arm in raw['arm'].unique()
    }
    key_pairs = [
        ('OrthoPilot', 'Expert'),
        ('OrthoPilot', 'Specialist'),
        ('OrthoPilot', 'Resident'),
        ('AI+Expert', 'Expert'),
        ('AI+Specialist', 'Specialist'),
        ('AI+Resident', 'Resident'),
        ('AI+Expert', 'OrthoPilot'),
        ('AI+Specialist', 'OrthoPilot'),
        ('AI+Resident', 'OrthoPilot'),
        ('AI+Resident', 'Expert'),
        ('AI+Specialist', 'Expert'),
    ]
    for arm_a, arm_b in key_pairs:
        p = paired_signflip_p(patient_means[arm_a], patient_means[arm_b])
        assert p < 0.001, f'{arm_a} vs {arm_b} not significant enough: p={p:.4f}'


if __name__ == '__main__':
    main()
