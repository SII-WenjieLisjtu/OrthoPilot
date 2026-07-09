# OrthoBench Benchmark 工作概要

## 项目概述

OrthoBench 是一个全流程临床推理基准测试(full-pathway clinical benchmark)，覆盖骨科全流程关键决策节点。

### 核心数据规模
- **5,905** 测试患者
- **135,745** 评估实例
- **11** 临床任务 (4 诊断 + 7 管理)
- **1,000** 种疾病码 (ICD-10)
- 数据来源: 180,000 患者纵向队列 (2004-2024)

### 泛化分层 (Generalization Stratification)

|          | Non-rare codes | Non-rare patients | Rare codes | Rare patients | Total codes | Total patients |
|----------|---------------|-------------------|------------|---------------|-------------|----------------|
| **ID**   | 321           | 3,051             | 62         | 274           | 383         | 3,325          |
| **OOD**  | 417           | 2,220             | 200        | 360           | 617         | 2,580          |
| **Total**| 738           | 5,271             | 262        | 634           | 1,000       | 5,905          |

### 11 个临床任务

| Task | Category   | Description                    | Question Types | Samples | Patients |
|------|------------|--------------------------------|---------------|---------|----------|
| 1    | Diagnostic | Admission diagnosis            | Open/MC/TF    | 17,713  | 5,905    |
| 2    | Diagnostic | Preoperative diagnosis         | Open/MC/TF    | 17,715  | 5,905    |
| 3    | Diagnostic | Postoperative diagnosis        | Open/MC/TF    | 17,400  | 5,905    |
| 4    | Diagnostic | Discharge diagnosis            | Open/MC/TF    | 17,712  | 5,905    |
| 5    | Management | Perioperative risk assessment  | Open          | 20,464  | 5,905    |
| 6    | Management | Surgical approach selection    | Open          | 8,154   | 5,905    |
| 7    | Management | Operative note generation      | Open          | 5,875   | 5,875    |
| 8    | Management | Postoperative order writing    | Open          | 13,665  | 5,905    |
| 9    | Management | Discharge summary generation   | Open          | 5,866   | 5,866    |
| 10   | Management | Rehabilitation planning        | Open          | 5,618   | 5,618    |
| 11   | Management | Multidisciplinary consultation | Open          | 5,563   | 5,563    |
| **Total** |        |                                |               | **135,745** | **5,905** |

---

## 已完成工作

### 1. 数据扩充 (augment_tasks.py)
- task10: 873 → 5,618 条 (random_offset=287)
- task11: 516 → 5,563 条 (random_offset=342)
- seed=42, 已去重, 原文件备份为 `_orig.json`

### 2. ICD 疾病名映射 (icd_mapping.py)
- 1,000 个 benchmark 疾病码全部映射为英文名称
- 21 个无中文名编码硬编码英文
- 450+ 中英医学术语规则翻译字典
- 0 个残留中文字符

### 3. Results 段落 (results_benchmark.tex)
- 3 段 Nature 风格段落
- 不含破折号、不含性能数据
- 覆盖: 定位与规模 → 任务分类 → 泛化分层

### 4. 核心圆形疾病树 (plot_disease_tree.py)
- 圆形树状图展示 1,000 种疾病 ICD 层级结构
- 16 个 ICD 章节彩色扇区 + 英文疾病名标注
- ID/OOD + Rare/Non-rare 外圈色带
- 输出: figures/disease_tree_circular.pdf/png (400mm, 600 DPI)

### 5. Fig. 2 多面板组合图 (plot_benchmark_overview.py)
- (a) 任务样本量横向条形图
- (b) ID/OOD × Rare/Non-rare 分组条形图
- (c) ICD 章节分布环形图
- (d) 疾病频率长尾分布图
- 输出: figures/fig2_benchmark_overview.pdf/png (183mm, Nature 双栏)

### 6. Extended Data (plot_extended_data.py + extended_data_tables.tex)
- 题型分布堆叠条形图 (Tasks 1-4)
- 疾病分布细节三面板图
- 3 个 LaTeX Extended Data Tables (任务总结 / 泛化分层 / ICD 章节)

---

## 文件索引

### 脚本
| 文件 | 说明 |
|------|------|
| `benchmark/augment_tasks.py` | 数据扩充脚本 (task10/task11) |
| `benchmark/icd_mapping.py` | ICD 疾病码→英文名映射 |
| `benchmark/plot_disease_tree.py` | 核心圆形疾病树 |
| `benchmark/plot_benchmark_overview.py` | Fig.2 多面板组合图 |
| `benchmark/plot_extended_data.py` | Extended Data 附录图 |

