#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据准备脚本：从result目录抽取评测样本，合并多模型输出
"""

import json
import os
import random
import re
from typing import Dict, List, Any
from pathlib import Path

# =====================
# 配置
# =====================
RESULT_DIR = "/path/to/orthopilot/gen_validation/result"
OUTPUT_DIR = "/path/to/orthopilot/gen_validation/evaluation_app/data/samples"

# 要对比的模型（支持备选名称）
MODELS = [
    "bone-14B-v4",
    "deepseek-r1-0528-ep",
    "medgemma-27b-text-it",
    "gpt-5-high"
]

# 模型名称备选（某些任务可能使用不同的文件名）
MODEL_FALLBACKS = {
    "deepseek-r1-0528-ep": ["deepseek-r1-250528"]  # Task 11使用不同名称
}

# 任务配置：task_id -> 抽样数量
TASK_SAMPLE_SIZES = {
    5: 100,   # 围手术期判断
    6: 100,   # 术前医嘱
    7: 100,   # 手术方案预测
    8: 100,   # 术后医嘱
    9: 100,   # 出院总结
    10: 91,   # 康复会诊（全部）
    11: 100,  # 会诊意见
}

TASK_NAMES = {
    5: "围手术期判断",
    6: "术前医嘱",
    7: "手术方案预测",
    8: "术后医嘱",
    9: "出院总结",
    10: "康复会诊",
    11: "会诊意见"
}

THINK_END_RE = re.compile(r"</think\s*>", re.IGNORECASE)

def extract_final_answer(text: str) -> str:
    """只保留模型最终回答部分，去除<think>标签内容"""
    if not text:
        return ""
    s = str(text).strip()
    m_all = list(THINK_END_RE.finditer(s))
    if m_all:
        return s[m_all[-1].end():].strip()
    return s

def get_model_file_path(model: str, task_id: int) -> str:
    """获取模型结果文件路径，支持备选名称"""
    primary_path = os.path.join(RESULT_DIR, f"{model}_task{task_id}.json")
    if os.path.exists(primary_path):
        return primary_path

    # 尝试备选名称
    fallbacks = MODEL_FALLBACKS.get(model, [])
    for fallback in fallbacks:
        fallback_path = os.path.join(RESULT_DIR, f"{fallback}_task{task_id}.json")
        if os.path.exists(fallback_path):
            print(f"  [INFO] 使用备选文件: {fallback}_task{task_id}.json")
            return fallback_path

    return primary_path  # 返回原始路径（会在后续检查中报错）

def load_model_results(model: str, task_id: int) -> Dict[str, Dict[str, Any]]:
    """加载模型结果，返回 {case_id: {human, model_output}} 的字典"""
    file_path = get_model_file_path(model, task_id)
    if not os.path.exists(file_path):
        print(f"[WARN] 文件不存在: {file_path}")
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = {}
    for item in data:
        case_id = item.get("id", "").strip()
        if not case_id:
            continue

        convs = item.get("conversations", [])
        if len(convs) < 3:
            continue

        # 提取human问题和模型输出
        human_text = ""
        model_output = ""
        ground_truth = ""

        for conv in convs:
            role = conv.get("from", "")
            value = conv.get("value", "")

            if role == "human":
                human_text = value
            elif role == "gpt":
                ground_truth = extract_final_answer(value)
            elif role == model or role not in ["system", "human", "gpt"]:
                # 模型输出（可能是任意模型名称）
                model_output = extract_final_answer(value)

        if human_text and model_output:
            results[case_id] = {
                "human": human_text,
                "ground_truth": ground_truth,
                "model_output": model_output
            }

    return results

def find_common_cases(task_id: int) -> List[str]:
    """找到所有模型都有输出的共同case_id"""
    case_sets = []
    for model in MODELS:
        results = load_model_results(model, task_id)
        case_sets.append(set(results.keys()))
        print(f"  - {model}: {len(results)} cases")

    if not case_sets:
        return []

    common = case_sets[0]
    for s in case_sets[1:]:
        common = common & s

    return list(common)

def prepare_task_samples(task_id: int, sample_size: int) -> List[Dict[str, Any]]:
    """准备单个任务的评测样本"""
    print(f"\n处理 Task {task_id} ({TASK_NAMES[task_id]})...")

    # 找共同cases
    common_cases = find_common_cases(task_id)
    print(f"  共同cases: {len(common_cases)}")

    if len(common_cases) < sample_size:
        print(f"  [WARN] 共同cases数量({len(common_cases)})小于目标样本量({sample_size})")
        sample_size = len(common_cases)

    # ���机抽样
    random.seed(42)  # 固定随机种子，确保可复现
    sampled_cases = random.sample(common_cases, sample_size)

    # 加载各模型结果
    model_results = {}
    for model in MODELS:
        model_results[model] = load_model_results(model, task_id)

    # 组装样本
    samples = []
    for case_id in sampled_cases:
        sample = {
            "case_id": case_id,
            "task_id": task_id,
            "task_name": TASK_NAMES[task_id],
            "patient_info": model_results[MODELS[0]][case_id]["human"],
            "ground_truth": model_results[MODELS[0]][case_id]["ground_truth"],
            "model_outputs": {}
        }

        for model in MODELS:
            sample["model_outputs"][model] = model_results[model][case_id]["model_output"]

        samples.append(sample)

    print(f"  已抽取 {len(samples)} 个样本")
    return samples

def main():
    print("="*60)
    print("医学AI评测数据准备脚本")
    print("="*60)
    print(f"\n模型列表: {MODELS}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_samples = []
    task_stats = {}

    for task_id, sample_size in TASK_SAMPLE_SIZES.items():
        samples = prepare_task_samples(task_id, sample_size)
        all_samples.extend(samples)
        task_stats[task_id] = len(samples)

        # 单独保存每个任务的样本
        task_file = os.path.join(OUTPUT_DIR, f"task{task_id}_samples.json")
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        print(f"  已保存到: {task_file}")

    # 保存合并文件
    all_file = os.path.join(OUTPUT_DIR, "all_samples.json")
    with open(all_file, 'w', encoding='utf-8') as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    # 打印统计
    print("\n" + "="*60)
    print("统计摘要")
    print("="*60)
    for task_id, count in task_stats.items():
        print(f"  Task {task_id} ({TASK_NAMES[task_id]}): {count} 样本")
    print(f"\n  总计: {len(all_samples)} 样本")
    print(f"  已保存到: {all_file}")

if __name__ == "__main__":
    main()
