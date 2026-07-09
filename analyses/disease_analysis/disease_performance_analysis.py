#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
疾病维度性能分析脚本
- 按疾病统计各模型在各任务上的性能
- 区分域内/域外、罕见/非罕见
- 输出CSV和可视化图表
"""

import os
import json
import re
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt

# 配置
META_ROOT = "/path/to/orthopilot/gen_validation/meta/subset"
RESULT_ROOT = "/path/to/orthopilot/gen_validation/result"
TEST_SUBSET_PATH = "/path/to/orthopilot/gen_validation/test_final/test_subset/test_ids.csv"
TEST_FULL_PATH = "/path/to/orthopilot/gen_validation/test_final/test_ids.csv"
CODE_COUNTS_PATH = "/path/to/orthopilot/data/stat/all/code_counts.csv"
OUTPUT_DIR = "/path/to/orthopilot/project/多中心验证/disease_analysis/output"

# 任务映射
CLOSED_TASKS = [1, 2, 3, 4]  # 诊断任务
OPEN_TASKS = [5, 6, 7, 8, 9, 10, 11]  # 管理任务

# 主要模型列表 - 使用显示名称
PRIMARY_MODELS = [
    "bone-14B-RL-v2",  # CHEESE
    "gpt-5.1",
    "deepseek-r1",
    "Qwen3-235B-A22B-Instruct-2507",
    "Gemini-2.5-flash",
    "kimi-k2-0905-preview",
    "llama-4-maverick",
    "anthropic_claude-sonnet-4.5",
]

# 模型名称映射 - task 1-4 (JSON文件名) -> task 5-11 (目录名)
# 注意：有些模型在两个任务类型中的名称不同
MODEL_NAME_MAPPING = {
    # 封闭式任务名称 -> 开放式任务名称
    "bone-14B-RL-v2": "bone-14B-RL-v2",
    "gpt-5.1": "gpt-5-2025-08-07",  # task 5-11中使用不同名称
    "deepseek-r1": "deepseek-r1-0528-ep",
    "Qwen3-235B-A22B-Instruct-2507": "qwen3-235b-a22b-instruct-2507",
    "Gemini-2.5-flash": "gemini-2.5-flash",
    "kimi-k2-0905-preview": "moonshotai_kimi-k2",
    "llama-4-maverick": "meta-llama_llama-4-maverick",
    "anthropic_claude-sonnet-4.5": "anthropic_claude-sonnet-4.5",
}

# 提取patient id的正则
PID_PAT = re.compile(r"patient_([^_]+)", re.IGNORECASE)


def extract_pid(item_id: str) -> str:
    """从ID字符串中提取patient ID"""
    m = PID_PAT.search(item_id or "")
    return m.group(1) if m else ""


def load_patient_disease_mapping():
    """加载患者到疾病的映射"""
    # 加载subset test_ids (实际评测的患者)
    subset_df = pd.read_csv(TEST_SUBSET_PATH)
    print(f"加载subset test_ids: {len(subset_df)}行")

    # 加载code_counts获取疾病名称
    code_df = pd.read_csv(CODE_COUNTS_PATH, encoding='utf-8-sig')
    print(f"加载code_counts: {len(code_df)}行")

    # 创建code到疾病名称的映射
    code_to_name = dict(zip(code_df['出院诊断编码'].astype(str), code_df['最常见对应诊断'].astype(str)))

    # 构建patient -> disease信息映射
    patient_info = {}
    for _, row in subset_df.iterrows():
        pid = str(row['patient_id'])
        code = str(row['disease_code'])
        disease_name = code_to_name.get(code, code)

        patient_info[pid] = {
            'patient_id': pid,
            'domain': row['domain'],  # ID (In-Domain) 或 OOD
            'disease_code': code,
            'disease_name': disease_name,
            'is_rare': row['is_rare'],
            'match_type': row['match_type'],
            'code_n_in_full_test': row['code_n_in_full_test'],
            'code_n_in_subset': row['code_n_in_subset'],
        }

    return patient_info


def load_closed_task_scores(task: int, model: str):
    """加载封闭式任务（1-4）的分数
    从judgement JSON文件中提取每个patient的is_correct
    """
    # 处理claude的特殊前缀
    if model.startswith("anthropic_"):
        model_file = model
    else:
        model_file = model

    judgement_file = os.path.join(META_ROOT, f"task{task}_judgements_{model_file}.json")

    if not os.path.exists(judgement_file):
        print(f"  未找到文件: {judgement_file}")
        return {}

    with open(judgement_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 按patient聚合
    patient_scores = defaultdict(list)

    for item in data:
        item_id = item.get('id', '')
        pid = extract_pid(item_id)
        if not pid:
            continue

        is_correct = item.get('is_correct', False)
        patient_scores[pid].append(1 if is_correct else 0)

    # 计算每个patient的平均正确率
    patient_avg = {}
    for pid, scores in patient_scores.items():
        patient_avg[pid] = np.mean(scores)

    return patient_avg


def calculate_coverage_score(coverage_dict):
    """计算单个coverage字典的分数
    coverage_dict包含primary/secondary/additional
    """
    def calc_level_score(level_items):
        if not level_items or not isinstance(level_items, list):
            return None
        # 过滤掉非字典项
        valid_items = [item for item in level_items if isinstance(item, dict)]
        if not valid_items:
            return None
        covered = sum(1 for item in valid_items if item.get('是否覆盖', False))
        return covered / len(valid_items)

    primary_score = calc_level_score(coverage_dict.get('primary', []))
    secondary_score = calc_level_score(coverage_dict.get('secondary', []))
    additional_score = calc_level_score(coverage_dict.get('additional', []))

    # 计算加权总分（primary最重要）
    scores = []
    weights = []
    if primary_score is not None:
        scores.append(primary_score)
        weights.append(0.6)
    if secondary_score is not None:
        scores.append(secondary_score)
        weights.append(0.3)
    if additional_score is not None:
        scores.append(additional_score)
        weights.append(0.1)

    if not scores:
        return None  # 返回None表示没有相关评分项

    # 归一化权重
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    return sum(s * w for s, w in zip(scores, weights))


def calculate_open_item_score(judgement_item):
    """计算开放式任务中单个judgement项的分数
    基于primary/secondary/additional的覆盖率

    不同任务有不同的结构：
    - Task 5: 有'明确的判断'键
    - Task 6-11: 有多个类别键（如'手术计划', '护理及饮食'等）
    """
    # 排除非评判相关的键
    metadata_keys = {'uid', 'input', 'inference', 'ensemble_tag', 'judge_specs', 'raw_errors', 'raw_judgements'}

    # 检查是否有'明确的判断'（Task 5风格）
    if '明确的判断' in judgement_item:
        coverage = judgement_item['明确的判断']
        score = calculate_coverage_score(coverage)
        return score if score is not None else 0.0

    # 否则是多类别结构（Task 6-11风格）
    # 收集所有类别的分数
    category_scores = []
    for key in judgement_item.keys():
        if key in metadata_keys:
            continue
        category_data = judgement_item[key]
        if isinstance(category_data, dict) and ('primary' in category_data or 'secondary' in category_data or 'additional' in category_data):
            score = calculate_coverage_score(category_data)
            if score is not None:
                category_scores.append(score)

    if not category_scores:
        return 0.0

    # 返回所有类别的平均分
    return np.mean(category_scores)


def load_open_task_scores(task: int, model: str):
    """加载开放式任务（5-11）的分数
    从per-patient judgement目录中提取分数
    """
    # 获取开放式任务的模型名称
    open_model_name = MODEL_NAME_MAPPING.get(model, model)

    # 找到对应的judgement目录
    task_dir = os.path.join(META_ROOT, f"task_{task}")
    if not os.path.exists(task_dir):
        print(f"  未找到目录: {task_dir}")
        return {}

    # 找到该模型对应的judgement目录 (优先使用vote_3_2f948c2eb6)
    model_dir = None
    preferred_suffix = "vote_3_2f948c2eb6"

    for dirname in os.listdir(task_dir):
        if dirname.startswith(f"judgement_{open_model_name}__"):
            model_dir = os.path.join(task_dir, dirname)
            if preferred_suffix in dirname:
                break  # 找到优先的后缀，停止搜索

    if model_dir is None:
        print(f"  未找到模型目录: {open_model_name}")
        return {}

    patient_scores = {}

    for filename in os.listdir(model_dir):
        if not filename.endswith('.json'):
            continue

        pid = filename.replace('.json', '')
        filepath = os.path.join(model_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # data是一个list of judgements
        if not isinstance(data, list):
            continue

        scores = [calculate_open_item_score(item) for item in data]
        if scores:
            patient_scores[pid] = np.mean(scores)

    return patient_scores


def analyze_model_task_performance(patient_info, model: str, task: int):
    """分析特定模型在特定任务上的性能"""
    if task in CLOSED_TASKS:
        scores = load_closed_task_scores(task, model)
    else:
        scores = load_open_task_scores(task, model)

    if not scores:
        return None

    # 合并patient信息和分数
    results = []
    for pid, info in patient_info.items():
        if pid in scores:
            row = info.copy()
            row['model'] = model
            row['task'] = task
            row['score'] = scores[pid]
            row['task_type'] = 'closed' if task in CLOSED_TASKS else 'open'
            results.append(row)

    return pd.DataFrame(results)


def aggregate_by_disease(df):
    """按疾病聚合统计"""
    agg = df.groupby(['disease_code', 'disease_name', 'model', 'task']).agg({
        'score': ['mean', 'std', 'count'],
        'domain': 'first',
        'is_rare': 'first',
    }).reset_index()

    agg.columns = ['disease_code', 'disease_name', 'model', 'task',
                   'mean_score', 'std_score', 'n_patients',
                   'domain', 'is_rare']

    return agg


def aggregate_by_category(df):
    """按类别（域内/域外、罕见/非罕见）聚合"""
    agg = df.groupby(['model', 'task', 'domain', 'is_rare']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()

    agg.columns = ['model', 'task', 'domain', 'is_rare',
                   'mean_score', 'std_score', 'n_cases']

    return agg


def calculate_disease_overall_scores(df):
    """计算每个病种在所有任务上的全局平均分数"""
    # 按disease和model聚合，计算所有任务的平均
    agg = df.groupby(['disease_code', 'disease_name', 'model', 'domain', 'is_rare']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()

    agg.columns = ['disease_code', 'disease_name', 'model', 'domain', 'is_rare',
                   'overall_score', 'std_score', 'n_cases']

    return agg


def calculate_task_type_scores(df):
    """计算封闭式和开放式任务分别的平均分数"""
    agg = df.groupby(['model', 'task_type']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()

    agg.columns = ['model', 'task_type', 'mean_score', 'std_score', 'n_cases']

    return agg


def main():
    """主函数"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. 加载患者到疾病的映射
    print("=" * 60)
    print("1. 加载患者-疾病映射...")
    print("=" * 60)
    patient_info = load_patient_disease_mapping()
    print(f"  共 {len(patient_info)} 个患者")

    # 打印一些统计信息
    domain_counts = defaultdict(int)
    rare_counts = defaultdict(int)
    for info in patient_info.values():
        domain_counts[info['domain']] += 1
        if info['is_rare']:
            rare_counts['rare'] += 1
        else:
            rare_counts['non-rare'] += 1

    print(f"  域内患者: {domain_counts.get('ID', 0)}, 域外患者: {domain_counts.get('OOD', 0)}")
    print(f"  罕见病: {rare_counts.get('rare', 0)}, 非罕见病: {rare_counts.get('non-rare', 0)}")

    # 2. 收集所有模型和任务的数据
    print("\n" + "=" * 60)
    print("2. 收集各模型各任务的性能数据...")
    print("=" * 60)

    all_data = []

    for model in PRIMARY_MODELS:
        print(f"\n模型: {model}")
        has_data = False
        for task in range(1, 12):
            df = analyze_model_task_performance(patient_info, model, task)
            if df is not None and not df.empty:
                all_data.append(df)
                print(f"  Task {task}: {len(df)} patients")
                has_data = True
            else:
                print(f"  Task {task}: 无数据")

        if not has_data:
            print(f"  [警告] 模型 {model} 没有任何数据")

    if not all_data:
        print("错误：没有收集到任何数据")
        return

    # 合并所有数据
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\n总数据行数: {len(combined_df)}")

    # 保存原始数据
    combined_df.to_csv(os.path.join(OUTPUT_DIR, "raw_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"已保存原始数据到: {os.path.join(OUTPUT_DIR, 'raw_scores.csv')}")

    # 3. 按疾病聚合
    print("\n" + "=" * 60)
    print("3. 按疾病聚合统计...")
    print("=" * 60)

    disease_agg = aggregate_by_disease(combined_df)
    disease_agg.to_csv(os.path.join(OUTPUT_DIR, "disease_level_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  疾病级别聚合: {len(disease_agg)} 行")

    # 4. 按类别聚合（域内/域外，罕见/非罕见）
    print("\n" + "=" * 60)
    print("4. 按类别聚合统计...")
    print("=" * 60)

    category_agg = aggregate_by_category(combined_df)
    category_agg.to_csv(os.path.join(OUTPUT_DIR, "category_level_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  类别级别聚合: {len(category_agg)} 行")
    print(f"\n预览:")
    print(category_agg.head(20).to_string(index=False))

    # 5. 计算病种全局平均分数
    print("\n" + "=" * 60)
    print("5. 计算病种全局平均分数...")
    print("=" * 60)

    disease_overall = calculate_disease_overall_scores(combined_df)
    disease_overall.to_csv(os.path.join(OUTPUT_DIR, "disease_overall_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  病种全局分数: {len(disease_overall)} 行")
    print(f"\n预览 (按分数排序前10):")
    print(disease_overall.sort_values('overall_score', ascending=False).head(10).to_string(index=False))

    # 6. 按任务类型（封闭式/开放式）统计
    print("\n" + "=" * 60)
    print("6. 按任务类型统计...")
    print("=" * 60)

    task_type_agg = calculate_task_type_scores(combined_df)
    task_type_agg.to_csv(os.path.join(OUTPUT_DIR, "task_type_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  任务类型聚合: {len(task_type_agg)} 行")
    print(f"\n预览:")
    print(task_type_agg.to_string(index=False))

    # 7. 按模型统计每个任务的平均分数
    print("\n" + "=" * 60)
    print("7. 按模型-任务统计...")
    print("=" * 60)

    model_task_agg = combined_df.groupby(['model', 'task', 'task_type']).agg({
        'score': ['mean', 'std', 'count'],
    }).reset_index()
    model_task_agg.columns = ['model', 'task', 'task_type', 'mean_score', 'std_score', 'n_cases']
    model_task_agg.to_csv(os.path.join(OUTPUT_DIR, "model_task_scores.csv"), index=False, encoding='utf-8-sig')
    print(f"  模型-任务聚合: {len(model_task_agg)} 行")
    print(f"\n预览:")
    print(model_task_agg.to_string(index=False))

    # 8. 生成报告
    print("\n" + "=" * 60)
    print("8. 生成分析报告...")
    print("=" * 60)

    report_lines = []
    report_lines.append("# 疾病维度性能分析报告\n")
    report_lines.append(f"**生成日期**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n")

    # 整体统计
    report_lines.append("## 1. 整体统计\n")
    report_lines.append(f"- 评测患者总数: {len(patient_info)}\n")
    report_lines.append(f"- 域内患者: {domain_counts.get('ID', 0)} ({domain_counts.get('ID', 0)/len(patient_info)*100:.1f}%)\n")
    report_lines.append(f"- 域外患者: {domain_counts.get('OOD', 0)} ({domain_counts.get('OOD', 0)/len(patient_info)*100:.1f}%)\n")
    report_lines.append(f"- 罕见病: {rare_counts.get('rare', 0)} ({rare_counts.get('rare', 0)/len(patient_info)*100:.1f}%)\n")
    report_lines.append(f"- 非罕见病: {rare_counts.get('non-rare', 0)} ({rare_counts.get('non-rare', 0)/len(patient_info)*100:.1f}%)\n\n")

    # 各模型在各任务类型上的性能
    report_lines.append("## 2. 各模型在封闭式/开放式任务上的性能\n")
    report_lines.append(task_type_agg.to_markdown(index=False))
    report_lines.append("\n\n")

    # 各模型在域内/域外、罕见/非罕见上的表现
    report_lines.append("## 3. 各模型在域内/域外、罕见/非罕见上的表现\n")
    report_lines.append("### 按模型汇总（跨所有任务）\n")

    for model in PRIMARY_MODELS:
        model_data = category_agg[category_agg['model'] == model]
        if not model_data.empty:
            report_lines.append(f"#### {model}\n")
            report_lines.append(model_data.to_markdown(index=False))
            report_lines.append("\n\n")

    # 疾病级别TOP/BOTTOM性能
    report_lines.append("## 4. 各模型在不同疾病上的性能（Top 10）\n")

    for model in PRIMARY_MODELS:
        model_diseases = disease_overall[disease_overall['model'] == model].sort_values('overall_score', ascending=False)
        if len(model_diseases) > 0:
            report_lines.append(f"### {model} - 表现最佳的10种疾病\n")
            report_lines.append(model_diseases.head(10)[['disease_code', 'disease_name', 'domain', 'is_rare', 'overall_score', 'n_cases']].to_markdown(index=False))
            report_lines.append("\n\n")

            report_lines.append(f"### {model} - 表现最差的10种疾病\n")
            report_lines.append(model_diseases.tail(10)[['disease_code', 'disease_name', 'domain', 'is_rare', 'overall_score', 'n_cases']].to_markdown(index=False))
            report_lines.append("\n\n")

    # 按任务统计
    report_lines.append("## 5. 各模型在各任务上的详细性能\n")
    report_lines.append(model_task_agg.to_markdown(index=False))
    report_lines.append("\n\n")

    # 保存报告
    report_path = os.path.join(OUTPUT_DIR, "report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"已保存报告到: {report_path}")

    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    print(f"输出文件：")
    print(f"  - {OUTPUT_DIR}/raw_scores.csv")
    print(f"  - {OUTPUT_DIR}/disease_level_scores.csv")
    print(f"  - {OUTPUT_DIR}/category_level_scores.csv")
    print(f"  - {OUTPUT_DIR}/disease_overall_scores.csv")
    print(f"  - {OUTPUT_DIR}/task_type_scores.csv")
    print(f"  - {OUTPUT_DIR}/model_task_scores.csv")
    print(f"  - {OUTPUT_DIR}/report.md")


if __name__ == "__main__":
    main()
