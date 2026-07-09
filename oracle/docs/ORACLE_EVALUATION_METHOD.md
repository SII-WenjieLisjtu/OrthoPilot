# ORACLE评测框架方法总结

## 评测框架概述

**ORACLE** (Open Response Assessment for Clinical Language Evaluation) 是一个专门针对开放式临床任务设计的评测框架，结合自动评测和医生评价两种方式。

## 评测方法

### 1. 自动评测（Automatic Evaluation）

#### 评测脚本
- **主脚本**: `scripts/task_all_gen_async.py`
- **模式**: `--mode score`
- **评测模型**: Qwen3-235B-A22B-Instruct-2507（3个judge实例投票）

#### 评分机制
基于**分层评分系统**（Hierarchical Scoring System）：

```python
scores = {
    "临床要素类别": {
        "primary": [covered, possible],      # 必需的核心临床要素
        "secondary": [covered, possible],    # 重要的支持信息
        "additional": [covered, possible]    # 增强临床效用的详细信息
    }
}
```

**最终分数计算**：
```python
total_covered = sum(all covered across all levels)
total_possible = sum(all possible across all levels)
oracle_score = total_covered / total_possible  # 范围: 0-1
```

#### 评测内容
针对不同任务评估不同的临床要素：
- **运动处方**: 手术方案、康复建议
- **内科管理**: 简要病史、诊疗方案
- **其他任务**: 任务特定的临床检查清单

### 2. 医生评价（Physician Evaluation）

#### 评价者
- **数量**: 12名骨科专科医生
- **职称分布**:
  - 住院医师: 2名
  - 主治医师: 4名
  - 副主任医师: 3名
  - 主任医师: 3名
- **经验范围**: 5-28年
- **医院级别**: 全部来自三甲医院

#### 评价维度
使用**5点Likert量表**评估5个临床维度：

1. **医学准确性** (Accuracy): 临床推理的正确性
2. **内容完整性** (Completeness): 必要临床要素的覆盖度
3. **临床安全性** (Safety): 避免有害建议
4. **可操作性** (Actionability): 建议的实际可实施性
5. **表述清晰度** (Clarity): 临床用户的理解难度

#### 评价任务
- **排名任务**: 对4个模型进行1-4排名（1=最好，4=最差）
- **错误标注**: 标记可能导致患者伤害的严重临床错误
- **评价时间**: 平均110.5秒/例（SD=67.4秒）

### 3. 评价一致性

#### 医生间一致性
- **Fleiss' Kappa**: κ = 0.87（排名任务）
- **Kendall's W**: W = 0.96（Likert评分）
- **解释**: 高度一致，表明临床判断的可靠性

#### 自动-人工相关性
- **图展示口径（现有 `generate_figures.py` + 当前 `data/evaluations/`）**: Spearman ρ = -0.895，Pearson r = -0.894（P < 0.001，n = 8,292）
- **任务范围（同一图展示口径）**: Spearman ρ = -0.881 至 -0.927（所有任务 P < 0.001）
- **验证报告口径（`validate_data.py`，先将排名转为 `5-rank`）**: Spearman ρ = 0.895，Pearson r = 0.894（P < 0.001，n = 8,292）
- **解释**: 两种口径使用同一批数据，但因为排名方向定义不同，相关系数符号相反、数值绝对值一致。当前 `figures/analysis/oracle_validation.png` 可由现有打包目录中的数据与脚本复现。

## 评测数据集

### 规模
- **病例数**: 691例
- **任务数**: 7个关键决策点
- **模型数**: 4个（CHEESE, GPT-5, MedGemma-27B, DeepSeek-R1）
- **评价数**: 2,073条（691例 × 3医生）
- **数据点**: 8,292个模型-病例对

### 任务覆盖
1. **Task 5**: 围手术期评估 (Perioperative assessment)
2. **Task 6**: 手术规划 (Surgical planning)
3. **Task 7**: 术前医嘱 (Preoperative orders)
4. **Task 8**: 术后医嘱 (Postoperative orders)
5. **Task 9**: 出院总结 (Discharge summary)
6. **Task 10**: 康复规划 (Rehabilitation planning)
7. **Task 11**: 多学科会诊 (Multidisciplinary consultation)

## ORACLE验证图说明

