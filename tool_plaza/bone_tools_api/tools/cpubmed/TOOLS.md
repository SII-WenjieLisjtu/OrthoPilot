# CPubMed工具列表

## 核心工具 (2个)

### 1. cpubmed.search (CPubMedTool)
**功能**: 通用医学知识图谱查询工具

**参数**:
- `entity` (必需): 医学实体名称
- `relation` (可选): 关系类型过滤
- `entity_type` (可选): 实体类型过滤
- `limit` (可选): 返回结果数量，默认20

**示例**:
```python
tool = CPubMedTool()
response = tool.execute({
    "entity": "糖尿病",
    "relation": "药物治疗",
    "limit": 10
})
```

### 2. cpubmed.get_relations (CPubMedRelationTool)
**功能**: 获取实体的所有关系类型和统计信息

**参数**:
- `entity` (必需): 医学实体名称
- `limit_per_relation` (可选): 每种关系返回的最大数量，默认10

**示例**:
```python
tool = CPubMedRelationTool()
response = tool.execute({
    "entity": "高血压",
    "limit_per_relation": 5
})
```

---

## 实用工具 (3个)

### 3. cpubmed.get_summary (CPubMedDatabaseSummaryTool)
**功能**: 获取数据库统计信息和概览

**参数**: 无

**返回**: 数据库规模、关系类型、实体类型等统计信息

**示例**:
```python
tool = CPubMedDatabaseSummaryTool()
response = tool.execute({})
```

### 4. cpubmed.get_entity_type (CPubMedGetEntityTypeTool)
**功能**: 查询指定实体的类型

**参数**:
- `entity` (必需): 实体名称

**示例**:
```python
tool = CPubMedGetEntityTypeTool()
response = tool.execute({"entity": "二甲双胍"})
```

### 5. cpubmed.fuzzy_search (CPubMedFuzzySearchTool)
**功能**: 模糊搜索实体，支持相似度匹配

**参数**:
- `keyword` (必需): 搜索关键词
- `threshold` (可选): 相似度阈值，0-1之间，默认0.6
- `limit` (可选): 返回结果数量，默认10

**示例**:
```python
tool = CPubMedFuzzySearchTool()
response = tool.execute({
    "keyword": "肺癌",
    "threshold": 0.7,
    "limit": 5
})
```

---

## 关系类型专用工具 (45个)

这些工具是基于 `cpubmed.search` 的封装，每个工具固定查询一种特定的关系类型。

### 工具命名规则
- 格式: `cpubmed.query_{英文关系名}`
- 示例: `cpubmed.query_drug_treatment` (药物治疗)
- 说明描述保持中文，便于理解

### 参数
所有关系专用工具使用相同的参数：
- `entity` (必需): 医学实体名称
- `limit` (可选): 返回结果数量，默认20

### 使用方式
```python
from tools.cpubmed import RELATION_TOOL_CLASSES

# 获取工具类
DrugTreatmentTool = RELATION_TOOL_CLASSES["药物治疗"]

# 创建实例并使用
tool = DrugTreatmentTool()
response = tool.execute({
    "entity": "高血压",
    "limit": 10
})
```

### 完整关系类型列表 (45种)

#### 治疗相关 (6种)
1. `cpubmed.query_drug_treatment` - 药物治疗
2. `cpubmed.query_auxiliary_treatment` - 辅助治疗
3. `cpubmed.query_surgical_treatment` - 手术治疗
4. `cpubmed.query_radiation_treatment` - 放射治疗
5. `cpubmed.query_chemotherapy` - 化疗
6. `cpubmed.query_prevention` - 预防

#### 检查相关 (6种)
7. `cpubmed.query_laboratory_test` - 实验室检查
8. `cpubmed.query_imaging_test` - 影像学检查
9. `cpubmed.query_auxiliary_test` - 辅助检查
10. `cpubmed.query_endoscopy_test` - 内窥镜检查
11. `cpubmed.query_histology_test` - 组织学检查
12. `cpubmed.query_screening` - 筛查

#### 症状诊断相关 (6种)
13. `cpubmed.query_clinical_manifestation` - 临床表现
14. `cpubmed.query_etiology` - 病因
15. `cpubmed.query_pathological_classification` - 病理分型
16. `cpubmed.query_complication` - 并发症
17. `cpubmed.query_differential_diagnosis` - 鉴别诊断
18. `cpubmed.query_risk_factor` - 高危因素

#### 流行病学相关 (8种)
19. `cpubmed.query_incidence` - 发病率
20. `cpubmed.query_affected_site` - 发病部位
21. `cpubmed.query_susceptible_population` - 多发群体
22. `cpubmed.query_onset_age` - 发病年龄
23. `cpubmed.query_gender_tendency` - 发病性别倾向
24. `cpubmed.query_endemic_area` - 多发地区
25. `cpubmed.query_seasonal_prevalence` - 多发季节
26. `cpubmed.query_mortality` - 死亡率

#### 预后相关 (3种)
27. `cpubmed.query_prognosis` - 预后状况
28. `cpubmed.query_survival_rate` - 预后生存率
29. `cpubmed.query_post_treatment_symptom` - 治疗后症状

#### 其他关系 (16种)
30. `cpubmed.query_synonym` - 同义词
31. `cpubmed.query_risk_assessment_factor` - 风险评估因素
32. `cpubmed.query_related_cause` - 相关（导致）
33. `cpubmed.query_related_transformation` - 相关（转化）
34. `cpubmed.query_related_symptom` - 相关（症状）
35. `cpubmed.query_department` - 就诊科室
36. `cpubmed.query_metastasis_site` - 转移部位
37. `cpubmed.query_invasion_site` - 外侵部位
38. `cpubmed.query_genetic_factor` - 遗传因素
39. `cpubmed.query_transmission_route` - 传播途径
40. `cpubmed.query_pathogenesis` - 发病机制
41. `cpubmed.query_pathophysiology` - 病理生理
42. `cpubmed.query_medical_history` - 病史
43. `cpubmed.query_stage` - 阶段
44. `cpubmed.query_comorbidity` - 合并症
45. `cpubmed.query_tissue_invasion_symptom` - 侵及周围组织转移的症状

---

## 工具统计

- **总工具数**: 50个
  - 核心通用工具: 2个
  - 实用工具: 3个
  - 关系专用工具: 45个

- **数据规模**:
  - 总三元组: 4,580,006
  - 唯一实体: 1,810,772
  - 关系类型: 45种
  - 实体类型: 12种

---

## 使用建议

### 1. 通用查询
使用 `cpubmed.search` 进行灵活的多条件查询

### 2. 探索实体
使用 `cpubmed.get_relations` 了解实体的全部关系

### 3. 专项查询
使用关系专用工具进行特定类型的快速查询

### 4. 模糊搜索
当不确定实体名称时，使用 `cpubmed.fuzzy_search` 查找相似实体

### 5. 数据探索
使用 `cpubmed.get_summary` 了解数据库整体情况
