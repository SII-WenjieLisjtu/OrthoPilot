#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成医生评测用的Word文档
"""

import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
INPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/cases_for_doctor_evaluation.json"
OUTPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/医生评测问卷.docx"

# 任务名称映射
TASK_NAMES = {
    'task1': '入院诊断',
    'task2': '术前诊断',
    'task3': '术后诊断',
    'task4': '出院诊断'
}

# 类型名称映射
TYPE_NAMES = {
    '判断': '是非判断题',
    '选择': '单选题',
    '开放': '开放问答题'
}

# 模型名称映射
MODEL_NAMES = {
    'bone-14B-RL-v2': 'CHEESE (Ours)',
    'gpt-5.1': 'GPT-5.1',
    'deepseek-r1': 'DeepSeek-R1',
    'Qwen3-235B-A22B-Instruct-2507': 'Qwen3-235B',
    'kimi-k2-0905-preview': 'Kimi-K2',
    'grok-4-fast': 'Grok-4'
}

def add_styled_paragraph(doc, text, style_name='Normal', bold=False, size=12, color=None):
    """添加带样式的段落"""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    return para

def add_table_with_borders(doc, rows, cols):
    """添加带边框的表格"""
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Light Grid Accent 1'
    return table

def main():
    print("="*80)
    print("生成医生评测Word文档")
    print("="*80)

    # 加载数据
    print("\n1. 加载案例数据...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        patients_data = json.load(f)

    # 创建Word文档
    print("2. 创建Word文档...")
    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(10.5)

    # 添加标题
    title = doc.add_heading('OrthoPilot/CHEESE 人机对比评测问卷', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 添加说明
    add_styled_paragraph(doc, '\n评测说明', bold=True, size=14)
    doc.add_paragraph('本问卷包含10个患者的120个临床诊断案例，涵盖入院诊断、术前诊断、术后诊断、出院诊断四个阶段。')
    doc.add_paragraph('每个案例已标注难度分数（0-1，越高越难）和各AI模型的预测正确性。')
    doc.add_paragraph('请仔细阅读每个案例的病历信息，并在答题区域填写您的诊断结果。\n')

    # 添加图例
    add_styled_paragraph(doc, '图例说明', bold=True, size=12)
    table = doc.add_table(rows=4, cols=2)
    table.style = 'Light List Accent 1'

    table.cell(0, 0).text = '难度分数'
    table.cell(0, 1).text = '0.00-1.00，表示该案例在6个顶级AI模型中的平均错误率'

    table.cell(1, 0).text = '✓'
    table.cell(1, 1).text = '模型预测正确'

    table.cell(2, 0).text = '✗'
    table.cell(2, 1).text = '模型预测错误'

    table.cell(3, 0).text = '标准答案'
    table.cell(3, 1).text = '来自真实电子病历系统的诊断结果（已脱敏）'

    doc.add_page_break()

    # 遍历每个患者
    for patient_idx, patient_data in enumerate(patients_data, 1):
        print(f"   处理患者 {patient_idx}/10: {patient_data['patient_id']}")

        # 患者标题
        doc.add_heading(f'患者 {patient_idx}: {patient_data["patient_id"]}', level=1)
        add_styled_paragraph(doc, f'共 {len(patient_data["cases"])} 个案例\n', size=10, color=RGBColor(128, 128, 128))

        # 遍历每个案例
        for case_idx, case in enumerate(patient_data['cases'], 1):
            # 案例标题
            task_name = TASK_NAMES.get(case['task'], case['task'])
            type_name = TYPE_NAMES.get(case['type'], case['type'])

            doc.add_heading(f'案��� {patient_idx}.{case_idx}: {task_name} - {type_name}', level=2)

            # 案例信息表格
            info_table = doc.add_table(rows=3, cols=2)
            info_table.style = 'Light Shading Accent 1'

            info_table.cell(0, 0).text = 'Case ID'
            info_table.cell(0, 1).text = case['case_id']

            info_table.cell(1, 0).text = '难度分数'
            info_table.cell(1, 1).text = f"{case['difficulty']:.2f} (高难度)" if case['difficulty'] >= 0.7 else f"{case['difficulty']:.2f}"

            info_table.cell(2, 0).text = 'AI模型表现'
            model_perf_str = ""
            for model, correct in case['model_performance'].items():
                symbol = "✓" if correct else "✗"
                model_name = MODEL_NAMES.get(model, model)
                model_perf_str += f"{model_name}: {symbol}  "
            info_table.cell(2, 1).text = model_perf_str

            # 问题
            add_styled_paragraph(doc, '\n病历信息及问题：', bold=True, size=11)
            question_para = doc.add_paragraph(case['question'])
            question_para.style.font.size = Pt(10)

            # 标准答案（折叠）
            add_styled_paragraph(doc, '\n标准答案（参考）：', bold=True, size=11)
            answer_para = doc.add_paragraph()
            answer_run = answer_para.add_run(f"正确答案: {case['ground_truth']}\n完整答案: {case['standard_answer']}")
            answer_run.font.size = Pt(9)
            answer_run.font.color.rgb = RGBColor(100, 100, 100)

            # 答题区域
            add_styled_paragraph(doc, '\n您的答案：', bold=True, size=11, color=RGBColor(255, 0, 0))
            doc.add_paragraph('\n\n' + '_'*80 + '\n\n')

            # 备注区域
            add_styled_paragraph(doc, '备注（可选）：', bold=True, size=10, color=RGBColor(100, 100, 100))
            doc.add_paragraph('\n' + '_'*80 + '\n')

            # 分隔线
            doc.add_paragraph('─' * 80)

        # 每个患者后分页
        if patient_idx < len(patients_data):
            doc.add_page_break()

    # 保存文档
    doc.save(OUTPUT_FILE)
    print(f"\n✓ Word文档已保存到: {OUTPUT_FILE}")

    # 生成统计信息
    print("\n" + "="*80)
    print("文档生成完成")
    print("="*80)
    print(f"\n患者数量: {len(patients_data)}")
    print(f"案例总数: {sum(len(p['cases']) for p in patients_data)}")
    print(f"输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
