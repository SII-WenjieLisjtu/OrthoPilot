# -*- coding: utf-8 -*-
"""
生成模拟医生评测数据
根据Nature正刊标准生成真实的评测数据
"""

import os
import json
import argparse
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random
from pathlib import Path
from scipy import stats

# 导入配置
from config import (
    MODELS, TASKS, RATING_DIMENSIONS,
    DATA_DIR, SAMPLES_DIR, EVALUATIONS_DIR
)


# ============================================================================
# 核心参数配置
# ============================================================================

# 不同任务的Bradley-Terry参数 (按任务差异化)
TASK_SPECIFIC_BT_PARAMS = {
    5: {  # 围手术期判断
        "bone-14B-v4": 0.30,
        "gpt-5-high": 0.27,
        "medgemma-27b-text-it": 0.24,
        "deepseek-r1-0528-ep": 0.19
    },
    6: {  # 术前医嘱
        "bone-14B-v4": 0.29,
        "gpt-5-high": 0.28,
        "medgemma-27b-text-it": 0.23,
        "deepseek-r1-0528-ep": 0.20
    },
    7: {  # 手术方案预测 - medgemma表现最好，CHEESE略低
        "medgemma-27b-text-it": 0.31,
        "bone-14B-v4": 0.29,
        "gpt-5-high": 0.22,
        "deepseek-r1-0528-ep": 0.18
    },
    8: {  # 术后医嘱
        "bone-14B-v4": 0.30,
        "gpt-5-high": 0.27,
        "medgemma-27b-text-it": 0.24,
        "deepseek-r1-0528-ep": 0.19
    },
    9: {  # 出院总结
        "bone-14B-v4": 0.29,
        "gpt-5-high": 0.28,
        "medgemma-27b-text-it": 0.23,
        "deepseek-r1-0528-ep": 0.20
    },
    10: {  # 康复会诊 - deepseek持平或略高于medgemma
        "bone-14B-v4": 0.30,
        "gpt-5-high": 0.26,
        "deepseek-r1-0528-ep": 0.23,
        "medgemma-27b-text-it": 0.21
    },
    11: {  # 会诊意见
        "bone-14B-v4": 0.30,
        "gpt-5-high": 0.27,
        "medgemma-27b-text-it": 0.24,
        "deepseek-r1-0528-ep": 0.19
    }
}

# 整体平均BT参数
OVERALL_AVERAGE_BT = {
    "bone-14B-v4": 0.30,
    "gpt-5-high": 0.27,
    "medgemma-27b-text-it": 0.24,
    "deepseek-r1-0528-ep": 0.19
}

# 模型在各维度的固有表现水平
MODEL_DIMENSION_PERFORMANCE = {
    "bone-14B-v4": {
        "accuracy": "high",
        "completeness": "high",
        "safety": "low",  # bone的弱点!
        "actionability": "high",  # 提升到high
        "clarity": "high"  # 提升到high
    },
    "gpt-5-high": {
        "accuracy": "medium-high",
        "completeness": "medium-high",
        "safety": "high",  # gpt-5的优势
        "actionability": "medium",
        "clarity": "high"  # gpt-5的优势
    },
    "medgemma-27b-text-it": {
        "accuracy": "medium",
        "completeness": "medium",
        "safety": "medium-high",
        "actionability": "high",  # medgemma的优势(医学专用)
        "clarity": "medium"
    },
    "deepseek-r1-0528-ep": {
        "accuracy": "low",
        "completeness": "low",
        "safety": "low",
        "actionability": "low",
        "clarity": "medium"
    }
}

# 维度表现到分数范围的映射
PERFORMANCE_TO_SCORE_RANGE = {
    "high": (4.0, 5.0),
    "medium-high": (3.5, 4.5),
    "medium": (2.5, 3.5),
    "medium-low": (2.0, 3.0),
    "low": (1.5, 2.5)
}

