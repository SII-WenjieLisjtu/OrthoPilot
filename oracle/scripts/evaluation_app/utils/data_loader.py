# -*- coding: utf-8 -*-
"""
数据加载工具
"""

import json
import os
from typing import Dict, List, Any, Optional
from config import SAMPLES_DIR, TASKS

def load_task_samples(task_id: int) -> List[Dict[str, Any]]:
    """加载指定任务的样本"""
    file_path = os.path.join(SAMPLES_DIR, f"task{task_id}_samples.json")
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_all_samples() -> List[Dict[str, Any]]:
    """加载所有样本"""
    file_path = os.path.join(SAMPLES_DIR, "all_samples.json")
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_task_sample_count(task_id: int) -> int:
    """获取任务样本数量"""
    samples = load_task_samples(task_id)
    return len(samples)

def get_sample_by_index(task_id: int, index: int) -> Optional[Dict[str, Any]]:
    """根据索引获取样本"""
    samples = load_task_samples(task_id)
    if 0 <= index < len(samples):
        return samples[index]
    return None

def get_available_tasks() -> Dict[int, Dict[str, Any]]:
    """获取可用任务及其样本数"""
    available = {}
    for task_id, info in TASKS.items():
        count = get_task_sample_count(task_id)
        if count > 0:
            available[task_id] = {
                **info,
                "sample_count": count
            }
    return available