### 文本
| 文件 | 说明 |
|------|------|
| `benchmark/results_benchmark.tex` | Results 段落 (OrthoBench 介绍) |
| `benchmark/extended_data_tables.tex` | Extended Data Tables (LaTeX) |

### 输出图表
| 文件 | 说明 |
|------|------|
| `benchmark/figures/disease_tree_circular.pdf/png` | 圆形疾病树 (400mm) |
| `benchmark/figures/fig2_benchmark_overview.pdf/png` | Fig.2 概览图 (183mm) |
| `benchmark/figures/ext_fig_question_types.pdf/png` | 题型分布图 |
| `benchmark/figures/ext_fig_disease_details.pdf/png` | 疾病分布细节图 |

### 数据
| 文件 | 说明 |
|------|------|
| `gen_validation/test_final/task10.json` | 扩充后 (5,618 条) |
| `gen_validation/test_final/task11.json` | 扩充后 (5,563 条) |
| `gen_validation/test_final/task10_orig.json` | 原始备份 (873 条) |
| `gen_validation/test_final/task11_orig.json` | 原始备份 (516 条) |
| `gen_validation/test_final/split_stats_by_code.csv` | 疾病码分布 (UTF-8 BOM) |
| `gen_validation/test_final/split_stats_summary_test.csv` | 四象限汇总 |
| `data/stat/all/code_counts.csv` | 1,808 码→中文名 |

---

## ICD-10 章节分布

| Ch. | Name | Codes | Patients | ID | OOD | Non-rare | Rare |
|-----|------|-------|----------|----|-----|----------|------|
| M | Musculoskeletal | 309 | 1,949 | 127 | 182 | 260 | 49 |
| S | Injuries | 254 | 2,290 | 109 | 145 | 245 | 9 |
| D | Neoplasms | 115 | 216 | 34 | 81 | 55 | 60 |
| C | Malignant neoplasms | 106 | 426 | 39 | 67 | 27 | 79 |
| T | Trauma & complications | 50 | 102 | 19 | 31 | 47 | 3 |
| Q | Congenital | 47 | 123 | 16 | 31 | 11 | 36 |
| R | Symptoms & signs | 26 | 80 | 9 | 17 | 26 | 0 |
| G | Nervous system | 21 | 60 | 7 | 14 | 17 | 4 |
| L | Skin | 17 | 20 | 2 | 15 | 14 | 3 |
| A | Infectious | 14 | 17 | 6 | 8 | 3 | 11 |
| Z | Health services | 13 | 590 | 9 | 4 | 13 | 0 |
| E | Endocrine | 11 | 14 | 4 | 7 | 6 | 5 |
| I | Circulatory | 10 | 10 | 2 | 8 | 7 | 3 |
| J | Respiratory | 3 | 4 | 0 | 3 | 3 | 0 |
| K | Digestive | 3 | 3 | 0 | 3 | 3 | 0 |
| F | Mental | 1 | 1 | 0 | 1 | 1 | 0 |
| **Total** | | **1,000** | **5,905** | **383** | **617** | **738** | **262** |

---

## 技术要点

### Nature 图表风格规范
- 颜色: NPG 调色板 (#E64B35, #4DBBD5, #00A087, #F39B11, #3C5488, #8491B4, #91D1C2, #B09C85)
- 字体: Arial/DejaVu Sans, 8-12pt
- 线宽: 0.6-0.8pt, 无上右边框 (despine)
- DPI: 600, 输出 PDF + PNG
- 尺寸: Nature 单栏 89mm / 双栏 183mm

### 已知问题与修复
1. **CSV BOM 编码**: `split_stats_by_code.csv` 含 UTF-8 BOM (EF BB BF), 读取时需用 `encoding='utf-8-sig'`
2. **task10 ID 重叠**: train 中 782 个 ID 与 test 重叠, 扩充时已过滤
3. **Extended Data Table 3**: 初始按章节分解的 ID/OOD/Rare 数字为估算值, 已用实际数据验证修正

### 关键配置
- 随机种子: seed=42
- task10 缺失偏移: 287 (5905-287=5618)
- task11 缺失偏移: 342 (5905-342=5563)