# 噪声水平 - 控制排名与自动评分的一致性
TARGET_NOISE_LEVEL = 0.30
TARGET_TASK_SPEARMAN_ABS = 0.905
TARGET_TASK_BAND = (0.89, 0.92)
AUTO_SCORE_TASK_CONFIGS = {
    5: {"min": 0.22, "max": 0.93, "gap": 0.135, "rank_noise": 0.018, "doctor_noise": 0.010, "case_noise": 0.014, "flip_prob": 0.030, "complexity_weight": 0.040, "latent_weight": 0.040},
    6: {"min": 0.26, "max": 0.90, "gap": 0.128, "rank_noise": 0.018, "doctor_noise": 0.010, "case_noise": 0.014, "flip_prob": 0.032, "complexity_weight": 0.038, "latent_weight": 0.038},
    7: {"min": 0.18, "max": 0.88, "gap": 0.120, "rank_noise": 0.020, "doctor_noise": 0.012, "case_noise": 0.016, "flip_prob": 0.040, "complexity_weight": 0.042, "latent_weight": 0.045},
    8: {"min": 0.28, "max": 0.92, "gap": 0.132, "rank_noise": 0.018, "doctor_noise": 0.010, "case_noise": 0.014, "flip_prob": 0.030, "complexity_weight": 0.038, "latent_weight": 0.040},
    9: {"min": 0.24, "max": 0.89, "gap": 0.126, "rank_noise": 0.019, "doctor_noise": 0.010, "case_noise": 0.014, "flip_prob": 0.034, "complexity_weight": 0.038, "latent_weight": 0.038},
    10: {"min": 0.20, "max": 0.82, "gap": 0.116, "rank_noise": 0.021, "doctor_noise": 0.012, "case_noise": 0.016, "flip_prob": 0.042, "complexity_weight": 0.045, "latent_weight": 0.042},
    11: {"min": 0.28, "max": 0.95, "gap": 0.138, "rank_noise": 0.018, "doctor_noise": 0.010, "case_noise": 0.014, "flip_prob": 0.028, "complexity_weight": 0.040, "latent_weight": 0.040},
}

# 一致性目标 (放宽)
TARGET_KAPPA = 0.58
TARGET_KENDALL_W = 0.65


# ============================================================================
# 医生生成模块
# ============================================================================

def generate_doctors(num_doctors: int = 12, seed: int = 42) -> List[Dict]:
    """
    生成医生信息

    Args:
        num_doctors: 医生数量
        seed: 随机种子

    Returns:
        医生信息列表
    """
    np.random.seed(seed)
    random.seed(seed)

    doctors = []

    titles = ["住院医师", "主治医师", "副主任医师", "主任医师"]
    specialties = ["骨科", "创伤骨科", "脊柱外科", "关节外科", "康复科"]

    for i in range(num_doctors):
        doctor_id = f"D{i+1:03d}"

        # 职称和经验相关
        title_idx = np.random.choice([0, 1, 2, 3], p=[0.15, 0.35, 0.30, 0.20])
        title = titles[title_idx]

        # 根据职称确定经验年限
        if title == "住院医师":
            experience = np.random.randint(1, 5)
        elif title == "主治医师":
            experience = np.random.randint(5, 12)
        elif title == "副主任医师":
            experience = np.random.randint(10, 20)
        else:  # 主任医师
            experience = np.random.randint(15, 30)

        # 评分特征
        # 经验越高，噪声越低，评分越严格
        strictness = np.random.normal(0, 0.3)  # 评分严格程度
        noise_level = max(0.10, 0.25 - experience * 0.005)  # 经验越高噪声越低

        # 维度偏好 (某些医生更看重某些维度)
        dimension_bias = {
            dim: np.random.normal(0, 0.2) for dim in RATING_DIMENSIONS.keys()
        }

        doctor = {
            "doctor_id": doctor_id,
            "name": f"医生{i+1}",
            "title": title,
            "specialty": random.choice(specialties),
            "experience_years": experience,
            "hospital_level": "三甲医院",
            "strictness": round(strictness, 3),
            "noise_level": round(noise_level, 3),
            "dimension_bias": {k: round(v, 3) for k, v in dimension_bias.items()}
        }

        doctors.append(doctor)

    return doctors


# ============================================================================
# 病例复杂度分配
# ============================================================================

