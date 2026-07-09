# -*- coding: utf-8 -*-
"""
配置文件
"""

import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
EVALUATIONS_DIR = os.path.join(DATA_DIR, "evaluations")

# 模型列表
MODELS = [
    "bone-14B-v4",
    "deepseek-r1-0528-ep",
    "medgemma-27b-text-it",
    "gpt-5-high"
]

# 任务信息
TASKS = {
    5: {"name": "围手术期评估", "description": "判断患者能否进行手术", "name_en": "Perioperative assessment"},
    6: {"name": "手术规划", "description": "预测手术操作步骤", "name_en": "Surgical planning"},
    7: {"name": "术前医嘱", "description": "预测术前医嘱内容", "name_en": "Preoperative orders"},
    8: {"name": "术后医嘱", "description": "预测术后医嘱内容", "name_en": "Postoperative orders"},
    9: {"name": "出院总结", "description": "生成出院总结文书", "name_en": "Discharge summary"},
    10: {"name": "康复规划", "description": "康复科会诊评估建议", "name_en": "Rehabilitation planning"},
    11: {"name": "多学科会诊", "description": "其他科室会诊意见", "name_en": "Multidisciplinary consultation"}
}

# 评分维度（中文）
RATING_DIMENSIONS = {
    "accuracy": "医学准确性",
    "completeness": "内容完整性",
    "safety": "临床安全性",
    "actionability": "可操作性",
    "clarity": "表述清晰度"
}

# 评分维度（英文）
RATING_DIMENSIONS_EN = {
    "accuracy": "Accuracy",
    "completeness": "Completeness",
    "safety": "Safety",
    "actionability": "Actionability",
    "clarity": "Clarity"
}

# 模型名称简化（英文）
MODEL_LABELS_EN = {
    "bone-14B-v4": "CHEESE",
    "gpt-5-high": "GPT-5",
    "medgemma-27b-text-it": "MedGemma-27B",
    "deepseek-r1-0528-ep": "DeepSeek-R1"
}

# 医生职称选项
TITLE_OPTIONS = [
    "住院医师",
    "主治医师",
    "副主任医师",
    "主任医师"
]

# 从业年限选项
EXPERIENCE_OPTIONS = [
    "<5年",
    "5-10年",
    "10-20年",
    ">20年"
]

# 医院级别选项
HOSPITAL_LEVEL_OPTIONS = [
    "三甲医院",
    "三乙医院",
    "二甲医院",
    "其他"
]

# 专科选项
SPECIALTY_OPTIONS = [
    "骨科",
    "创伤骨科",
    "脊柱外科",
    "关节外科",
    "康复科",
    "麻醉科",
    "内科",
    "其他"
]
