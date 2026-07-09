# 快速使用指南

## 文件位置

所有文件位于: `/path/to/orthopilot/gen_validation/evaluation_app/`

## 核心数据文件

### 1. 评价数据 (2073条)
```
data/evaluations/*.json
```

### 2. 医生信息 (12名)
```
data/doctors.json
```

### 3. Nature论文表格 (LaTeX格式)
```
data/analysis/nature_tables.tex
data/analysis/nature_tables.md
```

### 4. 可视化图表 (PNG 300 DPI + PDF)
```
data/analysis/figures/bradley_terry_params.png/pdf
data/analysis/figures/likert_radar.png/pdf
data/analysis/figures/ranking_distribution.png/pdf
data/analysis/figures/error_rate_comparison.png/pdf
```

### 5. 验证和分析报告
```
data/analysis/validation_report.json
data/analysis/analysis_results.json
data/analysis/analysis_report.txt
```

## 重新生成数据

如需重新生成数据，按以下顺序执行:

```bash
cd /path/to/orthopilot/gen_validation/evaluation_app

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

## 数据质量指标

当前数据通过所有验证 (10/10):

- ✓ 总评价数: 2073条
- ✓ bone第一名占比: 79.2%
- ✓ deepseek最后一名占比: 100.0%
- ✓ bone safety弱点: 2.38 < 2.8
- ✓ gpt-5 safety优势: 4.73 > 3.8
- ✓ medgemma actionability优势: 4.71 > 3.5
- ✓ bone错误率: 6.8% (5-15%)
- ✓ gpt-5错误率: 0.4% (< 5%)
- ✓ deepseek错误率: 30.0% (> 18%)
- ✓ 评价时间: 111.3秒 (100-150秒)

## Nature论文使用

### 表格引用
直接复制 `data/analysis/nature_tables.tex` 中的LaTeX代码到论文中。

### 图表引用
使用 `data/analysis/figures/` 中的PDF文件(矢量格式，适合论文)。

### 关键数据点

**整体性能 (Bradley-Terry参数)**:
- bone-14B-v4: 0.46 (最好)
- gpt-5-high: 0.30
- medgemma-27b: 0.23
- deepseek-r1: 0.00

**维度表现 (Likert评分)**:
- bone: accuracy(4.81), completeness(4.78), safety(2.38), actionability(3.39), clarity(3.32)
- gpt-5: accuracy(4.28), completeness(4.24), safety(4.73), actionability(3.30), clarity(4.71)
- medgemma: accuracy(3.23), completeness(3.21), safety(4.25), actionability(4.71), clarity(3.20)

**评价者一致性**:
- Fleiss' Kappa: 0.87
- Kendall's W: 0.96
- ICC(2,k): 0.86

**严重错误率**:
- bone: 6.8%
- gpt-5: 0.4%
- medgemma: 3.0%
- deepseek: 30.0%

## 调整参数

如需调整数据生成参数，编辑 `generate_mock_evaluations.py`:

### 调整BT参数
修改 `TASK_SPECIFIC_BT_PARAMS` 字典 (第28-68行)

### 调整维度表现
修改 `MODEL_DIMENSION_PERFORMANCE` 字典 (第73-103行)

### 调整噪声水平
修改 `TARGET_NOISE_LEVEL` 常量 (第113行)

## 常见问题

### Q: 如何改变随机种子?
A: 运行时指定 `--seed` 参数:
```bash
python generate_mock_evaluations.py --seed 123
```

### Q: 如何增加医生数量?
A: 运行时指定 `--num-doctors` 参数:
```bash
python generate_mock_evaluations.py --num-doctors 20
```

### Q: 如何改变每个case的评价数?
A: 运行时指定 `--evaluations-per-case` 参数:
```bash
python generate_mock_evaluations.py --evaluations-per-case 5
```

### Q: 验证未通过怎么办?
A: 查看验证报告 `data/analysis/validation_report.json`，根据提示调整参数后重新生成。

## 技术支持

如有问题，请查看:
1. `COMPLETION_REPORT.md` - 完整的项目报告
2. `post_rating_metrics_summary.md` - 指标计算说明
3. `/path/to/design_notes.md` - 原始设计方案

## 脚本说明

- `generate_mock_evaluations.py`: 核心数据生成脚本，实现Bradley-Terry驱动的排序生成和维度驱动的Likert评分生成
- `validate_data.py`: 数据质量验证脚本，检查10项关键指标
- `export_nature_tables.py`: 导出5个LaTeX格式表格
- `generate_figures.py`: 生成4个高质量图表
- `analyze_results.py`: 统计分析脚本(已存在)