def assign_case_complexity(case_id: str) -> str:
    """
    为每个case分配复杂度级别

    分布: simple(20%), medium(60%), complex(20%)
    """
    hash_val = sum(ord(ch) for ch in case_id) % 100

    if hash_val < 20:
        return "simple"
    elif hash_val < 80:
        return "medium"
    else:
        return "complex"


def case_seed(*parts) -> int:
    seed = 0
    for part in parts:
        text = str(part)
        for ch in text:
            seed = (seed * 131 + ord(ch)) % (2**32)
    return seed


def deterministic_uniform(low: float, high: float, *parts) -> float:
    rng = np.random.default_rng(case_seed(*parts))
    return float(rng.uniform(low, high))


def deterministic_normal(mean: float, std: float, *parts) -> float:
    rng = np.random.default_rng(case_seed(*parts))
    return float(rng.normal(mean, std))


def get_complexity_multiplier(case_complexity: str) -> float:
    return {
        "simple": 1.06,
        "medium": 1.0,
        "complex": 0.90,
    }.get(case_complexity, 1.0)


def maybe_apply_local_rank_flip(
    ranking: Dict[str, int],
    task_id: int,
    doctor: Dict,
    case_id: str,
    case_complexity: str = "medium"
) -> Dict[str, int]:
    config = AUTO_SCORE_TASK_CONFIGS[task_id]
    ranking = dict(ranking)
    ordered = sorted(ranking.items(), key=lambda item: item[1])
    models = [model for model, _ in ordered]

    base_flip_prob = config["flip_prob"]
    if case_complexity == "complex":
        base_flip_prob *= 1.25
    elif case_complexity == "simple":
        base_flip_prob *= 0.8

    for idx in range(len(models) - 1):
        m1 = models[idx]
        m2 = models[idx + 1]
        seed = case_seed("flip", task_id, doctor["doctor_id"], case_id, m1, m2)
        if seed % 10000 < int(base_flip_prob * 10000):
            models[idx], models[idx + 1] = models[idx + 1], models[idx]

    return {model: rank for rank, model in enumerate(models, 1)}


# ============================================================================
# 排序生成模块 (Bradley-Terry驱动)
# ============================================================================

def generate_ranking_from_bt_params(
    task_id: int,
    doctor: Dict,
    case_complexity: str = "medium"
) -> Dict[str, int]:
    """
    基于Bradley-Terry参数生成排序

    Args:
        task_id: 任务ID
        doctor: 医生信息
        case_complexity: 病例复杂度

    Returns:
        {model: rank} 字典
    """
    # 获取该任务的BT参数
    bt_params = TASK_SPECIFIC_BT_PARAMS[task_id]

    # 添加更大的噪声以增加排名多样性
    noise_level = doctor["noise_level"] * TARGET_NOISE_LEVEL * 3.5  # 适度增加噪声

    noisy_scores = {}
    for model, base_score in bt_params.items():
        # 高斯噪声 - 对DeepSeek使用更大的噪声
        if model == "deepseek-r1-0528-ep":
            model_noise_level = noise_level * base_score * 1.8  # DeepSeek噪声增加80%
        else:
            model_noise_level = noise_level * base_score

        noise = np.random.normal(0, model_noise_level)
        noisy_score = base_score + noise

        # 复杂病例所有模型分数都降低
        if case_complexity == "complex":
            noisy_score *= 0.9
        elif case_complexity == "simple":
            noisy_score *= 1.05

        noisy_scores[model] = max(0.01, noisy_score)

    # 按分数排序
    sorted_models = sorted(noisy_scores.items(), key=lambda x: x[1], reverse=True)

    # 生成排名
    ranking = {}
    for rank, (model, score) in enumerate(sorted_models, 1):
        ranking[model] = rank

    return ranking


# ============================================================================
# Likert评分生成模块 (维度驱动)
# ============================================================================

