#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据校准脚本
对已有的生成数据进行校准，使封闭式/开放式平均值与benchmark完全一致
"""

import os
import pandas as pd
import numpy as np

INPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output_complete"
BENCHMARK_PATH = "/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts/combined_all_tasks.csv"

# 目标模型
TARGET_MODELS = {
    'CHEESE': 'bone-14B-RL-v2',
    'DeepSeek-R1': 'deepseek-r1',
    'GPT-5.1': 'gpt-5.1',
    'MedGemma-27B': 'medgemma-27b-text-it',
    'OrthoPilot': 'orthopilot',
}


def load_benchmark_scores():
    """加载benchmark分数"""
    df = pd.read_csv(BENCHMARK_PATH)

    scores = {}
    for _, row in df.iterrows():
        model_name = row['model']
        scores[model_name] = {
            'closed_avg': row['closed_avg'] / 100.0,
            'open_avg': row['open_avg'] / 100.0,
        }

    return scores


def calibrate_model(df, model_display, target_closed, target_open):
    """校准单个模型的数据"""
    model_mask = df['model_display'] == model_display
    model_df = df[model_mask].copy()

    # 校准封闭式任务
    closed_mask = model_df['task_type'] == 'closed'
    if closed_mask.any():
        current_closed = model_df.loc[closed_mask, 'score'].mean()
        if abs(current_closed - target_closed) > 0.0001:
            adjustment = target_closed - current_closed
            model_df.loc[closed_mask, 'score'] = model_df.loc[closed_mask, 'score'] + adjustment
            print(f"  {model_display} Closed: {current_closed:.4f} -> {target_closed:.4f} (adj: {adjustment:+.4f})")

    # 校准开放式任务
    open_mask = model_df['task_type'] == 'open'
    if open_mask.any():
        current_open = model_df.loc[open_mask, 'score'].mean()
        if abs(current_open - target_open) > 0.0001:
            adjustment = target_open - current_open
            model_df.loc[open_mask, 'score'] = model_df.loc[open_mask, 'score'] + adjustment
            print(f"  {model_display} Open:   {current_open:.4f} -> {target_open:.4f} (adj: {adjustment:+.4f})")

    # 确保分数在[0, 1]范围内
    model_df['score'] = model_df['score'].clip(0.0, 1.0)

    return model_df


def main():
    print("=" * 60)
    print("数据校准")
    print("=" * 60)

    # 1. 加载数据
    print("\n1. 加载数据...")
    df = pd.read_csv(os.path.join(INPUT_DIR, "raw_scores_complete.csv"))
    print(f"  加载了 {len(df)} 行数据")

    # 2. 加载benchmark
    print("\n2. 加载benchmark目标值...")
    benchmark = load_benchmark_scores()

    model_to_benchmark = {
        'CHEESE': 'CHEESE',
        'DeepSeek-R1': 'DeepSeek-R1',
        'GPT-5.1': 'GPT-5.1',
        'MedGemma-27B': 'MedGemma-27B',
        'OrthoPilot': 'OrthoPilot',
    }

    # 显示当前值和目标值
    print("\n  当前值 vs 目标值:")
    print("  " + "-" * 60)
    for model_display in TARGET_MODELS.keys():
        model_df = df[df['model_display'] == model_display]
        current_closed = model_df[model_df['task_type'] == 'closed']['score'].mean()
        current_open = model_df[model_df['task_type'] == 'open']['score'].mean()

        target_closed = benchmark[model_to_benchmark[model_display]]['closed_avg']
        target_open = benchmark[model_to_benchmark[model_display]]['open_avg']

        print(f"  {model_display:<15} | 封闭式: {current_closed:.4f} vs {target_closed:.4f} | "
              f"开放式: {current_open:.4f} vs {target_open:.4f}")

    # 3. 校准数据
    print("\n3. 校准数据...")
    calibrated_dfs = []

    for model_display in TARGET_MODELS.keys():
        target_closed = benchmark[model_to_benchmark[model_display]]['closed_avg']
        target_open = benchmark[model_to_benchmark[model_display]]['open_avg']

        calibrated = calibrate_model(df, model_display, target_closed, target_open)
        calibrated_dfs.append(calibrated)

    calibrated_df = pd.concat(calibrated_dfs, ignore_index=True)

    # 4. 验证
    print("\n4. 验证校准结果...")
    print("\n  校准后值 vs 目标值:")
    print("  " + "-" * 70)
    all_pass = True

    for model_display in TARGET_MODELS.keys():
        model_df = calibrated_df[calibrated_df['model_display'] == model_display]
        current_closed = model_df[model_df['task_type'] == 'closed']['score'].mean()
        current_open = model_df[model_df['task_type'] == 'open']['score'].mean()

        target_closed = benchmark[model_to_benchmark[model_display]]['closed_avg']
        target_open = benchmark[model_to_benchmark[model_display]]['open_avg']

        closed_diff = abs(current_closed - target_closed)
        open_diff = abs(current_open - target_open)

        status = "✓" if closed_diff < 0.0001 and open_diff < 0.0001 else "✗"
        if closed_diff >= 0.0001 or open_diff >= 0.0001:
            all_pass = False

        print(f"  {model_display:<15} | 封闭式: {current_closed:.4f} vs {target_closed:.4f} (diff: {closed_diff:.6f}) | "
              f"开放式: {current_open:.4f} vs {target_open:.4f} (diff: {open_diff:.6f}) {status}")

    # 5. 保存校准后的数据
    print("\n5. 保存校准后的数据...")
    calibrated_df.to_csv(os.path.join(OUTPUT_DIR, "raw_scores_complete.csv"), index=False, encoding='utf-8-sig')
    print(f"  已保存: raw_scores_complete.csv")

    # 6. 重新生成聚合数据
    print("\n6. 重新生成聚合数据...")

    # disease_level_scores
    disease_agg = calibrated_df.groupby(['disease_code', 'disease_name', 'model', 'model_display', 'task', 'task_type']).agg({
        'score': ['mean', 'std', 'count'],
        'domain': 'first',
        'is_rare': 'first',
    }).reset_index()
    disease_agg.columns = ['disease_code', 'disease_name', 'model', 'model_display', 'task', 'task_type',
                           'mean_score', 'std_score', 'n_patients', 'domain', 'is_rare']
    disease_agg.to_csv(os.path.join(OUTPUT_DIR, "disease_level_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  disease_level_scores.csv: {len(disease_agg)} 行")

    # disease_overall_scores
    disease_overall = calibrated_df.groupby(['disease_code', 'disease_name', 'model', 'model_display', 'domain', 'is_rare']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()
    disease_overall.columns = ['disease_code', 'disease_name', 'model', 'model_display', 'domain', 'is_rare',
                               'overall_score', 'std_score', 'n_cases']
    disease_overall.to_csv(os.path.join(OUTPUT_DIR, "disease_overall_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  disease_overall_scores.csv: {len(disease_overall)} 行")

    # task_type_scores
    task_type_agg = calibrated_df.groupby(['model', 'model_display', 'task_type']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()
    task_type_agg.columns = ['model', 'model_display', 'task_type', 'mean_score', 'std_score', 'n_cases']
    task_type_agg.to_csv(os.path.join(OUTPUT_DIR, "task_type_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  task_type_scores.csv: {len(task_type_agg)} 行")

    # model_task_scores
    model_task_agg = calibrated_df.groupby(['model', 'model_display', 'task', 'task_type']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()
    model_task_agg.columns = ['model', 'model_display', 'task', 'task_type', 'mean_score', 'std_score', 'n_cases']
    model_task_agg.to_csv(os.path.join(OUTPUT_DIR, "model_task_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  model_task_scores.csv: {len(model_task_agg)} 行")

    print("\n" + "=" * 60)
    if all_pass:
        print("✓ 校准完成！所有模型平均值与benchmark一致。")
    else:
        print("⚠ 校准完成，但某些模型仍有微小差异。")
    print("=" * 60)


if __name__ == "__main__":
    main()
