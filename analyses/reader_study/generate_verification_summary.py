#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速浏览核验报告，生成核验通过的案例列表
"""

import json
from pathlib import Path

BASE_DIR = Path("/path/to/orthopilot/project/多中心验证/人机对比/case_study")
INPUT_FILE = BASE_DIR / "candidate_cases_for_verification.json"
OUTPUT_FILE = BASE_DIR / "verification_summary.md"

# 加载候选案例
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    candidates = json.load(f)

# 生成快速浏览摘要
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("# CHEESE优势案例 - 快速核验摘要\n\n")
    f.write(f"**总患者数**: {len(candidates)}\n\n")

    total_diagnostic = 0
    total_management = 0

    for patient in candidates:
        for task_key in patient['tasks']:
            task_data = patient['tasks'][task_key]
            if isinstance(task_data, list):
                total_diagnostic += len(task_data)
            else:
                total_management += 1

    f.write(f"**诊断案例数**: {total_diagnostic}\n")
    f.write(f"**管理任务数**: {total_management}\n")
    f.write(f"**总案例数**: {total_diagnostic + total_management}\n\n")

    f.write("---\n\n")
    f.write("## 诊断案例快速浏览\n\n")
    f.write("查看标准答案、CHEESE预测和AI模型表现，判断案例质量。\n\n")

    case_num = 1
    for patient_idx, patient in enumerate(candidates, 1):
        patient_id = patient['patient_id']

        # 只展示诊断任务
        for task_num in range(1, 5):
            task_key = f'task{task_num}'
            if task_key not in patient['tasks']:
                continue

            task_data = patient['tasks'][task_key]
            if not isinstance(task_data, list):
                continue

            for case in task_data:
                f.write(f"### 案例 {case_num}\n\n")
                f.write(f"**患者ID**: {patient_id}  \n")
                f.write(f"**任务**: Task {task_num}  \n")
                f.write(f"**类型**: {case['type']}  \n")
                f.write(f"**Case ID**: {case['case_id']}  \n\n")

                # AI模型表现
                f.write("**AI模型表现**:\n")
                model_perf = case['model_predictions']
                for model in ['bone-14B-RL-v2', 'gpt-5.1', 'deepseek-r1',
                             'Qwen3-235B-A22B-Instruct-2507', 'kimi-k2-0905-preview', 'grok-4-fast']:
                    if model in model_perf:
                        symbol = "✓" if model_perf[model]['is_correct'] else "✗"
                        f.write(f"- {model}: {symbol}\n")

                f.write(f"\n**统计**: CHEESE✓ | {case['other_error_count']}个错 | {case['other_correct_count']}个对\n\n")

                # 问题摘要
                question = ""
                cheese_answer = ""
                for conv in case['conversations']:
                    if conv['from'] == 'human':
                        question = conv['value']
                    elif conv['from'] == 'gpt':
                        cheese_answer = conv['value']

                # 提取关键信息
                question_short = question[:200] + '...' if len(question) > 200 else question
                f.write(f"**问题摘要**: {question_short}\n\n")

                f.write(f"**标准答案**: `{case['ground_truth']}`\n\n")

                # CHEESE答案（去除think）
                cheese_clean = cheese_answer.replace('<think>', '').replace('</think>', '').strip()
                cheese_short = cheese_clean[:150] + '...' if len(cheese_clean) > 150 else cheese_clean
                f.write(f"**CHEESE回答**: {cheese_short}\n\n")

                # 核验选项
                f.write("**核验**: [ ] 通过 [ ] 不通过 [ ] 需修改\n\n")
                f.write("---\n\n")

                case_num += 1

    f.write("\n## 核验说��\n\n")
    f.write("1. **通过**: 案例质量好，标准答案正确，CHEESE回答合理\n")
    f.write("2. **不通过**: 案例有问题，剔除\n")
    f.write("3. **需修改**: 可以使用但需修改标准答案或说明\n\n")

    f.write("**核验完成后**：\n")
    f.write("1. 统计通过的案例数量\n")
    f.write("2. 选择10个患者（确保覆盖足够案例）\n")
    f.write("3. 运行生成脚本创建最终Word文档\n")

print(f"✓ 快速核验摘要已生成: {OUTPUT_FILE}")
print(f"\n包含 {total_diagnostic} 个诊断案例需要核验")
print(f"\n请编辑该文件，在【核验】处标记：")
print(f"  [x] 通过")
print(f"  [ ] 不通过")
print(f"  [?] 需修改")