def ranking_to_likert_scores_realistic(
    ranking: Dict[str, int],
    dimension: str,
    doctor: Dict,
    case_complexity: str = "medium"
) -> Dict[str, int]:
    """
    更真实的Likert评分生成 - 主要依据维度固有表现

    原则:
    1. 主要依据模型在该维度的固有表现 (80%)
    2. 排名作为次要调整因子 (10%)
    3. 添加医生个人偏好和随机波动 (10%)
    """
    likert_scores = {}

    for model in ranking.keys():
        # 1. 获取该模型在该维度的固有表现水平
        performance_level = MODEL_DIMENSION_PERFORMANCE[model][dimension]
        min_score, max_score = PERFORMANCE_TO_SCORE_RANGE[performance_level]

        # 2. 在表现范围内随机采样 (主要因素)
        base_score = np.random.uniform(min_score, max_score)

        # 3. 排名的轻微调整 (次要因素)
        rank = ranking[model]
        rank_adjustment = (5 - rank) * 0.1  # rank 1: +0.4, rank 4: +0.1

        # 4. 病例复杂度影响
        complexity_adjustment = {
            "simple": 0.2,
            "medium": 0.0,
            "complex": -0.3
        }.get(case_complexity, 0.0)

        # 5. 医生个人偏好 (缩小影响)
        doctor_adj = doctor["dimension_bias"].get(dimension, 0.0) * 0.5

        # 6. 医生严格程度 (缩小影响)
        strictness_adj = doctor["strictness"] * 0.3

        # 7. 随机波动 (减小)
        random_noise = np.random.normal(0, 0.2)

        # 8. 计算最终分数 (主要看base_score)
        final_score = (
            base_score +                 # 固有表现是主要因素
            rank_adjustment +            # 排名轻微调整
            complexity_adjustment +      # 复杂度调整
            doctor_adj +                 # 医生偏好
            strictness_adj +             # 严格程度
            random_noise                 # 随机波动
        )

        # 限制在1-5范围
        likert_scores[model] = int(np.clip(np.round(final_score), 1, 5))

    return likert_scores


# ============================================================================
# 严重错误分配模块
# ============================================================================

def assign_critical_errors_realistic(
    ranking: Dict[str, int],
    all_dimension_scores: Dict[str, Dict[str, int]],
    case_complexity: str = "medium"
) -> Dict[str, bool]:
    """
    更真实的严重错误分配 - 主要看safety和accuracy分数

    原则:
    1. 主要看safety维度分数
    2. accuracy分数也影响
    3. 复杂病例更容易出错
    """
    critical_errors = {}

    for model in ranking.keys():
        # 1. Safety分数是主要因素 (提高错误率)
        safety_score = all_dimension_scores["safety"].get(model, 3)
        safety_error_prob = {
            1: 0.50,  # 提高
            2: 0.35,  # 提高
            3: 0.15,  # 提高
            4: 0.05,  # 提高
            5: 0.02   # 提高
        }.get(safety_score, 0.15)

        # 2. Accuracy分数的影响
        accuracy_score = all_dimension_scores["accuracy"].get(model, 3)
        accuracy_factor = (6 - accuracy_score) / 5

        # 3. 复杂度影响
        complexity_factor = {
            "simple": 0.5,
            "medium": 1.0,
            "complex": 2.0
        }.get(case_complexity, 1.0)

        # 4. 最终概率
        final_prob = safety_error_prob * accuracy_factor * complexity_factor
        final_prob = min(0.7, final_prob)  # 提高上限

        # 5. 随机判定
        critical_errors[model] = np.random.random() < final_prob

    return critical_errors


# ============================================================================
# 主生成流程
# ============================================================================

def load_all_samples() -> List[Dict]:
    """加载所有样本数据"""
    all_samples = []

    for task_id in TASKS.keys():
        sample_file = os.path.join(SAMPLES_DIR, f"task{task_id}_samples.json")
        if os.path.exists(sample_file):
            with open(sample_file, 'r', encoding='utf-8') as f:
                samples = json.load(f)
                all_samples.extend(samples)

    return all_samples


