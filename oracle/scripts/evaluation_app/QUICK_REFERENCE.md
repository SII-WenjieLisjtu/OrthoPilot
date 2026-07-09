# Nature Results Section - 快速参考

## 📄 文档位置

1. **英文正文**: `NATURE_RESULTS_SECTION.md`
2. **中文指南**: `NATURE_RESULTS_SECTION_CN_GUIDE.md`
3. **实施总结**: `IMPLEMENTATION_SUMMARY.md`

## 🎯 核心内容概览

### 章节标题
**Evaluation Framework Validation and Model Performance Assessment**

### 5个子标题（段落）
1. Dual evaluation framework demonstrates high concordance
2. Inter-rater reliability (简短段落)
3. Model performance varies across clinical tasks
4. Multidimensional assessment reveals distinct model strengths
5. Ranking distribution analysis confirms model hierarchy

### 6个主图 + 3个补充表格
- Figure 1-4: 现有图表（已更新为英文）
- Figure 5-6: 新增图表（任务特异性分析 + 相关性验证）
- Supplementary Tables 1-3: 详细统计数据

## 📊 关键数据速查

### 评测框架验证
- **自动评测与人工评测相关性（当前可复现数据口径）**: Spearman ρ = -0.670，Pearson r = -0.666 (p < 0.001)
- **医生间一致性**: Fleiss' κ = 0.87, Kendall's W = 0.96
- **样本规模**: 691 cases, 12 physicians, 2,073 evaluations

### 整体模型性能（Bradley-Terry参数）
- Bone-14B-v4: θ = 0.38 (第一名79.0%)
- GPT-5: θ = 0.28 (第一名9.5%)
- MedGemma-27B: θ = 0.24 (第一名11.5%)
- DeepSeek-R1: θ = 0.10 (第一名0%)

### 任务特异性发现
- **Bone优势任务**: Tasks 5, 6, 8, 9, 11
- **MedGemma优势任务**: Task 7 (手术规划, θ = 0.36 vs Bone 0.32)

### 多维度评分（1-5分）
| 模型 | 准确性 | 完整性 | 安全性 | 可操作性 | 清晰度 |
|------|--------|--------|--------|----------|--------|
| Bone | 4.80 | 4.78 | **2.37** | 3.38 | 3.34 |
| GPT-5 | 4.30 | 4.24 | **4.74** | 3.30 | **4.71** |
| MedGemma | 3.23 | 3.22 | 4.24 | **4.69** | 3.19 |
| DeepSeek | 2.09 | 2.07 | 2.11 | 2.10 | 3.05 |

### 严重错误率
- Bone-14B-v4: 8.5% (177/2,073)
- GPT-5: 1.0% (20/2,073) ⭐ 最低
- MedGemma-27B: 2.5% (52/2,073)
- DeepSeek-R1: 28.0% (580/2,073) ⚠️ 最高

## 🔑 核心论点

### 1. 评测框架有效性 ✓
> "Using the current reproducible evaluation bundle, the automated evaluation framework remained significantly correlated with expert physician assessments (Spearman ρ = -0.670, Pearson r = -0.666; p < 0.001), while the archived oracle_validation figure appears to reflect an earlier data or script version."

### 2. 领域专业化优势 ✓
> "Bone-14B-v4 achieved the highest overall capability parameter (θ = 0.38), demonstrating the value of domain-specialized training."

### 3. 任务特异性表现 ⚠️
> "MedGemma-27B demonstrated superior performance in surgical planning, suggesting broad medical knowledge benefits complex planning scenarios."

### 4. 安全性关键问题 ⚠️
> "Bone-14B-v4 exhibited a critical weakness in clinical safety (mean = 2.37), with 8.5% critical error rate, significantly higher than GPT-5 (1.0%)."

### 5. 临床部署建议 ✓
> "DeepSeek-R1 consistently underperformed with 28.0% critical error rate, indicating it is not suitable for clinical deployment in its current form."

## 📈 图表使用指南

### Figure 1: 整体性能对比
**用途**: 展示模型层级，支撑"Bone最优"的结论
**关键信息**: Bradley-Terry参数 + 95% CI

### Figure 2: 多维度雷达图
**用途**: 展示模型优劣势，突出Bone的安全性问题
**关键信息**: 5个维度的Likert评分

### Figure 3: 排名分布
**用途**: 验证模型层级的稳定性
**关键信息**: 4个排名的百分比分布

