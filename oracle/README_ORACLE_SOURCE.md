# ORACLE 评测框架素材索引

本目录将论文中 ORACLE（Open Response Assessment for Clinical Language Evaluation）评测框架用到的说明文字、示意图、分析图、脚本和评测数据集中到一个论文素材包中。

## 目录结构

| 目录 | 内容 |
|---|---|
| `docs/` | ORACLE 方法说明与图中文字素材 |
| `figures/concept/` | ORACLE 流程和真实病例示意图版本 |
| `figures/analysis/` | ORACLE 验证、BT 参数、Likert、排名分布、错误率等分析图 |
| `figures/reference/` | reference_figures和绘图示例 |
| `scripts/` | 自动评测、医生评价应用、分析和绘图脚本 |
| `data/samples/` | 医生评价应用的任务样本数据 |
| `data/evaluations/` | 医生评价原始 JSON 结果 |
| `data/analysis/` | 分析结果 JSON、验证报告和 Nature 表格 |

## 关键文件

### 方法与文字
- `docs/ORACLE_EVALUATION_METHOD.md`：ORACLE 方法、医生评价、验证指标和实施流程说明。
- `docs/ORACLE_FIGURE_TEXT_PACK_REAL_CASE.md`：真实病例示意图使用的英文/中文核对文字。

### 概念图
- `figures/concept/ORACLE_FIGURE_V21_compact_real_case.png`：当前更精炼的真实病例流程图。
- `figures/concept/ORACLE_FIGURE_V20_eval_gt_response_real_case.png`：更完整的真实病例评测流程图。
- `figures/concept/ORACLE_FIGURE_V19_real_case_verified.png`：经核对的真实病例版本。
- `figures/concept/ORACLE_FIGURE_V1_compact_flow.png` 至 `ORACLE_FIGURE_V18_gt_response_compact.png`：历史迭代版本，可用于继续比较和修改。

### 分析图
- `figures/analysis/oracle_validation.png` / `.pdf`：ORACLE 自动评分与医生排名一致性验证图。当前 `data/evaluations/*.json` 可由 `scripts/evaluation_app/generate_figures.py` 复现图中相关性：overall Spearman `ρ = -0.895`、Pearson `r = -0.894`（`n = 8,292`），任务级 Spearman `ρ` 范围为 `-0.881` 至 `-0.927`，所有任务 `P < 0.001`。
- `figures/analysis/extended_bt_params_with_ci.png` / `.pdf`：Extended Data Bradley-Terry 参数主图。
- `figures/analysis/extended_bt_params_final.png` / `.pdf`：BT 参数备份图。
- `figures/analysis/likert_radar*.png` / `.pdf`：Likert 维度雷达图。
- `figures/analysis/ranking_distribution*.png` / `.pdf`：医生排名分布图。
- `figures/analysis/error_rate_comparison*.png` / `.pdf`：错误率对比图。

### 图-脚本对应
- `oracle_validation.*` → `scripts/evaluation_app/generate_figures.py`
- `bradley_terry_params.*` → `scripts/evaluation_app/generate_figures.py`
- `bt_params_all_tasks.*` → `scripts/evaluation_app/generate_figures.py`
- `likert_radar.*` → `scripts/evaluation_app/generate_figures.py`
- `ranking_distribution.*` → `scripts/evaluation_app/generate_figures.py`
- `error_rate_comparison.*` → `scripts/evaluation_app/generate_figures.py`
- `extended_bt_params_with_ci.*` → `scripts/evaluation_app/generate_bt_figure_extended.py`
- `extended_bt_params_final*`、`extended_bt_params_redesigned*`、`likert_radar_optimized*`、`likert_radar_v2*`、`likert_radar_v3*`、`ranking_distribution_optimized*`、`ranking_distribution_v2*`、`ranking_distribution_v3*`、`error_rate_comparison_optimized*`、`test_bt_manual.png`：当前目录中没有对应的单独生成脚本，暂按历史/手工迭代产物保留。

### 脚本
- `scripts/task_all_gen_async.py`：开放任务生成与 ORACLE 自动评分主脚本。
- `scripts/evaluation_app/app.py`：医生评价 Streamlit 应用。
- `scripts/evaluation_app/analyze_results.py`：医生评价与自动评分结果分析。
- `scripts/evaluation_app/validate_data.py`：评测数据验证。
- `scripts/evaluation_app/generate_figures.py`：分析图生成。
- `scripts/evaluation_app/generate_bt_figure_extended.py`：Extended Data BT 参数图生成。
- `scripts/evaluation_app/generate_mock_evaluations.py`：医生评价模拟/校准数据生成。
- `scripts/evaluation_app/export_nature_tables.py`：Nature 表格导出。

### 数据
- `data/samples/all_samples.json`：所有任务样本汇总。
- `data/samples/task5_samples.json` 至 `task11_samples.json`：管理类开放任务样本。
- `data/evaluations/*.json`：医生评价原始记录。
- `data/analysis/analysis_results.json`：分析结果汇总。
- `data/analysis/validation_report.json`：数据验证报告。
- `data/analysis/nature_tables.tex` / `.md`：可用于论文或扩展数据的表格。
- `data/analysis/analysis_report.txt`：分析报告文本。

## 来源对应

这些文件主要从以下位置复制整理而来：

- `Bone/gen_validation/evaluation_app/`：医生评价应用、分析脚本、BT 图表和评价数据。
- `Bone/gen_validation/task_all_gen_async.py`：自动生成与 ORACLE 自动评分主脚本。
- `Bone/project/评测框架/` 原有根目录：ORACLE 方法说明和概念图历史版本。

根目录下原有的 `ORACLE_FIGURE_V*.png`、`ORACLE_EVALUATION_METHOD.md`、`ORACLE_FIGURE_TEXT_PACK_REAL_CASE.md` 暂时保留，以免破坏已有引用；后续可以统一改引用后再清理根目录副本。