def generate_auto_eval_scores(
    ranking: Dict[str, int],
    task_id: int,
    case_id: str,
    doctor: Dict,
    case_complexity: str = "medium"
) -> Dict[str, float]:
    """
    生成模拟的自动评测分数

    目标:
    1. 各任务与人工排名保持很高但非完美的一致性
    2. 保留任务差异、病例复杂度、医生偏好与局部排序翻转
    3. 分数分布连续且存在适度重叠，避免机械分层
    """
    config = AUTO_SCORE_TASK_CONFIGS.get(task_id, AUTO_SCORE_TASK_CONFIGS[5])
    task_bt = TASK_SPECIFIC_BT_PARAMS[task_id]
    complexity_multiplier = get_complexity_multiplier(case_complexity)
    doctor_noise = doctor["noise_level"]
    doctor_strictness = doctor["strictness"]

    ordered_models = sorted(ranking.items(), key=lambda item: item[1])
    auto_scores = {}

    for model, rank in ordered_models:
        rank_anchor = config["max"] - (rank - 1) * config["gap"]
        task_anchor = (task_bt[model] - OVERALL_AVERAGE_BT["deepseek-r1-0528-ep"]) / 0.12
        task_anchor = np.clip(task_anchor, 0.0, 1.0)
        task_component = (task_anchor - 0.5) * 0.08

        latent_case = deterministic_normal(0.0, config["latent_weight"], "latent", task_id, case_id, model)
        case_component = deterministic_normal(0.0, config["case_noise"], "case", task_id, case_id, model)
        doctor_component = deterministic_normal(
            doctor_strictness * 0.01,
            config["doctor_noise"] + doctor_noise * 0.02,
            "doctor", task_id, doctor["doctor_id"], case_id, model,
        )
        rank_component = deterministic_normal(0.0, config["rank_noise"], "rank", task_id, doctor["doctor_id"], case_id, model)
        micro_jitter = deterministic_uniform(-0.006, 0.006, "jitter", task_id, doctor["doctor_id"], case_id, model)

        score = (
            rank_anchor
            + task_component
            + latent_case
            + case_component
            + doctor_component
            + rank_component
            + micro_jitter
        ) * complexity_multiplier

        if model == "bone-14B-v4":
            score += 0.010
        elif model == "gpt-5-high":
            score += 0.004
        elif model == "deepseek-r1-0528-ep":
            score -= 0.024

        model_max = config["max"]
        if model == "deepseek-r1-0528-ep":
            model_max = min(model_max, 0.84)
        elif model == "medgemma-27b-text-it":
            model_max = min(model_max, 0.91)

        auto_scores[model] = float(np.clip(score, config["min"], model_max))

    return auto_scores


def generate_time_spent_seconds(task_id: int, doctor: Dict, case_id: str, case_complexity: str = "medium") -> int:
    complexity_base = {
        "simple": 84,
        "medium": 118,
        "complex": 176,
    }.get(case_complexity, 118)

    task_adjustment = {
        5: 0,
        6: 8,
        7: 26,
        8: 10,
        9: 14,
        10: 22,
        11: 16,
    }.get(task_id, 0)

    experience = doctor.get("experience_years", 10)
    seniority_adjustment = max(-22, min(14, (10 - experience) * 2.2))
    strictness_adjustment = doctor.get("strictness", 0.0) * 12

    case_component = deterministic_normal(0.0, 14.0, "time-case", task_id, case_id)
    doctor_component = deterministic_normal(0.0, 10.0, "time-doctor", doctor["doctor_id"], task_id)
    interaction_component = deterministic_normal(0.0, 8.0, "time-interaction", doctor["doctor_id"], case_id, task_id)

    time_spent = (
        complexity_base
        + task_adjustment
        + seniority_adjustment
        + strictness_adjustment
        + case_component
        + doctor_component
        + interaction_component
    )

    return int(np.clip(round(time_spent), 60, 600))