### 图表设计
- **布局**: 2×4面板（7任务 + Overall）
- **x轴**: ORACLE Score（0-1范围）
- **y轴**: Physician Ranking（1st, 2nd, 3rd, 4th）
- **颜色编码**:
  - 1st: 绿色 (#2E7D32)
  - 2nd: 黄色 (#FBC02D)
  - 3rd: 橙色 (#F57C00)
  - 4th: 红色 (#D32F2F)

### 关键特性
1. **严格整数y轴**: 排名为离散值，点在同一水平线上
2. **随机x轴噪声**: 每个任务使用不同随机种子，增加可视化清晰度
3. **嵌入式分布图**: 仅在上方显示每个排名的ORACLE分数分布
4. **趋势线**: 显示整体负相关趋势
5. **相关系数**: 标注Spearman ρ和p值

### 解释
- **负相关**: 排名数值越小（1st）→ ORACLE分数越高 → 性能越好
- **分布分离**: 不同排名的分数分布清晰分离，验证评测有效性
- **任务一致性**: 所有任务显示相似的强相关模式

## 传统指标的局限性

### 为什么需要ORACLE？

#### 1. BLEU/ROUGE的问题
- **词汇依赖**: 惩罚语义等价但词汇不同的回答
- **无临床理解**: 无法判断医学正确性
- **表面匹配**: 只关注n-gram重叠，忽略临床逻辑

#### 2. Exact Match的问题
- **过于严格**: 临床回答有多种正确表述方式
- **无部分分数**: 无法评估部分正确的回答
- **不适用开放式**: 无法处理长文本生成任务

#### 3. 纯人工评价的问题
- **资源密集**: 需要大量专家时间
- **难以规模化**: 无法评估大规模数据集
- **主观性**: 不同医生可能有不同判断标准

### ORACLE的优势

1. **临床相关性**: 基于实际临床检查清单
2. **可扩展性**: 自动评测可处理大规模数据
3. **可靠性**: 在当前可复现实验口径下，自动评测与医生评价保持显著相关（图展示口径 ρ = -0.895；验证报告口径 ρ = 0.895）
4. **全面性**: 覆盖多个临床维度和任务
5. **可解释性**: 分层评分提供详细反馈

## 实施细节

### 评测流程
```bash
# 1. 生成模型输出
python scripts/task_all_gen_async.py --tasks 5,6,7,8,9,10,11 --mode generate

# 2. 自动评测
python scripts/task_all_gen_async.py --tasks 5,6,7,8,9,10,11 --mode score \
  --judge-specs "local@https://YOUR_LLM_API_BASE_URL:YOUR_MODEL_NAME" \
  --infer-all

# 3. 医生评价（通过Streamlit应用）
streamlit run scripts/evaluation_app/app.py

# 4. 验证分析
python scripts/evaluation_app/validate_data.py
python scripts/evaluation_app/analyze_results.py
python scripts/evaluation_app/generate_figures.py
```

### 论文素材整理位置
- 方法文字：`docs/ORACLE_EVALUATION_METHOD.md`
- 图中文字：`docs/ORACLE_FIGURE_TEXT_PACK_REAL_CASE.md`
- 概念图：`figures/concept/`
- 分析图：`figures/analysis/`
- 样本数据：`data/samples/`
- 医生评价原始结果：`data/evaluations/`
- 分析结果与表格：`data/analysis/`
- 脚本：`scripts/`

### 数据格式

#### 自动评测输出
```json
{
  "patient_id": "xxx",
  "scores": {
    "临床要素类别": {
      "primary": [covered, possible],
      "secondary": [covered, possible],
      "additional": [covered, possible]
    }
  }
}
```

#### 医生评价输出
```json
{
  "doctor_id": "xxx",
  "task_id": 5,
  "case_id": "xxx",
  "ranking": {"CHEESE": 1, "GPT-5": 2, ...},
  "likert_scores": {
    "CHEESE": {
      "accuracy": 5,
      "completeness": 4,
      "safety": 3,
      "actionability": 4,
      "clarity": 4
    }
  },
  "critical_errors": {"CHEESE": false, ...},
  "auto_eval_scores": {"CHEESE": 0.85, ...}
}
```

## 统计方法

### 相关性分析
- **Spearman秩相关**: 评估排名相关性（非参数）
- **Pearson相关**: 评估线性相关性（参数）
- **显著性检验**: P < 0.001（双尾检验）

### 一致性分析
- **Fleiss' Kappa**: 多评价者分类一致性
- **Kendall's W**: 多评价者排序一致性

### 置信区间
- **Wilson Score**: 错误率的95%置信区间
- **Bootstrap**: Bradley-Terry参数的95% CI

## 论文撰写要点

### Results第一段结构
1. **动机**: 开放式任务评测的挑战
2. **传统指标局限**: BLEU/ROUGE/Exact Match的问题
3. **ORACLE设计**: 分层评分 + 医生评价
4. **验证结果**: 当前可复现实验中可见中高一致性（图展示口径 ρ = -0.895；验证报告口径 ρ = 0.895）
5. **临床意义**: 可靠、可扩展、临床相关

### 关键论述
- "传统指标无法捕获临床正确性和安全性"
- "ORACLE结合自动评测的可扩展性和医生评价的临床有效性"
- "当前可复现实验表明，ORACLE 自动评分与医生排序之间仍存在显著相关性，但需区分图展示口径（ρ = -0.895）与验证报告口径（ρ = 0.895）"
- "跨任务一致性证明了框架的泛化能力"

---

**版本**: 1.0
**日期**: 2026-03-03
**基于**: eval.sh, task_all_gen_async.py, 验证报告
