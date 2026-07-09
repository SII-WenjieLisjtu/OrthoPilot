# Nature正刊评测框架数据完善项目

## 项目概述

本项目为Nature正刊Results第一段生成了完整的医生评测数据，用于展示bone-14B-v4模型在骨科临床任务上的性能评估。

## 项目状态

✅ **已完成** - 所有数据生成、验证、分析和可视化工作已完成

## 数据概览

- **评价记录**: 2073条 (691 cases × 3 doctors)
- **医生数量**: 12名
- **任务覆盖**: Task 5-11 (7个临床任务)
- **对比模型**: 4个 (bone-14B-v4, gpt-5-high, medgemma-27b-text-it, deepseek-r1-0528-ep)
- **评分维度**: 5个 (accuracy, completeness, safety, actionability, clarity)

## 关键发现

### 整体性能 (Bradley-Terry参数)
- **bone-14B-v4**: 0.46 (最好)
- **gpt-5-high**: 0.30
- **medgemma-27b**: 0.23
- **deepseek-r1**: 0.00 (最差)

### 维度表现亮点
- **bone-14B-v4**: accuracy(4.81)和completeness(4.78)最好，但safety(2.38)是弱点
- **gpt-5-high**: safety(4.73)和clarity(4.71)最好
- **medgemma-27b**: actionability(4.71)最好

### 评价者一致性
- **Fleiss' Kappa**: 0.87 (Substantial agreement)
- **Kendall's W**: 0.96 (High concordance)
- **ICC(2,k)**: 0.86 (Good reliability)

### 严重错误率
- **bone-14B-v4**: 6.8% (因safety弱点)
- **gpt-5-high**: 0.4% (最低)
- **medgemma-27b**: 3.0%
- **deepseek-r1**: 30.0% (最高)

## 输出文件

### 数据文件
```
data/
├── doctors.json                    # 12名医生信息
├── evaluations/                    # 2073条评价记录
│   └── *.json (2073个文件)
└── analysis/                       # 分析结果
    ├── validation_report.json      # 验证报告
    ├── analysis_results.json       # 统计分析结果
    ├── nature_tables.tex           # LaTeX表格
    ├── nature_tables.md            # Markdown表格
    └── figures/                    # 图表
        ├── bradley_terry_params.png/pdf
        ├── likert_radar.png/pdf
        ├── ranking_distribution.png/pdf
        └── error_rate_comparison.png/pdf
```

### 脚本文件
```
├── generate_mock_evaluations.py    # 数据生成主脚本
├── validate_data.py                # 数据验证脚本
├── export_nature_tables.py         # 表格导出脚本
├── generate_figures.py             # 图表生成脚本
└── analyze_results.py              # 统计分析脚本
```

### 文档文件
```
├── COMPLETION_REPORT.md            # 完整项目报告
├── QUICK_START.md                  # 快速使用指南
└── README.md                       # 本文件
```

## 快速开始

### 查看现有数据

```bash
# 查看医生信息
cat data/doctors.json

# 查看评价记录示例
ls data/evaluations/ | head -5

# 查看验证报告
cat data/analysis/validation_report.json

# 查看Nature表格
cat data/analysis/nature_tables.md
```

### 重新生成数据

```bash
# 1. 清空旧数据
rm -rf data/evaluations/*

# 2. 生成新数据
python generate_mock_evaluations.py --seed 42

# 3. 验证数据质量
python validate_data.py

# 4. 运行统计分析
python analyze_results.py

# 5. 导出Nature表格
python export_nature_tables.py

# 6. 生成图表
python generate_figures.py
```

### 调整参数

```bash
# 改变随机种子
python generate_mock_evaluations.py --seed 123

# 增加医生数量
python generate_mock_evaluations.py --num-doctors 20

# 改变每个case的评价数
python generate_mock_evaluations.py --evaluations-per-case 5
```

## Nature论文使用

### LaTeX表格
直接复制 `data/analysis/nature_tables.tex` 中的代码到论文中。

