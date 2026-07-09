#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成医生评测Word文档 - 包含所有11个任务，按患者组织
"""

import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
INPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/selected_cases_all_11_tasks.json"
OUTPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/医生评测问卷_全流程11任务.docx"

# 任务名称
TASK_NAMES = {
    'task1': '入院诊断',
    'task2': '术前诊断',
    'task3': '术后诊断',
    'task4': '出院诊断',
    'task5': '围手术期风险评估',
    'task6': '手术方案选择',
    'task7': '手术记录生成',
    'task8': '术后医嘱',
    'task9': '出院总结',
    'task10': '康复计划',
    'task11': '多学科会诊'
}

# 类型名称
TYPE_NAMES = {
    '判断': '是非判断',
    '选择': '单选题',
    '开放': '开放问答'
}

# 模型名称
MODEL_NAMES = {
    'bone-14B-RL-v2': 'CHEESE',
    'gpt-5.1': 'GPT-5.1',
    'deepseek-r1': 'DeepSeek-R1',
    'Qwen3-235B-A22B-Instruct-2507': 'Qwen3-235B',
    'kimi-k2-0905-preview': 'Kimi-K2',
    'grok-4-fast': 'Grok-4'
}

def add_styled_paragraph(doc, text, bold=False, size=12, color=None, italic=False):
    """添加带样式的段落"""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = '宋体'
    if color:
        run.font.color.rgb = color
    return para

def format_score_display(scores):
    """格式化显示评分"""
    if not scores:
        return "无评分数据"

    result = []
    for criterion, score_dict in scores.items():
        if isinstance(score_dict, dict):
            score_str = f"{criterion}: "
            for key, val in score_dict.items():
                if isinstance(val, list):
                    score_str += f"{key}={val} "
                else:
                    score_str += f"{key}={val} "
            result.append(score_str.strip())

    return " | ".join(result) if result else str(scores)

def main():
    print("="*80)
    print("生成医生评测Word文档（全流程11任务）")
    print("="*80)

    # 加载数据
    print("\n1. 加载案例数据...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        patients_data = json.load(f)

    # 创建Word文档
    print("2. 创建Word文档...")
    doc = Document()

    # 设置默认样式
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(10.5)

    # 添加标题
    title = doc.add_heading('OrthoPilot/CHEESE 人机对比评测问卷', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph('骨科全流程智能体系统 - 11任务完整评测')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 添加说明
    add_styled_paragraph(doc, '\n评测说明', bold=True, size=14)
    doc.add_paragraph('• 本问卷包含10个患者的完整临床流程案例')
    doc.add_paragraph('• 覆盖骨科全流程11个关键任务：')
    doc.add_paragraph('  - Task 1-4: 诊断任务（入院→术前→术后→出院诊断）')
    doc.add_paragraph('  - Task 5-11: 管理任务（风险评估、手术方案、手术记录、术后医嘱、出院总结、康复计划、多学科会诊）')
    doc.add_paragraph('• 每个患者按照真实临床流程顺序展示所有任务')
    doc.add_paragraph('• 诊断任务(Task1-4)为封闭式题目，管理任务(Task5-11)为开放式生成任务\n')

    # 添加图例
    add_styled_paragraph(doc, '图例说明', bold=True, size=12)
    table = doc.add_table(rows=4, cols=2)
    table.style = 'Light List Accent 1'

    table.cell(0, 0).text = '诊断任务'
    table.cell(0, 1).text = 'Task1-4：判断题/选择题/开放题，展示AI模型正确性（✓/✗）'

    table.cell(1, 0).text = '管理任务'
    table.cell(1, 1).text = 'Task5-11：开放生成任务，展示AI模型评分结果'

    table.cell(2, 0).text = '难度分数'
    table.cell(2, 1).text = '0.00-1.00，基于6个顶级AI模型的平均错误率'

    table.cell(3, 0).text = 'AI模型'
    table.cell(3, 1).text = 'CHEESE(Ours) | GPT-5.1 | DeepSeek-R1 | Qwen3-235B | Kimi-K2 | Grok-4'

    doc.add_page_break()

    # 遍历每个患者
    total_diagnostic_cases = 0
    total_management_tasks = 0

    for patient_idx, patient_data in enumerate(patients_data, 1):
        print(f"   处理患者 {patient_idx}/10: {patient_data['patient_id']}")

        # 患者标题页
        doc.add_heading(f'患者 {patient_idx}', level=1)

        # 患者信息
        info_para = doc.add_paragraph()
        info_para.add_run(f'患者ID: ').bold = True
        info_para.add_run(f"{patient_data['patient_id']}\n")
        info_para.add_run(f'覆盖任务数: ').bold = True
        info_para.add_run(f"{patient_data['task_count']} 个任务\n")
        info_para.add_run(f'诊断难度: ').bold = True
        info_para.add_run(f"{patient_data['avg_diagnostic_difficulty']:.2f}\n")

        # 按任务顺序（1-11）展示
        for task_num in range(1, 12):
            task_key = f'task{task_num}'
            if task_key not in patient_data['tasks']:
                continue

            task_data = patient_data['tasks'][task_key]
            task_name = TASK_NAMES.get(task_key, task_key)

            # 任务标题
            doc.add_heading(f'{task_name} (Task {task_num})', level=2)

            # Task 1-4: 诊断任务（封闭式）
            if task_num <= 4 and isinstance(task_data, list):
                for case in task_data:
                    total_diagnostic_cases += 1

                    type_name = TYPE_NAMES.get(case.get('type', ''), case.get('type', ''))

                    # 案例子标题
                    doc.add_heading(f'{type_name}', level=3)

                    # 案例元信息
                    meta_table = doc.add_table(rows=2, cols=2)
                    meta_table.style = 'Light Shading Accent 1'

                    meta_table.cell(0, 0).text = '难度分数'
                    difficulty_text = f"{case.get('difficulty', 0):.2f}"
                    if case.get('difficulty', 0) >= 0.8:
                        difficulty_text += " (极高难度)"
                    elif case.get('difficulty', 0) >= 0.7:
                        difficulty_text += " (高难度)"
                    meta_table.cell(0, 1).text = difficulty_text

                    meta_table.cell(1, 0).text = 'AI模型表现'
                    model_perf = case.get('model_predictions', {})
                    model_perf_str = ""
                    for model in ['bone-14B-RL-v2', 'gpt-5.1', 'deepseek-r1',
                                 'Qwen3-235B-A22B-Instruct-2507', 'kimi-k2-0905-preview', 'grok-4-fast']:
                        if model in model_perf:
                            symbol = "✓" if model_perf[model].get('is_correct', False) else "✗"
                            model_name = MODEL_NAMES.get(model, model)
                            model_perf_str += f"{model_name}:{symbol}  "
                    meta_table.cell(1, 1).text = model_perf_str.strip()

                    # 病历信息和问题
                    add_styled_paragraph(doc, '\n【病历信息及诊断问题】', bold=True, size=11,
                                       color=RGBColor(0, 0, 139))

                    conversations = case.get('conversations', [])
                    for conv in conversations:
                        if conv.get('from') == 'human':
                            question_lines = conv.get('value', '').split('\n')
                            for line in question_lines:
                                if line.strip():
                                    para = doc.add_paragraph(line)
                                    para.style.font.size = Pt(10)

                    # 答题区域
                    add_styled_paragraph(doc, '\n【您的答案】', bold=True, size=11,
                                       color=RGBColor(220, 20, 60))

                    if case.get('type') == '判断':
                        answer_para = doc.add_paragraph()
                        answer_para.add_run('您的判断：□ 是    □ 否\n\n')
                        doc.add_paragraph('_' * 80)
                    elif case.get('type') == '选择':
                        doc.add_paragraph('您选择的选项：________\n')
                        doc.add_paragraph('_' * 80)
                    else:
                        doc.add_paragraph('您的诊断结果：\n')
                        doc.add_paragraph('_' * 80)

                    # 参考答案
                    add_styled_paragraph(doc, '\n【参考答案】', bold=True, size=10,
                                       color=RGBColor(128, 128, 128), italic=True)
                    answer_para = doc.add_paragraph()
                    standard_answer = ""
                    for conv in conversations:
                        if conv.get('from') == 'gpt':
                            standard_answer = conv.get('value', '').replace('<think>\n\n</think>\n\n', '')
                            break
                    answer_run = answer_para.add_run(
                        f"标准答案: {case.get('ground_truth', '')}\n"
                        f"完整解释: {standard_answer[:200]}..."
                    )
                    answer_run.font.size = Pt(9)
                    answer_run.font.color.rgb = RGBColor(150, 150, 150)
                    answer_run.italic = True

                    doc.add_paragraph('\n' + '─' * 80 + '\n')

            # Task 5-11: 管理任务（开放式）
            elif task_num > 4 and isinstance(task_data, dict):
                total_management_tasks += 1

                # 显示任务说明
                add_styled_paragraph(doc, '【任务类型】开放式生成任务', bold=True, size=11,
                                   color=RGBColor(0, 100, 0))

                # 病历信息
                add_styled_paragraph(doc, '\n【病历信息】', bold=True, size=11,
                                   color=RGBColor(0, 0, 139))

                conversations_list = task_data.get('conversations', [])
                if conversations_list and len(conversations_list) > 0:
                    # 取第一个conversation（通常每个患者只有一个）
                    convs = conversations_list[0] if isinstance(conversations_list[0], list) else conversations_list

                    for conv in convs:
                        if conv.get('from') == 'human':
                            question_lines = conv.get('value', '').split('\n')
                            for line in question_lines:
                                if line.strip():
                                    para = doc.add_paragraph(line)
                                    para.style.font.size = Pt(10)

                # AI模型评分
                model_scores = task_data.get('model_scores', {})
                if model_scores:
                    add_styled_paragraph(doc, '\n【AI模型评分】', bold=True, size=11)

                    score_table = doc.add_table(rows=len(model_scores)+1, cols=2)
                    score_table.style = 'Light Grid Accent 1'

                    score_table.cell(0, 0).text = '模型'
                    score_table.cell(0, 1).text = '评分'

                    for idx, (model, scores) in enumerate(model_scores.items(), 1):
                        model_name = MODEL_NAMES.get(model, model)
                        score_table.cell(idx, 0).text = model_name
                        score_table.cell(idx, 1).text = format_score_display(scores)

                # 答题区域
                add_styled_paragraph(doc, '\n【您的回答】', bold=True, size=11,
                                   color=RGBColor(220, 20, 60))
                doc.add_paragraph('\n' * 3)
                doc.add_paragraph('_' * 80)
                doc.add_paragraph('\n' * 2)

                # 参考答案
                add_styled_paragraph(doc, '\n【参考答案】', bold=True, size=10,
                                   color=RGBColor(128, 128, 128), italic=True)

                if conversations_list and len(conversations_list) > 0:
                    convs = conversations_list[0] if isinstance(conversations_list[0], list) else conversations_list
                    for conv in convs:
                        if conv.get('from') == 'gpt':
                            answer_para = doc.add_paragraph()
                            answer_run = answer_para.add_run(conv.get('value', '')[:500] + '...')
                            answer_run.font.size = Pt(9)
                            answer_run.font.color.rgb = RGBColor(150, 150, 150)
                            answer_run.italic = True
                            break

                doc.add_paragraph('\n' + '═' * 80 + '\n')

        # 患者完成后分页
        if patient_idx < len(patients_data):
            doc.add_page_break()

    # 保存文档
    doc.save(OUTPUT_FILE)
    print(f"\n✓ Word文档已保存到: {OUTPUT_FILE}")

    # 统计信息
    print("\n" + "="*80)
    print("文档生成完成")
    print("="*80)

    print(f"\n患者数量: {len(patients_data)}")
    print(f"诊断任务案例数(Task1-4): {total_diagnostic_cases}")
    print(f"管理任务数(Task5-11): {total_management_tasks}")
    print(f"总案例数: {total_diagnostic_cases + total_management_tasks}")
    print(f"\n输出文件: {OUTPUT_FILE}")
    print(f"文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()
