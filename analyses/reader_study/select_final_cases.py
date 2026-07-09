#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于质量标准筛选最终案例
目标：从15个候选患者中选择8个最佳患者
"""

import json
from pathlib import Path

base_dir = Path("/path/to/orthopilot/project/多中心验证/人机对比/case_study")

# 加载候选案例
with open(base_dir / "candidate_cases_for_verification.json", 'r') as f:
    candidates = json.load(f)

print("="*80)
print("基于质量标准筛选最终案例")
print("="*80)

# 筛选标准
selected_patients = []

for patient in candidates:
    patient_id = patient['patient_id']

    # 统计该患者的诊断案例数和管理任务数
    diagnostic_count = 0
    management_count = 0

    for task_key in patient['tasks']:
        task_data = patient['tasks'][task_key]
        if isinstance(task_data, list):  # 诊断任务
            diagnostic_count += len(task_data)
        else:  # 管理任务
            management_count += 1

    # 检查CHEESE答案质量
    all_correct = True
    for task_num in range(1, 5):
        task_key = f'task{task_num}'
        if task_key in patient['tasks']:
            task_data = patient['tasks'][task_key]
            if isinstance(task_data, list):
                for case in task_data:
                    # 检查CHEESE是否预测正确
                    if not case['model_predictions']['bone-14B-RL-v2']['is_correct']:
                        all_correct = False
                        break

    # 评分
    score = 0
    if all_correct:
        score += 10  # CHEESE全部正确
    score += diagnostic_count  # 诊断案例数
    score += management_count * 0.5  # 管理任务数

    selected_patients.append({
        'patient': patient,
        'patient_id': patient_id,
        'diagnostic_count': diagnostic_count,
        'management_count': management_count,
        'all_cheese_correct': all_correct,
        'score': score
    })

# 按评分排序
selected_patients.sort(key=lambda x: x['score'], reverse=True)

# 选择top 8患者
final_patients = selected_patients[:8]

print(f"\n选中的8个最佳患者:")
print(f"{'Patient ID':<25} {'诊断案例':<10} {'管理任务':<10} {'CHEESE全对':<12} {'评分':<8}")
print("-"*80)

for item in final_patients:
    print(f"{item['patient_id']:<25} {item['diagnostic_count']:<10} "
          f"{item['management_count']:<10} {'✓' if item['all_cheese_correct'] else '✗':<12} "
          f"{item['score']:<8.1f}")

# 统计
total_diagnostic = sum(p['diagnostic_count'] for p in final_patients)
total_management = sum(p['management_count'] for p in final_patients)

print(f"\n统计摘要:")
print(f"  总患者数: 8")
print(f"  诊断案例数: {total_diagnostic}")
print(f"  管理任务数: {total_management}")
print(f"  总案例数: {total_diagnostic + total_management}")

# 保存最终选择的患者
final_cases = [p['patient'] for p in final_patients]

output_file = base_dir / "final_selected_cases.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(final_cases, f, ensure_ascii=False, indent=2)

print(f"\n✓ 最终案例已保存到: {output_file}")

# 生成任务分布
print(f"\n各任务覆盖情况:")
for task_num in range(1, 12):
    count = sum(1 for p in final_cases if f'task{task_num}' in p['tasks'])
    task_names = {
        1: '入院诊断', 2: '术前诊断', 3: '术后诊断', 4: '出院诊断',
        5: '围手术期风险评估', 6: '手术方案选择', 7: '手术记录生成',
        8: '术后医嘱', 9: '出院总结', 10: '康复计划', 11: '多学科会诊'
    }
    print(f"  Task{task_num} {task_names[task_num]}: {count}/8 患者")

print("\n"+"="*80)
print("下一步：生成最终Word文档（宋体，含完整CHEESE回答）")
print("="*80)