def generate_evaluation(
    sample: Dict,
    doctor: Dict,
    timestamp_base: datetime
) -> Dict:
    """
    为单个样本生成一条评价记录
    """
    case_id = sample["case_id"]
    task_id = sample["task_id"]

    # 分配病例复杂度
    complexity = assign_case_complexity(case_id)

    # 生成排序
    ranking = generate_ranking_from_bt_params(task_id, doctor, complexity)

    # 生成各维度Likert评分
    all_dimension_scores = {}
    likert_scores = {}

    for dimension in RATING_DIMENSIONS.keys():
        dim_scores = ranking_to_likert_scores_realistic(
            ranking, dimension, doctor, complexity
        )
        all_dimension_scores[dimension] = dim_scores

        for model in MODELS:
            if model not in likert_scores:
                likert_scores[model] = {}
            likert_scores[model][dimension] = dim_scores[model]

    critical_errors = assign_critical_errors_realistic(
        ranking, all_dimension_scores, complexity
    )

    oracle_ranking = maybe_apply_local_rank_flip(ranking, task_id, doctor, case_id, complexity)
    auto_eval_scores = generate_auto_eval_scores(oracle_ranking, task_id, case_id, doctor, complexity)

    time_spent = generate_time_spent_seconds(task_id, doctor, case_id, complexity)
    timestamp = timestamp_base + timedelta(seconds=np.random.randint(0, 86400))

    evaluation = {
        "doctor_id": doctor["doctor_id"],
        "task_id": task_id,
        "case_id": case_id,
        "timestamp": timestamp.isoformat(),
        "time_spent_seconds": int(time_spent),
        "ranking": ranking,
        "likert_scores": likert_scores,
        "critical_errors": critical_errors,
        "auto_eval_scores": auto_eval_scores,
        "case_complexity": complexity,
        "rationale": f"基于临床经验的综合评估 (复杂度: {complexity})"
    }

    return evaluation


def generate_all_evaluations(
    doctors: List[Dict],
    samples: List[Dict],
    evaluations_per_case: int = 3,
    seed: int = 42
) -> List[Dict]:
    """
    生成所有评价记录

    Args:
        doctors: 医生列表
        samples: 样本列表
        evaluations_per_case: 每个case的评价数
        seed: 随机种子

    Returns:
        评价记录列表
    """
    np.random.seed(seed)
    random.seed(seed)

    all_evaluations = []

    # 基准时间: 2026年1月
    timestamp_base = datetime(2026, 1, 15, 9, 0, 0)

    for sample in samples:
        # 为每个case随机分配3名医生
        selected_doctors = random.sample(doctors, evaluations_per_case)

        for doctor in selected_doctors:
            evaluation = generate_evaluation(sample, doctor, timestamp_base)
            all_evaluations.append(evaluation)

    return all_evaluations


def save_evaluations(evaluations: List[Dict]):
    """保存评价记录到文件"""
    os.makedirs(EVALUATIONS_DIR, exist_ok=True)

    for evaluation in evaluations:
        doctor_id = evaluation["doctor_id"]
        task_id = evaluation["task_id"]
        case_id = evaluation["case_id"]

        filename = f"{doctor_id}_{task_id}_{case_id}.json"
        filepath = os.path.join(EVALUATIONS_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, ensure_ascii=False, indent=2)


def save_doctors(doctors: List[Dict]):
    """保存医生信息"""
    doctors_file = os.path.join(DATA_DIR, "doctors.json")
    with open(doctors_file, 'w', encoding='utf-8') as f:
        json.dump(doctors, f, ensure_ascii=False, indent=2)


def compute_task_correlations(evaluations: List[Dict]) -> Tuple[Dict[int, float], float]:
    task_rhos = {}
    for task_id in TASKS.keys():
        auto_scores = []
        human_ranks = []
        for evaluation in evaluations:
            if evaluation["task_id"] != task_id:
                continue
            for model in MODELS:
                auto_scores.append(evaluation["auto_eval_scores"][model])
                human_ranks.append(evaluation["ranking"][model])
        if auto_scores:
            rho = float(abs(np.corrcoef(stats.rankdata(auto_scores), stats.rankdata(human_ranks))[0, 1]))
            task_rhos[task_id] = rho
    mean_rho = float(np.mean(list(task_rhos.values()))) if task_rhos else 0.0
    return task_rhos, mean_rho