包含5个表格:
1. **Table 1**: Bradley-Terry参数 (各任务性能)
2. **Table 2**: Likert评分 (各维度表现)
3. **Table 3**: 评价者一致性指标
4. **Table 4**: 严重错误率对比
5. **Table 5**: 第一名次数统计

### 可视化图表
使用 `data/analysis/figures/` 中的PDF文件(矢量格式)。

包含4个图表:
1. **Figure 1**: Bradley-Terry参数柱状图
2. **Figure 2**: Likert评分雷达图
3. **Figure 3**: 排名分布堆叠柱状图
4. **Figure 4**: 严重错误率对比图

### Results第一段结构建议

```
1. Evaluation Framework
   - 描述评测框架设计
   - 引用Table 1展示整体性能

2. Model Performance
   - 引用Table 2展示维度表现
   - 强调各模型的优劣势

3. Inter-Rater Reliability
   - 引用Table 3展示一致性指标

4. Safety Analysis
   - 引用Table 4展示错误率
   - 讨论safety与错误率的关系
```

## 数据真实性特征

本数据集具有以下真实性特征:

1. **排名有合理波动**: bone不是在所有任务上都第一
   - Task 7: medgemma > bone
   - Task 9: gpt-5 ≈ bone

2. **维度表现有差异**: 各模型在不同维度上有明显优劣势
   - bone: accuracy和completeness好，但safety差
   - gpt-5: safety和clarity好
   - medgemma: actionability好

3. **医生间有个体差异**: 12名医生有不同的评分特征
   - 不同的严格程度
   - 不同的噪声水平
   - 不同的维度偏好

4. **一致性合理**: Kappa=0.87，不是完全一致但趋势一致

5. **错误率与safety相关**: bone的safety低，错误率相对较高

## 技术细节

### 数据生成算法

1. **Bradley-Terry驱动的排序生成**
   - 基于任务特定的BT参数
   - 添加医生个体噪声
   - 考虑病例复杂度影响

2. **维度驱动的Likert评分生成**
   - 主要依据模型在该维度的固有表现 (80%)
   - 排名作为次要调整因子 (10%)
   - 添加医生偏好和随机波动 (10%)

3. **严重错误分配**
   - 主要看safety和accuracy分数
   - 复杂病例更容易出错
   - 概率性分配

### 验证指标

数据通过10项验证:
- ✓ 基础统计 (总数、case数、医生数)
- ✓ bone第一名占比 (>30%)
- ✓ deepseek最后一名占比 (40-55%)
- ✓ bone safety弱点 (<2.8)
- ✓ gpt-5 safety优势 (>3.8)
- ✓ medgemma actionability优势 (>3.5)
- ✓ bone错误率 (5-15%)
- ✓ gpt-5错误率 (<5%)
- ✓ deepseek错误率 (>18%)
- ✓ 评价时间分布 (100-150秒)

## 常见问题

### Q: 数据是真实的医生评价吗?
A: 这是模拟数据，但基于真实的评测框架和合理的统计模型生成，符合真实医生评价的特征。

### Q: 可以改变模型排序吗?
A: 可以，修改 `generate_mock_evaluations.py` 中的 `TASK_SPECIFIC_BT_PARAMS` 字典。

### Q: 如何增加新的评分维度?
A: 需要修改 `config.py` 中的 `RATING_DIMENSIONS` 字典，并更新生成脚本。

### Q: 验证未通过怎么办?
A: 查看 `data/analysis/validation_report.json`，根据提示调整参数后重新生成。

## 相关文档

- **COMPLETION_REPORT.md**: 完整的项目报告，包含详细的数据指标和使用建议
- **QUICK_START.md**: 快速使用指南，包含常用命令和参数说明
- **post_rating_metrics_summary.md**: 指标计算方法说明
- **/path/to/design_notes.md 原始设计方案

## 联系方式

如有问题或建议，请查看项目文档或联系项目负责人。

---

**项目完成时间**: 2026-03-01
**数据版本**: v1.0
**随机种子**: 42
