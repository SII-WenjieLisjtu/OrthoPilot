#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
挑选人机对比的困难案例 - 包含所有11个任务
Task 1-4: 诊断任务（入院、术前、术后、出院诊断）
Task 5-11: 管理任务（围手术期风险评估、手术方案选择、手术记录生成、术后医嘱、出院总结、康复计划、多学科会诊）
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

# 任务名称
TASK_NAMES = {
    1: '入院诊断',
    2: '术前诊断',
    3: '术后诊断',
    4: '出院诊断',
    5: '围手术期风险评估',
    6: '手术方案选择',
    7: '手术记录生成',
    8: '术后医嘱',
    9: '出院总结',
    10: '康复计划',
    11: '多学科会诊'
}

# 需要比较的模型
MODELS = [
    "bone-14B-RL-v2",
    "gpt-5.1",
    "deepseek-r1",
    "Qwen3-235B-A22B-Instruct-2507",
    "kimi-k2-0905-preview",
    "grok-4-fast",
]

def extract_patient_id(case_id):
    """从case_id中提取patient_id"""
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

    print(f"   加载 task{task_num} 原始数据...")
    with open(task_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 建立映射
    if task_num <= 4:
        # task1-4: 按case_id映射
        return {item['id']: item for item in data}
    else:
        # task5-11: 按patient_id映射
        result = {}
        for item in data:
            patient_id = extract_patient_id(item['id'])
            if patient_id:
                if patient_id not in result:
                    result[patient_id] = []
                result[patient_id].append(item)
        return result

def load_diagnostic_judgements(task_nums, models):
    """加载task1-4的评测结果"""
    print("\n预加载诊断任务(task1-4)评测结果...")
    all_judgements = {}

    for task_num in task_nums:
        for model in models:
            judge_file = META_DIR / f"task{task_num}_judgements_{model}.json"

            if not judge_file.exists():
                print(f"   Warning: {judge_file} not found")
                continue

            print(f"   加载 task{task_num} - {model}...")
            with open(judge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            judgement_dict = {item['id']: item for item in data}
            all_judgements[(task_num, model)] = judgement_dict

    return all_judgements

def load_management_scores(task_nums, models):
    """加载task5-11的评测分数"""
    print("\n预加载管理任务(task5-11)评测结果...")
    all_scores = {}

    for task_num in task_nums:
        for model in models:
            # task5-11使用scores文件
            score_files = list(META_DIR.glob(f"task{task_num}_scores_{model}*.json"))

            if not score_files:
                print(f"   Warning: task{task_num} scores for {model} not found")
                continue

            score_file = score_files[0]
            print(f"   加载 task{task_num} - {model}...")

            with open(score_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 建立patient_id到scores的映射
            score_dict = {item['patient_id']: item['scores'] for item in data}
            all_scores[(task_num, model)] = score_dict

    return all_scores

def main():
    print("="*80)
    print("挑选人机对比案例（包含所有11个任务）")
    print("="*80)

    # 定义任务范围
    diagnostic_tasks = list(range(1, 5))  # task1-4
    management_tasks = list(range(5, 12))  # task5-11

    # 预加载所有数据
    diagnostic_judgements = load_diagnostic_judgements(diagnostic_tasks, MODELS)
    management_scores = load_management_scores(management_tasks, MODELS)

    # Step 1: 统计每个patient_id在哪些任务中出现
    print("\n1. 统计患者在各任务中的分布...")
    patient_tasks = defaultdict(set)
    patient_cases = defaultdict(lambda: defaultdict(list))

    # task1-4
    for task_num in diagnostic_tasks:
        print(f"   处理 task{task_num}...")
        key = (task_num, "bone-14B-RL-v2")
        if key not in diagnostic_judgements:
            continue

        for case_id in diagnostic_judgements[key].keys():
            patient_id = extract_patient_id(case_id)
            if patient_id:
                patient_tasks[patient_id].add(task_num)
                patient_cases[patient_id][task_num].append(case_id)

    # task5-11
    for task_num in management_tasks:
        print(f"   处理 task{task_num}...")
        key = (task_num, "bone-14B-RL-v2")
        if key not in management_scores:
            continue

        for patient_id in management_scores[key].keys():
            patient_tasks[patient_id].add(task_num)
            # task5-11以patient为单位，不需要case列表

    # Step 2: 筛选在多个任务中都出现的患者（优先选择覆盖11个任务的）
    print("\n2. 筛选覆盖多个任务的患者...")

    # 优先选择覆盖所有11个任务的患者
    full_coverage_patients = {
        pid: tasks for pid, tasks in patient_tasks.items()
        if len(tasks) >= 10  # 至少覆盖10个任务
    }

    print(f"   找到 {len(full_coverage_patients)} 个患者覆盖>=10个任务")

    if len(full_coverage_patients) < 10:
        # 如果不够，降低要求
        full_coverage_patients = {
            pid: tasks for pid, tasks in patient_tasks.items()
            if len(tasks) >= 8
        }
        print(f"   降低要求：找到 {len(full_coverage_patients)} 个患者覆盖>=8个任务")

    # Step 3: 为每个患者计算难度分数（基于task1-4）
    print("\n3. 计算患者在诊断任务上的难度分数...")
    patient_difficulty = {}

    for idx, (patient_id, tasks) in enumerate(full_coverage_patients.items()):
        if idx % 100 == 0:
            print(f"   处理 {idx}/{len(full_coverage_patients)} 个患者...")

        # 只基于task1-4计算难度
        diagnostic_tasks_for_patient = [t for t in tasks if t <= 4]

        if not diagnostic_tasks_for_patient:
            continue

        total_difficulty = 0
        case_count = 0

        for task_num in diagnostic_tasks_for_patient:
            for case_id in patient_cases[patient_id][task_num]:
                error_count = 0
                total_count = 0

                for model in MODELS:
                    key = (task_num, model)
                    if key in diagnostic_judgements and case_id in diagnostic_judgements[key]:
                        total_count += 1
                        if not diagnostic_judgements[key][case_id].get('is_correct', False):
                            error_count += 1

                if total_count > 0:
                    difficulty = error_count / total_count
                    total_difficulty += difficulty
                    case_count += 1

        if case_count > 0:
            avg_difficulty = total_difficulty / case_count
            patient_difficulty[patient_id] = {
                'avg_difficulty': avg_difficulty,
                'tasks': sorted(list(tasks)),
                'task_count': len(tasks),
                'diagnostic_case_count': case_count
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
    print(f"{'Patient ID':<25} {'任务数':<8} {'诊断难度':<10} {'任务列表'}")
    print("-"*100)

    for patient_id, info in selected_patients:
        tasks_str = ','.join(map(str, info['tasks']))
        print(f"{patient_id:<25} {info['task_count']:<8} {info['avg_difficulty']:<10.2f} {tasks_str}")

    # Step 5: 加载原始数据
    print("\n5. 加载所有任务的原始数据...")
    all_task_data = {}
    for task_num in range(1, 12):
        all_task_data[task_num] = load_task_data(task_num)

    # Step 6: 导出选中患者的详细案例
    print("\n6. 导出选中患者的详细案例...")
    selected_cases = []

    for patient_id, info in selected_patients:
        patient_data = {
            'patient_id': patient_id,
            'task_count': info['task_count'],
            'avg_diagnostic_difficulty': info['avg_difficulty'],
            'tasks': {}
        }

        # task1-4: 诊断任务
        for task_num in [t for t in info['tasks'] if t <= 4]:
            task_cases = []

            for case_id in patient_cases[patient_id][task_num]:
                original_data = all_task_data[task_num].get(case_id, {})

                # 加载各模型的预测结果
                model_predictions = {}
                ground_truth = ""

                for model in MODELS:
                    key = (task_num, model)
                    if key in diagnostic_judgements and case_id in diagnostic_judgements[key]:
                        item = diagnostic_judgements[key][case_id]
                        model_predictions[model] = {
                            'prediction': item.get('prediction', ''),
                            'is_correct': item.get('is_correct', False)
                        }
                        if not ground_truth:
                            ground_truth = item.get('ground_truth', '')

                # 计算难度分数
                error_count = sum(1 for m in model_predictions.values() if not m['is_correct'])
                difficulty = error_count / len(model_predictions) if model_predictions else 0

                case_info = {
                    'case_id': case_id,
                    'type': original_data.get('type', 'unknown'),
                    'difficulty': difficulty,
                    'conversations': original_data.get('conversations', []),
                    'model_predictions': model_predictions,
                    'ground_truth': ground_truth
                }

                task_cases.append(case_info)

            patient_data['tasks'][f'task{task_num}'] = task_cases

        # task5-11: 管理任务
        for task_num in [t for t in info['tasks'] if t > 4]:
            if patient_id in all_task_data[task_num]:
                task_items = all_task_data[task_num][patient_id]

                # 加载各模型的评分
                model_scores = {}
                for model in MODELS:
                    key = (task_num, model)
                    if key in management_scores and patient_id in management_scores[key]:
                        model_scores[model] = management_scores[key][patient_id]

                patient_data['tasks'][f'task{task_num}'] = {
                    'conversations': [item.get('conversations', []) for item in task_items],
                    'model_scores': model_scores
                }

        selected_cases.append(patient_data)

    # 保存为JSON
    output_file = OUTPUT_DIR / "selected_cases_all_11_tasks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(selected_cases, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 案例详情已保存到: {output_file}")

    # 生成统计摘要
    print("\n" + "="*80)
    print("统计摘要")
    print("="*80)

    total_diagnostic_cases = sum(
        len(p['tasks'].get(f'task{i}', []))
        for p in selected_cases
        for i in range(1, 5)
    )

    total_management_tasks = sum(
        1 for p in selected_cases
        for i in range(5, 12)
        if f'task{i}' in p['tasks']
    )

    print(f"\n总患者数: {len(selected_cases)}")
    print(f"诊断任务案例数(task1-4): {total_diagnostic_cases}")
    print(f"管理任务数(task5-11): {total_management_tasks}")

    print(f"\n各任务覆盖情况:")
    for task_num in range(1, 12):
        count = sum(1 for p in selected_cases if f'task{task_num}' in p['tasks'])
        print(f"  {TASK_NAMES[task_num]} (task{task_num}): {count}/10 患者")

    print("\n" + "="*80)
    print("完成!")
    print("="*80)

if __name__ == "__main__":
    main()
