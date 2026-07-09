# 病种维度性能分析

## 分析概述

本分析基于ORACLE评测框架在OrthoBench数据集上的评测结果，按照疾病分类统计各模型的性能。

### 数据基础

- **评测患者总数**: 1,000例（来自subset test_ids）
- **域内患者(ID)**: 383例 (38.3%)
- **域外患者(OOD)**: 617例 (61.7%)
- **罕见病**: 262例 (26.2%)
- **非罕见病**: 738例 (73.8%)
- **病种总数**: 1,000种不同疾病编码

### 模型覆盖

- **有完整数据(1-11任务)**: CHEESE (bone-14B-RL-v2)
- **仅有封闭式任务(1-4)数据**: GPT-5.1, DeepSeek-R1, Qwen3-235B, Gemini-2.5, Kimi-k2, Llama-4

## 输出文件

### 数据文件 (`output/`)

1. **raw_scores.csv** (3.4 MB) - 每个患者在每个任务上的详细分数
2. **disease_level_scores.csv** (2.5 MB) - 按疾病-模型-任务聚合的分数
3. **disease_overall_scores.csv** (656 KB) - 每个病种在所有任务上的全局平均分数
4. **category_level_scores.csv** (8.9 KB) - 按域内/域外、罕见/非罕见分类的分数
5. **task_type_scores.csv** - 封闭式/开放式任务分别的统计
6. **model_task_scores.csv** - 每个模型在每个任务上的分数
7. **report.md** - 完整的分析报告（Markdown格式）

### 图表文件 (`figures/`)

1. **task_type_comparison.png/pdf** - 封闭式 vs 开放式任务性能对比
2. **domain_rare_heatmap.png/pdf** - 域内/域外 vs 罕见/非罕见热力图
3. **top_bottom_diseases.png/pdf** - CHEESE表现最佳/最差的10种疾病
4. **model_disease_comparison.png/pdf** - 各模型病种级别平均性能对比
5. **summary_table.csv** - 性能汇总表

## 主要发现

### 整体性能（病种平均）

| 模型 | 整体平均分 | 域内(ID) | 域外(OOD) | 罕见病 | 非罕见病 | 封闭式 | 开放式 |
|------|-----------|----------|-----------|--------|----------|--------|--------|
| GPT-5.1 | 0.590 | 0.615 | 0.574 | 0.540 | 0.607 | 0.590 | - |
| Kimi-k2 | 0.571 | 0.598 | 0.554 | 0.520 | 0.589 | 0.571 | - |
| Gemini-2.5 | 0.568 | 0.587 | 0.556 | 0.542 | 0.577 | 0.568 | - |
| DeepSeek-R1 | 0.566 | 0.590 | 0.552 | 0.526 | 0.581 | 0.567 | - |
| Llama-4 | 0.549 | 0.574 | 0.534 | 0.513 | 0.562 | 0.549 | - |
| **CHEESE** | **0.546** | **0.567** | **0.533** | **0.495** | **0.564** | **0.608** | **0.492** |
| Qwen3-235B | 0.553 | 0.584 | 0.534 | 0.505 | 0.571 | 0.554 | - |

### 关键洞察

1. **CHEESE在封闭式任务上领先**: 0.608 vs 其他模型最高0.590 (GPT-5.1)
2. **域内性能优于域外**: 所有模型在域内(ID)疾病上表现更好
3. **非罕见病性能优于罕见病**: 罕见病对所有模型都是挑战
4. **开放式任务更具挑战性**: CHEESE在开放式任务上得分为0.492

## 下一步工作

基于这些分析结果，可以撰写Results Section 3: Performance across diseases，包括：

1. **病种分类性能分析** - 按疾病类别（创伤、脊柱、关节、肿瘤等）汇总
2. **域内/域外泛化能力分析** - 统计显著性检验
3. **罕见病处理能力分析** - 与常见病的对比
4. **开放式任务病种分析** - CHEESE在各个管理任务上的病种级别表现

## 使用方法

### 查看特定病种的性能

```python
import pandas as pd

df = pd.read_csv("output/disease_overall_scores.csv")

# 查看特定病种的性能
disease_perf = df[df['disease_name'] == '腰椎间盘突出']
print(disease_perf[['model', 'overall_score', 'n_cases']])

# 查看CHEESE在罕见病上的表现
cheese_rare = df[(df['model'] == 'bone-14B-RL-v2') & (df['is_rare'] == True)]
print(cheese_rare['overall_score'].describe())
```

### 绘制自定义图表

```python
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("output/disease_overall_scores.csv")

# 按模型绘制病种分数分布
cheese_scores = df[df['model'] == 'bone-14B-RL-v2']['overall_score']
gpt_scores = df[df['model'] == 'gpt-5.1']['overall_score']

plt.hist([cheese_scores, gpt_scores], bins=20, label=['CHEESE', 'GPT-5.1'])
plt.xlabel('Overall Score')
plt.ylabel('Number of Diseases')
plt.legend()
plt.savefig('disease_score_distribution.png')
```

---

**生成日期**: 2026-03-23
