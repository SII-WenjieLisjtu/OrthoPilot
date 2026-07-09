#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成医生评测用的Word文档 - 按患者组织
"""

import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 配置路径
BASE_DIR = Path("/path/to/orthopilot")
INPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/cases_for_doctor_evaluation.json"
OUTPUT_FILE = BASE_DIR / "project/多中心验证/人机对比/case_study/医生评测问卷_按患者.docx"

# 任务名称映射
TASK_NAMES = {
    'task1': '入院诊断',
    'task2': '术前诊断',
    'task3': '术后诊断',
    'task4': '出院诊断'
}

# 类型名称映射
TYPE_NAMES = {
    '判断': '是非判断',
    '选择': '单选题',
    '开放': '开放问答'
}

# 模型名称映射
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

def main():
    print("="*80)
    print("生成医生评测Word文档（按患者组织）")
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

    # 添加说明
    add_styled_paragraph(doc, '\n评测说明', bold=True, size=14)
    doc.add_paragraph('• 本问卷包含10个患者的120个临床诊断案例')
    doc.add_paragraph('• 每个患者包含4个诊断阶段：入院诊断→术前诊断→术后诊断→出院诊断')
    doc.add_paragraph('• 每个案例展示该患者在对应阶段的病历信息和诊断问题')
    doc.add_paragraph('• 请按照患者顺序依次作答，体验完整的诊疗流程\n')

    # 添加图例
    add_styled_paragraph(doc, '图例说明', bold=True, size=12)
    table = doc.add_table(rows=3, cols=2)
    table.style = 'Light List Accent 1'

    table.cell(0, 0).text = '✓ / ✗'
    table.cell(0, 1).text = 'AI模型预测的正确性（✓正确 ✗错误）'

    table.cell(1, 0).text = '难度分数'
    table.cell(1, 1).text = '0.00-1.00，表示6个顶级AI模型的平均错误率'

    table.cell(2, 0).text = '参考模型'
    table.cell(2, 1).text = 'CHEESE(Ours) | GPT-5.1 | DeepSeek-R1 | Qwen3-235B | Kimi-K2 | Grok-4'

    doc.add_page_break()

    # 按患者组织内容
    for patient_idx, patient_data in enumerate(patients_data, 1):
        print(f"   处理患者 {patient_idx}/10: {patient_data['patient_id']}")

        # 患者标题页
        doc.add_heading(f'患者 {patient_idx}', level=1)

        # 患者信息表
        info_para = doc.add_paragraph()
        info_para.add_run(f'患者ID: ').bold = True
        info_para.add_run(f"{patient_data['patient_id']}\n")
        info_para.add_run(f'案例数量: ').bold = True
        info_para.add_run(f"{len(patient_data['cases'])} 个\n")
        info_para.add_run(f'诊疗流程: ').bold = True
        info_para.add_run('入院诊断 → 术前诊断 → 术后诊断 → 出院诊断')

        doc.add_paragraph('─' * 80)

        # 按任务顺序组织该患者的案例
        # 先对案例按task排序
        sorted_cases = sorted(patient_data['cases'], key=lambda x: x['task'])

        # 遍历该患者的每个案例
        for case_idx, case in enumerate(sorted_cases, 1):
            task_name = TASK_NAMES.get(case['task'], case['task'])
            type_name = TYPE_NAMES.get(case['type'], case['type'])

            # 案例标题
            doc.add_heading(f'{task_name} ({type_name})', level=2)

            # 案例元信息
            meta_table = doc.add_table(rows=2, cols=2)
            meta_table.style = 'Light Shading Accent 1'

            # 第一行：难度和类型
            meta_table.cell(0, 0).text = '难度分数'
            difficulty_text = f"{case['difficulty']:.2f}"
            if case['difficulty'] >= 0.8:
                difficulty_text += " (极高难度)"
            elif case['difficulty'] >= 0.7:
                difficulty_text += " (高难度)"
            meta_table.cell(0, 1).text = difficulty_text

            # 第二行：AI模型表现
            meta_table.cell(1, 0).text = 'AI模型表现'
            model_perf_str = ""
            for model in ['bone-14B-RL-v2', 'gpt-5.1', 'deepseek-r1',
                         'Qwen3-235B-A22B-Instruct-2507', 'kimi-k2-0905-preview', 'grok-4-fast']:
                if model in case['model_performance']:
                    symbol = "✓" if case['model_performance'][model] else "✗"
                    model_name = MODEL_NAMES.get(model, model)
                    model_perf_str += f"{model_name}:{symbol}  "
            meta_table.cell(1, 1).text = model_perf_str.strip()

            # 病历信息和问题
            add_styled_paragraph(doc, '\n【病历信息及诊断问题】', bold=True, size=11,
                               color=RGBColor(0, 0, 139))

            # 处理问题文本，提取主诉、现病史等结构化信息
            question_lines = case['question'].split('\n')
            for line in question_lines:
                if line.strip():
                    para = doc.add_paragraph(line)
                    para.style.font.size = Pt(10)

            # 答题区域
            add_styled_paragraph(doc, '\n【您的答案】', bold=True, size=11,
                               color=RGBColor(220, 20, 60))

            # 根据题型提供不同的答题框
            if case['type'] == '判断':
                answer_para = doc.add_paragraph()
                answer_para.add_run('您的判断：□ 是    □ 否')
                answer_para.add_run('\n\n判断理由：\n')
                doc.add_paragraph('_' * 80)
            elif case['type'] == '选择':
                doc.add_paragraph('您选择的选项：________')
                doc.add_paragraph('\n选择理由：\n')
                doc.add_paragraph('_' * 80)
            else:  # 开放题
                doc.add_paragraph('您的诊断结果：\n')
                doc.add_paragraph('_' * 80)
                doc.add_paragraph('\n诊断依据：\n')
                doc.add_paragraph('_' * 80)

            # 标准答案（折叠显示）
            add_styled_paragraph(doc, '\n【参考答案】（评测后展开）', bold=True, size=10,
                               color=RGBColor(128, 128, 128), italic=True)

            answer_para = doc.add_paragraph()
            answer_run = answer_para.add_run(
                f"标准答案: {case['ground_truth']}\n"
                f"完整解释: {case['standard_answer'][:200]}..."
            )
            answer_run.font.size = Pt(9)
            answer_run.font.color.rgb = RGBColor(150, 150, 150)
            answer_run.italic = True

            # 备注区
            add_styled_paragraph(doc, '\n【备注】（可选）', bold=True, size=10,
                               color=RGBColor(100, 100, 100))
            doc.add_paragraph('_' * 80)

            # 案例分隔线
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

    total_cases = sum(len(p['cases']) for p in patients_data)
    print(f"\n患者数量: {len(patients_data)}")
    print(f"案例总数: {total_cases}")
    print(f"平均每患者: {total_cases / len(patients_data):.0f} 个案例")
    print(f"\n输出文件: {OUTPUT_FILE}")
    print(f"文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

    # .doc格式说明
    print("\n" + "="*80)
    print("关于文件格式")
    print("="*80)
    print("\n• 当前生成的是 .docx 格式（Word 2007+）")
    print("• 如需 .doc 格式（Word 2003），可以：")
    print("  1. 在Word中打开此文件")
    print("  2. 选择 '文件' → '另存为'")
    print("  3. 选择 'Word 97-2003 文档 (*.doc)' 格式")
    print("  4. 保存即可")

if __name__ == "__main__":
    main()
