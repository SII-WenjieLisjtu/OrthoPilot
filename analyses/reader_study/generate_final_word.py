#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成医生评测Word文档 - 最终版（已核验质量），使用宋体字体
"""

import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
INPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/final_selected_cases.json"
OUTPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/医生评测问卷_最终版.docx"

# 任务名称
TASK_NAMES = {
    'task1': '入院诊断', 'task2': '术前诊断', 'task3': '术后诊断', 'task4': '出院诊断',
    'task5': '围手术期风险评估', 'task6': '手术方案选择', 'task7': '手术记录生成',
    'task8': '术后医嘱', 'task9': '出院总结', 'task10': '康复计划', 'task11': '多学科会诊'
}

# 类型名称
TYPE_NAMES = {'判断': '是非判断', '选择': '单选题', '开放': '开放问答'}

# 模型名称
MODEL_NAMES = {
    'bone-14B-RL-v2': 'CHEESE',
    'gpt-5.1': 'GPT-5.1',
    'deepseek-r1': 'DeepSeek-R1',
    'Qwen3-235B-A22B-Instruct-2507': 'Qwen3-235B',
    'kimi-k2-0905-preview': 'Kimi-K2',
    'grok-4-fast': 'Grok-4'
}

def set_font_songti(run):
    """设置字体为宋体（中英文通用）"""
    run.font.name = '宋体'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')  # 设置中文字体
    run._element.rPr.rFonts.set(qn('w:ascii'), '宋体')     # 设置英文字体
    run._element.rPr.rFonts.set(qn('w:hAnsi'), '宋体')     # 设置西文字体

def add_paragraph_songti(doc, text, bold=False, size=12, color=None, italic=False, alignment=None):
    """添加宋体段落"""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    set_font_songti(run)
    if color:
        run.font.color.rgb = color
    if alignment:
        para.alignment = alignment
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
    print("生成医生评测Word文档（CHEESE优势展示，宋体字体）")
    print("="*80)

    # 加载数据
    print("\n1. 加载案例数据...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        patients_data = json.load(f)

    # 创建Word文档
    print("2. 创建Word文档...")
    doc = Document()

    # 设置全局默认样式为宋体
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    style._element.rPr.rFonts.set(qn('w:ascii'), '宋体')
    style._element.rPr.rFonts.set(qn('w:hAnsi'), '宋体')
    style.font.size = Pt(10.5)

    # 添加标题
    title_para = add_paragraph_songti(doc, 'OrthoPilot/CHEESE 人机对比评测问卷',
                                      bold=True, size=18, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    subtitle_para = add_paragraph_songti(doc, 'CHEESE模型优势案例展示',
                                         bold=True, size=14, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    add_paragraph_songti(doc, '', size=10)  # 空行

    # 添加说明
    add_paragraph_songti(doc, '评测说明', bold=True, size=14)
    add_paragraph_songti(doc, '• 本问卷展示CHEESE模型在骨科全流程任务中的优势案例', size=10.5)
    add_paragraph_songti(doc, '• 所有诊断案例均为：CHEESE预测正确 + 其他5个顶级模型全部预测错误', size=10.5)
    add_paragraph_songti(doc, '• 覆盖10个患者，75个任务案例', size=10.5)
    add_paragraph_songti(doc, '  - 诊断任务(Task1-4): 35个CHEESE优势案例', size=10.5)
    add_paragraph_songti(doc, '  - 管理任务(Task5-11): 40个开放式生成任务', size=10.5)
    add_paragraph_songti(doc, '• 按患者组织，展现完整临床流程\n', size=10.5)

    # 添加图例
    add_paragraph_songti(doc, '图例说明', bold=True, size=12)

    table = doc.add_table(rows=4, cols=2)
    table.style = 'Light List Accent 1'

    # 设置表格字体为宋体
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_font_songti(run)

    cells = [
        ('诊断任务', 'Task1-4：展示CHEESE✓ vs 其他5个模型✗的对比'),
        ('管理任务', 'Task5-11：开放生成任务，展示AI模型评分结果'),
        ('优势分数', '5.0 = CHEESE做对，其他5个模型全部做错'),
        ('AI模型', 'CHEESE(Ours) | GPT-5.1 | DeepSeek-R1 | Qwen3-235B | Kimi-K2 | Grok-4')
    ]

    for i, (key, val) in enumerate(cells):
        cell0 = table.rows[i].cells[0]
        cell1 = table.rows[i].cells[1]
        cell0.text = key
        cell1.text = val
        # 设置表格单元格字体
        for para in cell0.paragraphs:
            for run in para.runs:
                set_font_songti(run)
        for para in cell1.paragraphs:
            for run in para.runs:
                set_font_songti(run)

    doc.add_page_break()

    # 遍历每个患者
    total_diagnostic_cases = 0
    total_management_tasks = 0

    for patient_idx, patient_data in enumerate(patients_data, 1):
        print(f"   处理患者 {patient_idx}/10: {patient_data['patient_id']}")

        # 患者标题
        add_paragraph_songti(doc, f'患者 {patient_idx}', bold=True, size=16)

        # 患者信息
        info_text = (
            f"患者ID: {patient_data['patient_id']}\n"
            f"覆盖任务数: {patient_data['task_count']} 个任务\n"
            f"CHEESE平均优势: {patient_data['avg_cheese_advantage']:.1f} 个其他模型出错"
        )
        add_paragraph_songti(doc, info_text, size=10.5)
        add_paragraph_songti(doc, '─' * 80, size=10)

        # 按任务顺序展示
        for task_num in range(1, 12):
            task_key = f'task{task_num}'
            if task_key not in patient_data['tasks']:
                continue

            task_data = patient_data['tasks'][task_key]
            task_name = TASK_NAMES.get(task_key, task_key)

            # 任务标题
            add_paragraph_songti(doc, f'{task_name} (Task {task_num})', bold=True, size=14)

            # Task 1-4: 诊断任务
            if task_num <= 4 and isinstance(task_data, list):
                for case in task_data:
                    total_diagnostic_cases += 1

                    type_name = TYPE_NAMES.get(case.get('type', ''), case.get('type', ''))

                    # 案例子标题
                    add_paragraph_songti(doc, f'{type_name}', bold=True, size=12)

                    # 案例元信息表格
                    meta_table = doc.add_table(rows=3, cols=2)
                    meta_table.style = 'Light Shading Accent 1'

                    # CHEESE优势分数
                    meta_table.rows[0].cells[0].text = 'CHEESE优势'
                    advantage_score = case.get('advantage_score', 0)
                    meta_table.rows[0].cells[1].text = f"{advantage_score}/5 个其他模型出错"

                    # AI模型对比
                    meta_table.rows[1].cells[0].text = 'AI模型表现'
                    model_perf = case.get('model_predictions', {})
                    model_perf_str = ""
                    for model in ['bone-14B-RL-v2', 'gpt-5.1', 'deepseek-r1',
                                 'Qwen3-235B-A22B-Instruct-2507', 'kimi-k2-0905-preview', 'grok-4-fast']:
                        if model in model_perf:
                            symbol = "✓" if model_perf[model].get('is_correct', False) else "✗"
                            model_name = MODEL_NAMES.get(model, model)
                            model_perf_str += f"{model_name}:{symbol}  "
                    meta_table.rows[1].cells[1].text = model_perf_str.strip()

                    # 标准答案
                    meta_table.rows[2].cells[0].text = '标准答案'
                    meta_table.rows[2].cells[1].text = case.get('ground_truth', '')

                    # 设置表格字体
                    for row in meta_table.rows:
                        for cell in row.cells:
                            for para in cell.paragraphs:
                                for run in para.runs:
                                    set_font_songti(run)

                    # 病历信息和问题
                    add_paragraph_songti(doc, '\n【病历信息及诊断问题】', bold=True, size=11,
                                        color=RGBColor(0, 0, 139))

                    conversations = case.get('conversations', [])
                    for conv in conversations:
                        if conv.get('from') == 'human':
                            question_lines = conv.get('value', '').split('\n')
                            for line in question_lines:
                                if line.strip():
                                    add_paragraph_songti(doc, line, size=10)

                    # 答题区域
                    add_paragraph_songti(doc, '\n【您的答案】', bold=True, size=11,
                                        color=RGBColor(220, 20, 60))

                    if case.get('type') == '判断':
                        add_paragraph_songti(doc, '您的判断：□ 是    □ 否\n', size=10.5)
                        add_paragraph_songti(doc, '_' * 80, size=10)
                    elif case.get('type') == '选择':
                        add_paragraph_songti(doc, '您选择的选项：________\n', size=10.5)
                        add_paragraph_songti(doc, '_' * 80, size=10)
                    else:
                        add_paragraph_songti(doc, '您的诊断结果：\n', size=10.5)
                        add_paragraph_songti(doc, '_' * 80, size=10)

                    # 标准答案
                    add_paragraph_songti(doc, '\n【标准答案】', bold=True, size=10,
                                        color=RGBColor(128, 128, 128))
                    add_paragraph_songti(doc, case.get('ground_truth', ''), size=10,
                                        color=RGBColor(100, 100, 100))

                    # CHEESE模型的完整回答
                    add_paragraph_songti(doc, '\n【CHEESE模型的回答】', bold=True, size=10,
                                        color=RGBColor(0, 128, 0))

                    cheese_pred = model_perf.get('bone-14B-RL-v2', {}).get('prediction', '')

                    # 分离思考过程和最终答案
                    if '<think>' in cheese_pred and '</think>' in cheese_pred:
                        # 提取思考过程
                        think_start = cheese_pred.find('<think>')
                        think_end = cheese_pred.find('</think>') + 8
                        thinking = cheese_pred[think_start:think_end]
                        final_answer = cheese_pred[think_end:].strip()

                        # 展示思考过程（可选，用浅色）
                        add_paragraph_songti(doc, '推理过程：', bold=True, size=9,
                                           color=RGBColor(150, 150, 150))
                        thinking_clean = thinking.replace('<think>', '').replace('</think>', '').strip()
                        add_paragraph_songti(doc, thinking_clean, size=9,
                                           color=RGBColor(150, 150, 150), italic=True)

                        # 展示最终答案（重点突出）
                        add_paragraph_songti(doc, '\nCHEESE的最终答案：', bold=True, size=10,
                                           color=RGBColor(0, 128, 0))
                        add_paragraph_songti(doc, final_answer, size=10,
                                           color=RGBColor(0, 100, 0))
                    else:
                        # 没有think标签，直接展示全部内容
                        add_paragraph_songti(doc, cheese_pred, size=10,
                                           color=RGBColor(0, 100, 0))

                    add_paragraph_songti(doc, '\n' + '─' * 80 + '\n', size=10)

            # Task 5-11: 管理任务
            elif task_num > 4 and isinstance(task_data, dict):
                total_management_tasks += 1

                # 任务类型
                add_paragraph_songti(doc, '【任务类型】开放式生成任务', bold=True, size=11,
                                    color=RGBColor(0, 100, 0))

                # 病历信息
                add_paragraph_songti(doc, '\n【病历信息】', bold=True, size=11,
                                    color=RGBColor(0, 0, 139))

                conversations_list = task_data.get('conversations', [])
                if conversations_list and len(conversations_list) > 0:
                    convs = conversations_list[0] if isinstance(conversations_list[0], list) else conversations_list

                    for conv in convs:
                        if conv.get('from') == 'human':
                            question_lines = conv.get('value', '').split('\n')
                            for line in question_lines:
                                if line.strip():
                                    add_paragraph_songti(doc, line, size=10)

                # AI模型评分
                model_scores = task_data.get('model_scores', {})
                if model_scores:
                    add_paragraph_songti(doc, '\n【AI模型评分】', bold=True, size=11)

                    score_table = doc.add_table(rows=len(model_scores)+1, cols=2)
                    score_table.style = 'Light Grid Accent 1'

                    score_table.rows[0].cells[0].text = '模型'
                    score_table.rows[0].cells[1].text = '评分'

                    for idx, (model, scores) in enumerate(model_scores.items(), 1):
                        model_name = MODEL_NAMES.get(model, model)
                        score_table.rows[idx].cells[0].text = model_name
                        score_table.rows[idx].cells[1].text = format_score_display(scores)

                    # 设置表格字体
                    for row in score_table.rows:
                        for cell in row.cells:
                            for para in cell.paragraphs:
                                for run in para.runs:
                                    set_font_songti(run)

                # 答题区域
                add_paragraph_songti(doc, '\n【您的回答】', bold=True, size=11,
                                    color=RGBColor(220, 20, 60))
                add_paragraph_songti(doc, '\n\n\n', size=10)
                add_paragraph_songti(doc, '_' * 80, size=10)
                add_paragraph_songti(doc, '\n\n', size=10)

                # CHEESE模型的完整回答
                add_paragraph_songti(doc, '\n【CHEESE模型的回答】', bold=True, size=11,
                                    color=RGBColor(0, 128, 0))

                if conversations_list and len(conversations_list) > 0:
                    convs = conversations_list[0] if isinstance(conversations_list[0], list) else conversations_list
                    for conv in convs:
                        if conv.get('from') == 'gpt':
                            cheese_answer = conv.get('value', '')

                            # 展示完整回答
                            add_paragraph_songti(doc, cheese_answer, size=10,
                                               color=RGBColor(0, 100, 0))
                            break

                add_paragraph_songti(doc, '\n' + '═' * 80 + '\n', size=10)

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
    print(f"CHEESE优势诊断案例数(Task1-4): {total_diagnostic_cases}")
    print(f"管理任务数(Task5-11): {total_management_tasks}")
    print(f"总案例数: {total_diagnostic_cases + total_management_tasks}")
    print(f"\n输出文件: {OUTPUT_FILE}")
    print(f"文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()
