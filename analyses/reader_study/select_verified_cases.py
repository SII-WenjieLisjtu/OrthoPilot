#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
挑选高质量的CHEESE优势案例
标准：
1. CHEESE做对
2. 其他模型中有2-4个做错（避免全错的可疑样本）
3. 输出案例供人工核验
"""

import json
from collections import defaultdict
from pathlib import Path

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
TEST_FINAL_DIR = BASE_DIR / "gen_validation/test_final"
META_DIR = BASE_DIR / "gen_validation/meta/subset"
OUTPUT_DIR = BASE_DIR / "project/多中心验证/人机对比/case_study"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 任务名称
TASK_NAMES = {
    1: '入院诊断', 2: '术前诊断', 3: '术后诊断', 4: '出院诊断',
    5: '围手术期风险评估', 6: '手术方案选择', 7: '手术记录生成',
    8: '术后医嘱', 9: '出院总结', 10: '康复计划', 11: '多学科会诊'
}

# 模型列表
CHEESE_MODEL = "bone-14B-RL-v2"
OTHER_MODELS = ["gpt-5.1", "deepseek-r1", "Qwen3-235B-A22B-Instruct-2507",
                "kimi-k2-0905-preview", "grok-4-fast"]

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
        return {}

    with open(task_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if task_num <= 4:
        return {item['id']: item for item in data}
    else:
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

            all_judgements[(task_num, model)] = {item['id']: item for item in data}

    return all_judgements

def load_management_scores(task_nums, models):
    """加载task5-11的评测分数"""
    print("\n预加载管理任务(task5-11)评测结果...")
    all_scores = {}

    for task_num in task_nums:
        for model in models:
            score_files = list(META_DIR.glob(f"task{task_num}_scores_{model}*.json"))
            if not score_files:
                continue

            score_file = score_files[0]
            print(f"   加载 task{task_num} - {model}...")

            with open(score_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            all_scores[(task_num, model)] = {item['patient_id']: item['scores'] for item in data}

    return all_scores

def calculate_cheese_advantage(case_id, task_num, diagnostic_judgements):
    """
    计算CHEESE的优势分数
    返回：(cheese_correct, other_error_count, other_correct_count)
    """
    # 检查CHEESE是否正确
    cheese_key = (task_num, CHEESE_MODEL)
    if cheese_key not in diagnostic_judgements or case_id not in diagnostic_judgements[cheese_key]:
        return False, 0, 0

    cheese_correct = diagnostic_judgements[cheese_key][case_id].get('is_correct', False)

    if not cheese_correct:
        return False, 0, 0

    # 统计其他模型的错误数和正确数
    other_error_count = 0
    other_correct_count = 0

    for model in OTHER_MODELS:
        key = (task_num, model)
        if key in diagnostic_judgements and case_id in diagnostic_judgements[key]:
            if not diagnostic_judgements[key][case_id].get('is_correct', False):
                other_error_count += 1
            else:
                other_correct_count += 1

    return cheese_correct, other_error_count, other_correct_count

def main():
    print("="*80)
    print("挑选高质量CHEESE优势案例")
    print("标准：CHEESE做对 + 其他2-4个模型做错（避免全错的可疑样本）")
    print("="*80)

    diagnostic_tasks = list(range(1, 5))
    management_tasks = list(range(5, 12))

    # 预加载数据
    all_models = [CHEESE_MODEL] + OTHER_MODELS
    diagnostic_judgements = load_diagnostic_judgements(diagnostic_tasks, all_models)
    management_scores = load_management_scores(management_tasks, all_models)

    # Step 1: 找出CHEESE优势案例（避免可疑样本）
    print("\n1. 寻找高质量CHEESE优势案例...")
    cheese_advantage_cases = defaultdict(lambda: defaultdict(list))
    patient_tasks = defaultdict(set)

    for task_num in diagnostic_tasks:
        print(f"   分析 task{task_num}...")
        cheese_key = (task_num, CHEESE_MODEL)
        if cheese_key not in diagnostic_judgements:
            continue

        for case_id in diagnostic_judgements[cheese_key].keys():
            cheese_correct, other_error_count, other_correct_count = calculate_cheese_advantage(
                case_id, task_num, diagnostic_judgements
            )

            # 新标准：CHEESE做对 且 其他模型中有2-3个做错（有2-3个做对）
            # 这样避免其他模型几乎全错的可疑样本
            if cheese_correct and 2 <= other_error_count <= 3 and other_correct_count >= 2:
                patient_id = extract_patient_id(case_id)
                if patient_id:
                    cheese_advantage_cases[patient_id][task_num].append({
                        'case_id': case_id,
                        'other_error_count': other_error_count,
                        'other_correct_count': other_correct_count,
                        'advantage_score': other_error_count - other_correct_count  # 优势分数
                    })
                    patient_tasks[patient_id].add(task_num)

    print(f"\n   找到 {len(cheese_advantage_cases)} 个患者有高质量CHEESE优势案例")

    # Step 2: 添加管理任务覆盖信息
    print("\n2. 添加管理任务覆盖信息...")
    for task_num in management_tasks:
        cheese_key = (task_num, CHEESE_MODEL)
        if cheese_key not in management_scores:
            continue

        for patient_id in management_scores[cheese_key].keys():
            if patient_id in patient_tasks:
                patient_tasks[patient_id].add(task_num)

    # Step 3: 计算每个患者的综合得分
    print("\n3. 计算患者综合得分...")
    patient_scores = {}

    for patient_id, tasks in patient_tasks.items():
        if len(tasks) < 8:  # 至少覆盖8个任务
            continue

        # 统计诊断任务上CHEESE的优势
        total_advantage = 0
        total_cases = 0

        for task_num in [t for t in tasks if t <= 4]:
            if task_num in cheese_advantage_cases[patient_id]:
                for case in cheese_advantage_cases[patient_id][task_num]:
                    total_advantage += case['advantage_score']
                    total_cases += 1

        if total_cases > 0:
            avg_advantage = total_advantage / total_cases
            patient_scores[patient_id] = {
                'avg_advantage': avg_advantage,
                'total_advantage': total_advantage,
                'task_count': len(tasks),
                'diagnostic_cases': total_cases,
                'tasks': sorted(list(tasks))
            }

    # Step 4: 选择top 15患者（多选一些，供人工筛选）
    print("\n4. 选择top 15患者供人工核验...")
    sorted_patients = sorted(
        patient_scores.items(),
        key=lambda x: (x[1]['avg_advantage'], x[1]['task_count']),
        reverse=True
    )

    # 选择15个，最终人工核验后保留10个
    selected_patients = sorted_patients[:15]

    print(f"\n选中的15个候选患者（需人工核验）:")
    print(f"{'Patient ID':<25} {'任务数':<8} {'案例数':<8} {'平均优势':<12} {'任务列表'}")
    print("-"*100)

    for patient_id, info in selected_patients:
        tasks_str = ','.join(map(str, info['tasks']))
        print(f"{patient_id:<25} {info['task_count']:<8} {info['diagnostic_cases']:<8} "
              f"{info['avg_advantage']:<12.2f} {tasks_str}")

    # Step 5: 加载原始数据
    print("\n5. 加载所有任务的原始数据...")
    all_task_data = {}
    for task_num in range(1, 12):
        all_task_data[task_num] = load_task_data(task_num)

    # Step 6: 导出详细案例供人工核验
    print("\n6. 导出详细案例供人工核验...")
    selected_cases = []
    verification_report = []  # 用于生成核验报告

    for patient_id, info in selected_patients:
        patient_data = {
            'patient_id': patient_id,
            'task_count': info['task_count'],
            'avg_cheese_advantage': info['avg_advantage'],
            'tasks': {}
        }

        # task1-4: 只包含高质量CHEESE优势案例
        for task_num in [t for t in info['tasks'] if t <= 4]:
            if task_num not in cheese_advantage_cases[patient_id]:
                continue

            task_cases = []
            for case_info in cheese_advantage_cases[patient_id][task_num]:
                case_id = case_info['case_id']
                original_data = all_task_data[task_num].get(case_id, {})

                # 加载各模型的预测结果
                model_predictions = {}
                ground_truth = ""

                for model in all_models:
                    key = (task_num, model)
                    if key in diagnostic_judgements and case_id in diagnostic_judgements[key]:
                        item = diagnostic_judgements[key][case_id]
                        model_predictions[model] = {
                            'prediction': item.get('prediction', ''),
                            'is_correct': item.get('is_correct', False)
                        }
                        if not ground_truth:
                            ground_truth = item.get('ground_truth', '')

                # 提取问题和答案供人工核验
                conversations = original_data.get('conversations', [])
                question = ""
                for conv in conversations:
                    if conv.get('from') == 'human':
                        question = conv.get('value', '')
                        break

                # 添加到核验报告
                verification_report.append({
                    'patient_id': patient_id,
                    'task': TASK_NAMES[task_num],
                    'case_id': case_id,
                    'type': original_data.get('type', ''),
                    'question': question[:200] + '...' if len(question) > 200 else question,
                    'ground_truth': ground_truth,
                    'cheese_prediction': model_predictions.get(CHEESE_MODEL, {}).get('prediction', ''),
                    'other_error_count': case_info['other_error_count'],
                    'other_correct_count': case_info['other_correct_count'],
                    'model_results': {
                        model: '✓' if pred.get('is_correct', False) else '✗'
                        for model, pred in model_predictions.items()
                    }
                })

                case_data = {
                    'case_id': case_id,
                    'type': original_data.get('type', 'unknown'),
                    'advantage_score': case_info['advantage_score'],
                    'other_error_count': case_info['other_error_count'],
                    'other_correct_count': case_info['other_correct_count'],
                    'conversations': conversations,
                    'model_predictions': model_predictions,
                    'ground_truth': ground_truth
                }

                task_cases.append(case_data)

            patient_data['tasks'][f'task{task_num}'] = task_cases

        # task5-11: 管理任务
        for task_num in [t for t in info['tasks'] if t > 4]:
            if patient_id in all_task_data[task_num]:
                task_items = all_task_data[task_num][patient_id]

                # 加载各模型的评分
                model_scores = {}
                for model in all_models:
                    key = (task_num, model)
                    if key in management_scores and patient_id in management_scores[key]:
                        model_scores[model] = management_scores[key][patient_id]

                patient_data['tasks'][f'task{task_num}'] = {
                    'conversations': [item.get('conversations', []) for item in task_items],
                    'model_scores': model_scores
                }

        selected_cases.append(patient_data)

    # 保存JSON数据
    output_file = OUTPUT_DIR / "candidate_cases_for_verification.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(selected_cases, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 候选案例已保存到: {output_file}")

    # 生成人工核验报告
    verification_file = OUTPUT_DIR / "verification_report.txt"
    with open(verification_file, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("CHEESE优势案例 - 人工核验报告\n")
        f.write("="*100 + "\n\n")
        f.write(f"总候选患者数: {len(selected_patients)}\n")
        f.write(f"总候选案例数: {len(verification_report)}\n\n")
        f.write("核验标准：\n")
        f.write("1. 标准答案是否正确？\n")
        f.write("2. CHEESE的回答是否合理？\n")
        f.write("3. 其他模型的错误是否可以理解？\n")
        f.write("4. 题目是否有歧义？\n\n")
        f.write("="*100 + "\n\n")

        for idx, item in enumerate(verification_report, 1):
            f.write(f"案例 {idx}\n")
            f.write("-"*100 + "\n")
            f.write(f"患者ID: {item['patient_id']}\n")
            f.write(f"任务: {item['task']}\n")
            f.write(f"类型: {item['type']}\n")
            f.write(f"Case ID: {item['case_id']}\n\n")

            f.write(f"问题:\n{item['question']}\n\n")

            f.write(f"标准答案: {item['ground_truth']}\n\n")

            f.write(f"AI模型表现:\n")
            for model, result in item['model_results'].items():
                f.write(f"  {model}: {result}\n")
            f.write(f"  (CHEESE对, {item['other_error_count']}个错, {item['other_correct_count']}个对)\n\n")

            f.write(f"CHEESE预测:\n{item['cheese_prediction'][:300]}...\n\n")

            f.write("核验结果: [ ] 通过  [ ] 不通过  [ ] 需修改\n")
            f.write("核验意见: _______________________________________\n\n")
            f.write("="*100 + "\n\n")

    print(f"✓ 核验报告已保存到: {verification_file}")

    # 统计摘要
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

    print(f"\n候选患者数: {len(selected_cases)} (建议人工核验后保留10个)")
    print(f"候选诊断案例数(task1-4): {total_diagnostic_cases}")
    print(f"管理任务数(task5-11): {total_management_tasks}")

    print(f"\n各任务覆盖情况:")
    for task_num in range(1, 12):
        count = sum(1 for p in selected_cases if f'task{task_num}' in p['tasks'])
        print(f"  {TASK_NAMES[task_num]} (task{task_num}): {count}/15 患者")

    # 分析CHEESE优势分布
    print(f"\nCHEESE优势分布（诊断任务）:")
    print(f"{'任务':<15} {'平均错误数':<12} {'平均正确数':<12}")
    print("-"*40)
    for task_num in range(1, 5):
        total_error = sum(
            case['other_error_count']
            for p in selected_cases
            if f'task{task_num}' in p['tasks']
            for case in p['tasks'].get(f'task{task_num}', [])
        )
        total_correct = sum(
            case['other_correct_count']
            for p in selected_cases
            if f'task{task_num}' in p['tasks']
            for case in p['tasks'].get(f'task{task_num}', [])
        )
        case_count = sum(
            len(p['tasks'].get(f'task{task_num}', []))
            for p in selected_cases
        )
        if case_count > 0:
            print(f"{TASK_NAMES[task_num]:<15} {total_error/case_count:<12.1f} {total_correct/case_count:<12.1f}")

    print("\n" + "="*80)
    print("下一步：人工核验")
    print("="*80)
    print(f"\n1. 查看核验报告: {verification_file}")
    print(f"2. 逐个核验案例，标记是否通过")
    print(f"3. 从15个候选患者中选择10个质量最高的")
    print(f"4. 生成最终的医生评测问卷")

if __name__ == "__main__":
    main()
