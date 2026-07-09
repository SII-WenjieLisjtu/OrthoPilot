# 代码参考

## 核心函数与模块

### icd_mapping.py

```python
# 主要入口
def build_icd_mapping():
    """返回 (code_to_english, code_to_chapter) 两个字典"""
    # code_to_english: {'M17.100': 'Primary Knee Osteoarthritis', ...}
    # code_to_chapter: {'M17.100': 'M', 'S72.001': 'S', ...}

# 内部翻译
def _translate_chinese(name):
    """规则翻译: 450+ 中英术语, 最长匹配优先"""
```

### augment_tasks.py

```python
# 配置
TASKS = {
    "task10": {"random_offset": 287},  # 5905 - 287 = 5618
    "task11": {"random_offset": 342},  # 5905 - 342 = 5563
}

# 核心逻辑
def augment_task(task_name, config):
    # 1. 加载 test + train
    # 2. 过滤重叠 ID
    # 3. 随机抽样 (seed=42)
    # 4. 合并 & 去重验证
    # 5. 备份 & 写入
```

### plot_disease_tree.py

```python
# 关键参数
fig_size_mm = 400           # 400mm × 400mm
gap_chapter_deg = 3.0       # 章节间隔角度
gap_category_deg = 0.3      # 类目间隔角度

# 径向层
r_chapter_inner = 0.12      # 章节弧带内径
r_chapter_outer = 0.17      # 章节弧带外径
r_leaf = 0.38               # 叶节点
r_id_ood = 0.40-0.44        # ID/OOD 色带
r_rare = 0.45-0.49          # Rare/Non-rare 色带
r_label = 0.52              # 疾病名标签起始
```

### plot_benchmark_overview.py

```python
# Fig.2 四子图布局
fig_w_mm = 183              # Nature 双栏
fig_h_mm = 160
# (a) 任务样本量横向条形图
# (b) ID/OOD × Rare/Non-rare 分组条形图 (双 Y 轴)
# (c) ICD 章节环形图
# (d) 长尾频率分布图 (log scale)
```

## NPG 颜色定义

```python
CHAPTER_COLORS = {
    'M': '#E64B35', 'S': '#4DBBD5', 'D': '#00A087', 'C': '#F39B11',
    'T': '#3C5488', 'Q': '#8491B4', 'R': '#91D1C2', 'G': '#B09C85',
    'L': '#7E6148', 'A': '#DC0000', 'Z': '#3B4992', 'E': '#EE4C97',
    'I': '#631879', 'J': '#008B45', 'K': '#008280', 'F': '#BB7784',
}

ID_COLOR = '#3C5488'      # 蓝
OOD_COLOR = '#E64B35'     # 红
RARE_COLOR = '#8E44AD'    # 紫
NONRARE_COLOR = '#BDC3C7' # 灰
```

## 数据文件格式

### split_stats_by_code.csv (UTF-8 BOM!)
```
code,domain_by_class,is_rare,test_patient_count,...
M17.100,ID,False,245,...
```
注意: 读取时必须用 `encoding='utf-8-sig'`

### code_counts.csv
```
出院诊断编码,频次,最常见对应诊断
M17.100,1234,膝关节骨性关节炎
```

### task10.json / task11.json
```json
[
  {"id": "patient_123", "input": "...", "output": "..."},
  ...
]
```
