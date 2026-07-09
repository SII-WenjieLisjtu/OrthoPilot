# -*- coding: utf-8 -*-
"""
存储工具 - 管理医生信息和评价结果
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from config import DATA_DIR, EVALUATIONS_DIR

DOCTORS_FILE = os.path.join(DATA_DIR, "doctors.json")

def ensure_dirs():
    """确保必要目录存在"""
    os.makedirs(EVALUATIONS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

def load_doctors() -> Dict[str, Dict[str, Any]]:
    """加载所有医生信息"""
    if not os.path.exists(DOCTORS_FILE):
        return {}
    with open(DOCTORS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 如果是列表格式，转换为字典格式
        if isinstance(data, list):
            return {d['doctor_id']: d for d in data}
        return data

def save_doctor(doctor_info: Dict[str, Any]) -> str:
    """保存医生信息，返回doctor_id"""
    ensure_dirs()
    doctors = load_doctors()

    doctor_id = doctor_info.get("doctor_id") or f"D{len(doctors)+1:03d}"
    doctor_info["doctor_id"] = doctor_id
    doctor_info["created_at"] = datetime.now().isoformat()

    doctors[doctor_id] = doctor_info

    with open(DOCTORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(doctors, f, ensure_ascii=False, indent=2)

    return doctor_id

def get_doctor(doctor_id: str) -> Optional[Dict[str, Any]]:
    """获取医生信息"""
    doctors = load_doctors()
    return doctors.get(doctor_id)

def save_evaluation(evaluation: Dict[str, Any]) -> str:
    """保存评价结果"""
    ensure_dirs()

    doctor_id = evaluation.get("doctor_id", "unknown")
    task_id = evaluation.get("task_id", 0)
    case_id = evaluation.get("case_id", "unknown")

    # 生成文件名
    safe_case_id = case_id.replace("/", "_").replace("\\", "_")[:50]
    filename = f"{doctor_id}_task{task_id}_{safe_case_id}.json"
    filepath = os.path.join(EVALUATIONS_DIR, filename)

    evaluation["saved_at"] = datetime.now().isoformat()

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    return filepath

def get_doctor_evaluations(doctor_id: str, task_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """获取医生的评价记录"""
    ensure_dirs()
    evaluations = []

    prefix = f"{doctor_id}_"
    if task_id is not None:
        prefix = f"{doctor_id}_task{task_id}_"

    for filename in os.listdir(EVALUATIONS_DIR):
        if filename.startswith(prefix) and filename.endswith(".json"):
            filepath = os.path.join(EVALUATIONS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                evaluations.append(json.load(f))

    return evaluations

def get_evaluated_case_ids(doctor_id: str, task_id: int) -> List[str]:
    """获取医生已评价的case_id列表"""
    evaluations = get_doctor_evaluations(doctor_id, task_id)
    return [e.get("case_id") for e in evaluations if e.get("case_id")]

def get_progress(doctor_id: str, task_id: int, total_samples: int) -> Dict[str, int]:
    """获取评价进度"""
    evaluated = get_evaluated_case_ids(doctor_id, task_id)
    return {
        "completed": len(evaluated),
        "total": total_samples,
        "remaining": total_samples - len(evaluated)
    }

def load_all_evaluations() -> List[Dict[str, Any]]:
    """加载所有评价结果"""
    ensure_dirs()
    evaluations = []

    for filename in os.listdir(EVALUATIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(EVALUATIONS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                evaluations.append(json.load(f))

    return evaluations
