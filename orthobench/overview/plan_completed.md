# 执行计划与完成状态

## 计划执行顺序

### Step 1: 数据扩充 [DONE]
- 脚本: `benchmark/augment_tasks.py`
- task10: 873 → 5,618 条
- task11: 516 → 5,563 条
- 总 benchmark 样本: 135,745
- 原文件已备份为 `_orig.json`

### Step 2: 疾病名映射 [DONE]
- 脚本: `benchmark/icd_mapping.py`
- `build_icd_mapping()` 返回 `(code_to_english, code_to_chapter)` 字典
- 21 个硬编码英文名 + 450+ 中英术语规则翻译
- 1,000 个 benchmark 码 100% 英文覆盖

### Step 3: 核心圆形疾病树 [DONE]
- 脚本: `benchmark/plot_disease_tree.py`
- 经过 3 次迭代优化
- v1: 基础圆形树
- v2: 优化标签间距、章节着色
- v3: 添加扇形背景填充、分类分隔线、色带标注
- 输出: `figures/disease_tree_circular.pdf` (768K), `.png` (20MB)

### Step 4: 撰写 LaTeX 段落 [DONE]
- 文件: `benchmark/results_benchmark.tex`
- 3 段 Nature 风格
- 无破折号、无性能数据
- 段落结构: 定位与规模 → 任务分类与 ORACLE → 泛化分层

### Step 5: Fig. 2 多面板图 [DONE]
- 脚本: `benchmark/plot_benchmark_overview.py`
- 4 个子图: (a) 任务条形图, (b) 四象限分组图, (c) ICD 环形图, (d) 长尾分布图
- 输出: `figures/fig2_benchmark_overview.pdf` (32K), `.png` (848K)

### Step 6: Extended Data [DONE]
- 图表脚本: `benchmark/plot_extended_data.py`
  - 题型分布图 + 疾病分布细节三面板图
- LaTeX 表格: `benchmark/extended_data_tables.tex`
  - Table 1: 任务总结
  - Table 2: 泛化分层 2×2
  - Table 3: ICD 章节分布 (已用实际数据验证修正)

## 验证结果
- task10: 5,618 条, 0 重复
- task11: 5,563 条, 0 重复
- 所有 13 个输出文件存在且大小正确
- LaTeX 无破折号、无性能数据、3 段结构
- 总 benchmark: 135,745 样本
