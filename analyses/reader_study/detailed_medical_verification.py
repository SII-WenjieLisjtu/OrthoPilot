#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学合理性详细核验
"""

import json
from pathlib import Path

base_dir = Path("/path/to/orthopilot/project/多中心验证/人机对比/case_study")

# 加载完整案例
with open(base_dir / "candidate_cases_for_verification.json", 'r') as f:
    candidates = json.load(f)

# 手动核验结果
verification_detailed = []

print("="*100)
print("逐案例医学合理性核验")
print("="*100)

case_num = 0
for patient in candidates:
    patient_id = patient['patient_id']

    for task_num in range(1, 5):
        task_key = f'task{task_num}'
        if task_key not in patient['tasks']:
            continue

        task_data = patient['tasks'][task_key]
        if not isinstance(task_data, list):
            continue

        for case in task_data:
            case_num += 1

            # 提取完整问题
            question = ""
            for conv in case['conversations']:
                if conv['from'] == 'human':
                    question = conv['value']

            ground_truth = case['ground_truth']

            # CHEESE完整预测
            cheese_pred = case['model_predictions'].get('bone-14B-RL-v2', {}).get('prediction', '')

            # 提取推理过程和最终答案
            if '<think>' in cheese_pred and '</think>' in cheese_pred:
                thinking = cheese_pred[cheese_pred.find('<think>'):cheese_pred.find('</think>')+8]
                final_answer = cheese_pred.split('</think>')[-1].strip()
            else:
                thinking = ""
                final_answer = cheese_pred.strip()

            # 核验
            print(f"\n{'='*100}")
            print(f"【案例 {case_num}】")
            print(f"患者ID: {patient_id}")
            print(f"任务: Task{task_num} - {case['type']}")
            print(f"Case ID: {case['case_id']}")
            print(f"\n问题:")
            print(question[:500])
            if len(question) > 500:
                print("...")

            print(f"\n标准答案: {ground_truth}")
            print(f"CHEESE最终答案: {final_answer[:200]}")

            if thinking:
                print(f"\nCHEESE推理过程（前300字符）:")
                print(thinking[:300] + "...")

            # 其他模型表现
            print(f"\n其他模型: {case['other_error_count']}错 {case['other_correct_count']}对")

            # 人工核验判断
            print(f"\n【人工核验】")
            print(f"1. 标准答案是否正确？")
            print(f"2. CHEESE答案是否合理？")
            print(f"3. 问题是否清晰？")
            print(f"\n核验结果: _________________")
            print(f"备注: _________________")

print(f"\n{'='*100}")
print(f"共 {case_num} 个案例需要核验")
print(f"{'='*100}")

# 生成核验报告
with open(base_dir / "detailed_verification_report.txt", 'w', encoding='utf-8') as f:
    f.write("医学合理性详细核验报告\n")
    f.write("="*100 + "\n\n")
    f.write(f"总案例数: {case_num}\n")
    f.write(f"核验标准:\n")
    f.write(f"1. 标准答案是否医学上正确\n")
    f.write(f"2. CHEESE的回答是否合理\n")
    f.write(f"3. 问题表述是否清晰无歧义\n\n")
    f.write("="*100 + "\n\n")

    # 需要人工逐个核验
    f.write("请逐个核验每个案例，标记通过/不通过/需修改\n\n")

print(f"\n详细核验报告已生成: detailed_verification_report.txt")
