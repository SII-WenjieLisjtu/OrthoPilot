#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
挑选人机对比的困难案例
目标：挑选10个患者，覆盖多个任务，优先选择多个模型都容易出错的case
"""

import json
import os
from collections import defaultdict
from pathlib import Path

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
TEST_FINAL_DIR = BASE_DIR / "gen_validation/test_final"
META_DIR = BASE_DIR / "gen_validation/meta/subset"
OUTPUT_DIR = BASE_DIR / "project/多中心验证/人机对比/case_study"

# 创建输出目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 需要比较的模型（包括顶级基线模型）
MODELS = [
    "bone-14B-RL-v2",  # 我们的模型
    "gpt-5.1",
    "deepseek-r1",
    "Qwen3-235B-A22B-Instruct-2507",
    "kimi-k2-0905-preview",
    "grok-4-fast",
]

def extract_patient_id(case_id):
    """从case_id中提取patient_id"""
    # format: task_X_patient_XXXXXXXX_type
    parts = case_id.split("_")
    if len(parts) >= 4 and parts[2] == "patient":
        return parts[3]
    return None

def load_task_data(task_num):
    """加载某个任务的原始数据"""
    task_file = TEST_FINAL_DIR / f"task{task_num}.json"
    if not task_file.exists():
        print(f"Warning: {task_file} not found")
        return {}

    with open(task_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 建立id到数据的映射
    return {item['id']: item for item in data}

def load_judgements(task_num, model):
    """加载某个任务某个模型的评测结果"""
    if task_num <= 4:
        # task1-4是诊断任务，使用简单文件名
        judge_file = META_DIR / f"task{task_num}_judgements_{model}.json"
    else:
        # task5-11是管理任务，使用带vote的文件名
        judge_file = META_DIR / f"task{task_num}_judgements_{model}__vote_3_2f948c2eb6_Qwen3-235B-A22B-Instruct-2507_Qwen3-235B-A22B-Instruct-2507_Qwen3-235B-A22B-Inst.json"

    if not judge_file.exists():
        # 尝试另一个版本
        judge_file = META_DIR / f"task{task_num}_judgements_{model}__vote_3_44e4d28126_Qwen3-235B-A22B-Instruct-2507_Qwen3-235B-A22B-Instruct-2507_Qwen3-235B-A22B-Inst.json"

    if not judge_file.exists():
        print(f"Warning: {judge_file} not found")
        return []

    with open(judge_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data

def calculate_case_difficulty(case_id, task_num):
    """
    计算case的难度分数
    难度分数 = 预测错误的模型数量 / 总模型数量
    分数越高说明越难
    """
    error_count = 0
    total_count = 0

    for model in MODELS:
        judgements = load_judgements(task_num, model)
        for item in judgements:
            if item['id'] == case_id:
                total_count += 1
                if not item['is_correct']:
                    error_count += 1
                break

    if total_count == 0:
        return 0.0

    return error_count / total_count

def main():
    print("="*80)
    print("开始挑选人机对比案例")
    print("="*80)

    # Step 1: 统计每个patient_id在哪些任务中出现
    print("\n1. 统计患者在各任务中的分布...")
    patient_tasks = defaultdict(set)  # patient_id -> set of tasks
    patient_cases = defaultdict(lambda: defaultdict(list))  # patient_id -> task -> [case_ids]

    # 只处理task1-4（诊断任务），因为这些任务有明确的正误判断
    for task_num in range(1, 5):  # task1-4
        print(f"   处理 task{task_num}...")
        judgements = load_judgements(task_num, "bone-14B-RL-v2")

        for item in judgements:
            patient_id = extract_patient_id(item['id'])
            if patient_id:
                patient_tasks[patient_id].add(task_num)
                patient_cases[patient_id][task_num].append(item['id'])

    # Step 2: 筛选在多个任务中都出现的患者
    print("\n2. 筛选覆盖多个任务的患者...")
    multi_task_patients = {
        pid: tasks for pid, tasks in patient_tasks.items()
        if len(tasks) >= 2  # 至少出现在2个任务中（因为只有4个诊断任务）
    }
    print(f"   找到 {len(multi_task_patients)} 个患者覆盖>=2个任务")

    # Step 3: 为每个患者计算难度分数
    print("\n3. 计算患者案例的难度分数...")
    patient_difficulty = {}

    for patient_id, tasks in multi_task_patients.items():
        total_difficulty = 0
        case_count = 0

        for task_num in tasks:
            for case_id in patient_cases[patient_id][task_num]:
                difficulty = calculate_case_difficulty(case_id, task_num)
                total_difficulty += difficulty
                case_count += 1

        if case_count > 0:
            avg_difficulty = total_difficulty / case_count
            patient_difficulty[patient_id] = {
                'avg_difficulty': avg_difficulty,
                'tasks': sorted(list(tasks)),
                'task_count': len(tasks),
                'case_count': case_count
            }

    # Step 4: 按难度排序并选择top 10
    print("\n4. 选择top 10困难患者...")
    sorted_patients = sorted(
        patient_difficulty.items(),
        key=lambda x: (x[1]['avg_difficulty'], x[1]['task_count']),
        reverse=True
    )

    selected_patients = sorted_patients[:10]

    print(f"\n选中的10个患者:")
    print(f"{'Patient ID':<25} {'任务数':<8} {'案例数':<8} {'平均难度':<10} {'任务列表'}")
    print("-"*80)

    for patient_id, info in selected_patients:
        print(f"{patient_id:<25} {info['task_count']:<8} {info['case_count']:<8} {info['avg_difficulty']:<10.2f} {info['tasks']}")

    # Step 5: 导出选中患者的详细案例
    print("\n5. 导出选中患者的详细案例...")

    selected_cases = []

    for patient_id, info in selected_patients:
        patient_data = {
            'patient_id': patient_id,
            'task_count': info['task_count'],
            'avg_difficulty': info['avg_difficulty'],
            'tasks': {}
        }

        for task_num in info['tasks']:
            task_data_dict = load_task_data(task_num)
            task_cases = []

            for case_id in patient_cases[patient_id][task_num]:
                # 加载原始数据
                original_data = task_data_dict.get(case_id, {})

                # 加载各模型的预测结果
                model_predictions = {}
                for model in MODELS:
                    judgements = load_judgements(task_num, model)
                    for item in judgements:
                        if item['id'] == case_id:
                            model_predictions[model] = {
                                'prediction': item['prediction'],
                                'is_correct': item['is_correct']
                            }
                            break

                # 计算难度分数
                difficulty = calculate_case_difficulty(case_id, task_num)

                case_info = {
                    'case_id': case_id,
                    'type': original_data.get('type', 'unknown'),
                    'difficulty': difficulty,
                    'conversations': original_data.get('conversations', []),
                    'model_predictions': model_predictions,
                    'ground_truth': judgements[0].get('ground_truth', '') if judgements else ''
                }

                task_cases.append(case_info)

            patient_data['tasks'][f'task{task_num}'] = task_cases

        selected_cases.append(patient_data)

    # 保存为JSON
    output_file = OUTPUT_DIR / "selected_hard_cases.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(selected_cases, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 案例详情已保存到: {output_file}")

    # Step 6: 生成医生评测用的简化版本
    print("\n6. 生成医生评测用的简化版本...")

    doctor_eval_cases = []

    for patient_data in selected_cases:
        patient_eval = {
            'patient_id': patient_data['patient_id'],
            'cases': []
        }

        for task_name, task_cases in patient_data['tasks'].items():
            for case in task_cases:
                # 提取问题和标准答案
                conversations = case['conversations']
                question = ""
                answer = ""

                for conv in conversations:
                    if conv['from'] == 'human':
                        question = conv['value']
                    elif conv['from'] == 'gpt':
                        answer = conv['value']

                case_eval = {
                    'case_id': case['case_id'],
                    'task': task_name,
                    'type': case['type'],
                    'question': question,
                    'standard_answer': answer.replace('<think>\n\n</think>\n\n', ''),
                    'difficulty': case['difficulty'],
                    'doctor_answer': "",  # 待填写
                    'doctor_notes': ""  # 待填写
                }

                patient_eval['cases'].append(case_eval)

        doctor_eval_cases.append(patient_eval)

    # 保存医生评测版本
    doctor_file = OUTPUT_DIR / "cases_for_doctor_evaluation.json"
    with open(doctor_file, 'w', encoding='utf-8') as f:
        json.dump(doctor_eval_cases, f, ensure_ascii=False, indent=2)

    print(f"✓ 医生评测版本已保存到: {doctor_file}")

    # 生成统计摘要
    print("\n" + "="*80)
    print("统计摘要")
    print("="*80)

    total_cases = sum(len(p['cases']) for p in doctor_eval_cases)
    task_distribution = defaultdict(int)
    type_distribution = defaultdict(int)

    for patient_data in doctor_eval_cases:
        for case in patient_data['cases']:
            task_distribution[case['task']] += 1
            type_distribution[case['type']] += 1

    print(f"\n总患者数: {len(doctor_eval_cases)}")
    print(f"总案例数: {total_cases}")
    print(f"\n任务分布:")
    for task, count in sorted(task_distribution.items()):
        print(f"  {task}: {count}")
    print(f"\n类型分布:")
    for typ, count in sorted(type_distribution.items()):
        print(f"  {typ}: {count}")

    print("\n" + "="*80)
    print("完成!")
    print("="*80)

if __name__ == "__main__":
    main()