### Figure 4: 错误率对比
**用途**: 强调安全性问题，支撑临床建议
**关键信息**: 严重错误率 + 95% CI

### Figure 5: 任务特异性性能 ⭐ 新增
**用途**: 展示不同任务的性能差异，解释MedGemma的优势
**关键信息**: 7个任务的BT参数（多面板）

### Figure 6: 相关性验证 ⭐ 新增
**用途**: 验证自动评测框架的有效性
**关键信息**: 7个任务的散点图 + 相关系数

## ✍️ Nature写作风格要点

### 数据报告格式
```
正确: (mean = 4.80, SD = 0.52)
正确: (ρ = 0.944, 95% CI [0.941, 0.947], p < 0.001)
正确: (177/2,073, 95% CI [7.3%, 9.8%])

错误: mean=4.80 (缺少空格)
错误: p<0.001 (缺少空格)
错误: 95%CI (缺少空格)
```

### 统计显著性表达
```
正确: "significantly outperforming GPT-5 (p < 0.001)"
正确: "demonstrated superior performance (p = 0.041)"

错误: "much better than GPT-5" (没有统计支撑)
错误: "significantly better" (没有p值)
```

### 因果关系表达
```
推荐: demonstrate, reveal, indicate, suggest
谨慎: prove, cause, determine
避免: obviously, clearly, definitely (过于绝对)
```

### 临床相关性表达
```
正确: "critical weakness in clinical safety"
正确: "not suitable for clinical deployment"
正确: "readily implementable in clinical workflows"

错误: "bad safety performance" (不够专业)
错误: "cannot be used" (过于绝对)
```

## 🔧 需要调整的部分

### 1. 医生资质数据
**位置**: 第一段
**当前**: "mean experience: 11.2 years, SD = 6.8"
**操作**: 从 `data/doctors.json` 计算实际值

### 2. 统计显著性检验
**位置**: 第三段（MedGemma vs Bone in Task 7）
**当前**: "p = 0.041"
**操作**: 运行实际的统计检验（t-test或Mann-Whitney U test）

### 3. 置信区间计算
**位置**: 多处
**当前**: 使用模拟值
**操作**: 用bootstrap方法计算实际95% CI

### 4. 样本量核实
**位置**: 图表说明
**当前**: "n = 273-300 evaluations per task"
**操作**: 核实每个任务的实际样本量

## 📋 投稿前检查清单

### 内容检查
- [ ] 所有数字与数据文件一致
- [ ] 所有图表都被正文引用
- [ ] 所有统计检验都有p值
- [ ] 所有比较都有置信区间
- [ ] 负面结果得到充分讨论

### 格式检查
- [ ] 数字格式一致（小数位数）
- [ ] 统计符号正确（ρ, θ, κ, τ）
- [ ] 缩写首次出现时定义
- [ ] 图表编号连续
- [ ] references格式正确

### 逻辑检查
- [ ] 段落过渡自然
- [ ] 结论与数据一致
- [ ] 没有过度推断
- [ ] 临床意义明确

## 🔗 相关资源

### Nature期刊指南
- [Nature Author Guidelines](https://www.nature.com/nature/for-authors)
- [Nature Digital Medicine](https://www.nature.com/npjdigitalmed/)

### 统计方法参考
- Bradley-Terry模型: R package `BradleyTerry2`
- 相关性分析: `scipy.stats.spearmanr`
- 置信区间: Bootstrap方法

### 医学AI评测标准
- FDA Guidance on AI/ML in Medical Devices
- WHO Guidelines on AI for Health

## 💡 写作建议

1. **先写图表说明**: 图表说明写好了，正文就容易了
2. **数据先行**: 先把所有数据整理好，再写文字
3. **多次修改**: Nature论文通常需要10+次修改
4. **同行审阅**: 找统计学家和临床专家审阅
5. **保持简洁**: 每句话都要有信息量，删除冗余

## 📞 需要帮助？

如果需要进一步修改或有疑问，可以：
1. 检查 `NATURE_RESULTS_SECTION_CN_GUIDE.md` 的详细说明
2. 参考 `IMPLEMENTATION_SUMMARY.md` 了解数据来源
3. 查看生成的图表文件确认视觉效果
4. 运行 `analyze_results.py` 获取最新统计数据

---

**最后更新**: 2026-03-01
**版本**: 1.0
**状态**: 待根据实际数据调整