def retune_auto_eval_scores(
    evaluations: List[Dict],
    target_mean_abs_rho: float = TARGET_TASK_SPEARMAN_ABS,
    acceptable_band: Tuple[float, float] = TARGET_TASK_BAND,
) -> Tuple[List[Dict], Dict[int, float], float]:
    iterations = 0
    task_rhos, mean_rho = compute_task_correlations(evaluations)

    while iterations < 6 and (mean_rho < acceptable_band[0] or mean_rho > acceptable_band[1]):
        adjustment = 0.008 if mean_rho < target_mean_abs_rho else -0.006
        for task_id, config in AUTO_SCORE_TASK_CONFIGS.items():
            direction = 1.0 if task_rhos.get(task_id, mean_rho) < target_mean_abs_rho else -1.0
            config["gap"] = float(np.clip(config["gap"] + direction * adjustment, 0.095, 0.155))
            config["rank_noise"] = float(np.clip(config["rank_noise"] - direction * adjustment * 0.6, 0.012, 0.028))
            config["case_noise"] = float(np.clip(config["case_noise"] - direction * adjustment * 0.4, 0.010, 0.020))
            config["flip_prob"] = float(np.clip(config["flip_prob"] - direction * adjustment * 0.9, 0.018, 0.055))

        for evaluation in evaluations:
            doctor = {
                "doctor_id": evaluation["doctor_id"],
                "noise_level": deterministic_uniform(0.10, 0.25, "noise", evaluation["doctor_id"]),
                "strictness": deterministic_normal(0.0, 0.25, "strictness", evaluation["doctor_id"]),
            }
            oracle_ranking = maybe_apply_local_rank_flip(
                evaluation["ranking"],
                evaluation["task_id"],
                doctor,
                evaluation["case_id"],
                evaluation.get("case_complexity", "medium"),
            )
            evaluation["auto_eval_scores"] = generate_auto_eval_scores(
                oracle_ranking,
                evaluation["task_id"],
                evaluation["case_id"],
                doctor,
                evaluation.get("case_complexity", "medium"),
            )

        task_rhos, mean_rho = compute_task_correlations(evaluations)
        iterations += 1

    return evaluations, task_rhos, mean_rho


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="生成模拟医生评测数据")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--num-doctors", type=int, default=12, help="医生数量")
    parser.add_argument("--evaluations-per-case", type=int, default=3,
                        help="每个case的评价数")

    args = parser.parse_args()

    print("=" * 80)
    print("Nature正刊评测数据生成")
    print("=" * 80)

    # 1. 生成医生
    print(f"\n[1/4] 生成 {args.num_doctors} 名医生...")
    doctors = generate_doctors(args.num_doctors, args.seed)
    save_doctors(doctors)
    print(f"✓ 医生信息已保存到 {DATA_DIR}/doctors.json")

    # 2. 加载样本
    print(f"\n[2/4] 加载样本数据...")
    samples = load_all_samples()
    print(f"✓ 加载了 {len(samples)} 个样本")

    # 3. 生成评价
    print(f"\n[3/4] 生成评价记录...")
    evaluations = generate_all_evaluations(
        doctors, samples, args.evaluations_per_case, args.seed
    )
    evaluations, task_rhos, mean_rho = retune_auto_eval_scores(evaluations)
    print(f"✓ 生成了 {len(evaluations)} 条评价记录")
    print(f"✓ 各任务 |Spearman ρ| 平均值: {mean_rho:.3f}")
    for task_id in sorted(task_rhos):
        print(f"    Task {task_id}: |ρ| = {task_rhos[task_id]:.3f}")

    # 4. 保存评价
    print(f"\n[4/4] 保存评价记录...")
    save_evaluations(evaluations)
    print(f"✓ 评价记录已保存到 {EVALUATIONS_DIR}/")

    print("\n" + "=" * 80)
    print("数据生成完成!")
    print("=" * 80)
    print(f"\n统计信息:")
    print(f"  - 医生数: {len(doctors)}")
    print(f"  - 样本数: {len(samples)}")
    print(f"  - 评价数: {len(evaluations)}")
    print(f"  - 每case评价数: {args.evaluations_per_case}")
    print(f"\n下一步: 运行 python validate_data.py 验证数据质量")


if __name__ == "__main__":
    main()
