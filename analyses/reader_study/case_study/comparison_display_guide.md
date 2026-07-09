# 医生 vs CHEESE 对比展示指南

## 📄 文档结构

**医生评测问卷_CHEESE优势展示.docx** 现在包含完整的CHEESE模型回答，可用于制作人机对比图表。

### 每个案例的结构

#### 诊断任务 (Task 1-4)

```
┌─────────────────────────────────────────┐
│ 【案例信息】                             │
│ • CHEESE优势: 5/5 其他模型出错          │
│ • AI模型表现: CHEESE✓ GPT-5.1✗ ...     │
│ • 标准答案: xxx                         │
├───────────────���─────────────────────────┤
│ 【病历信息及诊断问题】                   │
│ • 主诉: ...                             │
│ • 现病史: ...                           │
│ • 专科情况: ...                         │
│ • 诊断问题: ...                         │
├─────────────────────────────────────────┤
│ 【您的答案】                             │
│ ________________________________        │
│ (医生填写区)                            │
├─────────────────────────────────────────┤
│ 【标准答案】                             │
│ xxx                                     │
├─────────────────────────────────────────┤
│ 【CHEESE模型的回答】                     │
│                                         │
│ 推理过程：(浅灰色)                      │
│ 好的，我现在需要分析这个患者的入院记录    │
│ ...完整的推理过程...                    │
│                                         │
│ CHEESE的最终答案：(绿色突出)            │
│ 是/否/选项X/完整诊断                    │
└─────────────────────────────────────────┘
```

#### 管理任务 (Task 5-11)

```
┌─────────────────────────────────────────┐
│ 【任务类型】开放式生成任务               │
├─────────────────────────────────────────┤
│ 【病历信息】                             │
│ • 疾病史: ...                           │
│ • 专科情况: ...                         │
│ • 任务要求: ...                         │
├─────────────────────────────────────────┤
│ 【AI模型评分】                           │
│ • CHEESE: 明确的判断(5,5)...            │
│ • DeepSeek-R1: ...                      │
│ • Grok-4: ...                           │
├─────────────────────────────────────────┤
│ 【您的回答】                             │
│ ________________________________        │
│ (医生填写区)                            │
├─────────────────────────────────────────┤
│ 【CHEESE模型的回答】(绿色)               │
│ 完整的临床管理方案...                    │
│ (包含完整的风险评估/手术方案/           │
│  术后医嘱/出院总结等)                   │
└───────────────────────────────────────���─┘
```

## 🎨 制作对比图的数据提取

### 方案1：直接从Word提取

可以直接从Word文档中提取内容制作对比图：

```python
from docx import Document

doc = Document('医生评测问卷_CHEESE优势展示.docx')

# 遍历段落提取内容
for para in doc.paragraphs:
    text = para.text
    
    # 识别医生答案区域
    if '【您的答案】' in text:
        # 下一段是医生的答案
        pass
    
    # 识别CHEESE回答
    if '【CHEESE模型的回答】' in text:
        # 后续段落是CHEESE的回答
        pass
```

### 方案2：使用JSON数据

更推荐使用JSON数据文件：**selected_cases_cheese_advantage.json**

```python
import json

with open('selected_cases_cheese_advantage.json', 'r') as f:
    cases = json.load(f)

for patient in cases:
    patient_id = patient['patient_id']
    
    # 诊断任务
    for task_num in range(1, 5):
        task_key = f'task{task_num}'
        if task_key in patient['tasks']:
            for case in patient['tasks'][task_key]:
                # 提取问题
                question = ""
                for conv in case['conversations']:
                    if conv['from'] == 'human':
                        question = conv['value']
                    elif conv['from'] == 'gpt':
                        standard_answer = conv['value']
                
                # CHEESE的预测
                cheese_prediction = case['model_predictions']['bone-14B-RL-v2']['prediction']
                
                # 标准答案
                ground_truth = case['ground_truth']
                
                # 制作对比图
                # doctor_answer = "..." # 从医生填写的Word中提取
                make_comparison_figure(
                    question=question,
                    doctor_answer=doctor_answer,
                    cheese_answer=cheese_prediction,
                    standard_answer=ground_truth
                )
    
    # 管理任务
    for task_num in range(5, 12):
        task_key = f'task{task_num}'
        if task_key in patient['tasks']:
            task_data = patient['tasks'][task_key]
            convs = task_data['conversations'][0]
            
            for conv in convs:
                if conv['from'] == 'human':
                    question = conv['value']
                elif conv['from'] == 'gpt':
                    cheese_answer = conv['value']
            
            # 制作对比图
            # ...
```

## 📊 对比图示例

### 示例1：诊断任务对比（表格形式）

```
┌─────────────────────────────────────────────────────────────┐
│ 案例：入院诊断 - 是非判断                                    │
│ 患者ID: 453171276965683200                                  │
│ CHEESE优势: 5/5 其他模型全错                                │
├─────────────────────────────────────────────────────────────┤
│ 病历摘要：                                                   │
│ 主诉: 右肩关节疼痛不适半年余，加重一周                       │
│ 诊断问题: 诊断「骨化性肌炎」是否正确？                       │
├─────────────────┬───────────────────┬───────────────────────┤
│ 标准答案        │ 医生答案           │ CHEESE答案            │
├─────────────────┼───────────────────┼───────────────────────┤
│ 是              │ 是                │ 是                    │
│                 │                   │                       │
│                 │ 理由：             │ 推理：                │
│                 │ 根据病史和体征，   │ 患者半年余前出现右肩   │
│                 │ 考虑骨化性肌炎     │ 关节疼痛不适，一周前   │
│                 │ 可能性大           │ 工作后右肩疼痛加重，   │
│                 │                   │ 次日出现右肩活动受限， │
│                 │                   │ 以外展及上举为主...    │
│                 │                   │ 结合专科检查和辅助检查 │
│                 │                   │ 结果，诊断「骨化性肌炎」│
│                 │                   │ 是正确的。             │
├─────────────────┴───────────────────┴───────────────────────┤
│ 结果：✓ 医生正确  ✓ CHEESE正确                              │
│ 其他AI模型：GPT-5.1✗ DeepSeek-R1✗ Qwen3-235B✗ ...          │
└─────────────────────────────────────────────────────────────┘
```

### 示例2：管理任务对比（并排展示）

```
┌────────────────────────────────────────────────────────────────┐
│ 案例：围手术期风险评估                                          │
│ 患者ID: 453171276965683200                                     │
├────────────────────────────────────────────────────────────────┤
│ 医生的风险评估：              │ CHEESE的风险评估：            │
│                               │                               │
│ 1. 手术适应症：符合           │ 1. 手术适应症评估：           │
│ 2. 风险评估：                 │    患者右肩关节疼痛...符合    │
│    - 心血管风险：低           │                               │
│    - 出血风险：低             │ 2. 术前风险评估：             │
│    - 感染风险：中             │    - 心血管系统：血压、心率   │
│ 3. 需完善检查：               │      正常，无明显异常         │
│    - APTT                     │    - 呼吸系统：无异常         │
│    - C反应蛋白                │    - 凝血功能：需完善APTT    │
│                               │    - 炎症指标：需完善CRP      │
│                               │                               │
│                               │ 3. 手术风险：                 │
│                               │    综合评估为中等风险，建议   │
│                               │    完善上述检查后再决定...    │
│                               │                               │
│ AI评分：                      │ AI评分：                      │
│ 明确的判断(4,5)               │ 明确的判断(5,5)               │
├────────────────────────────────┴───────────────────────────────┤
│ 对比分析：                                                      │
│ • 一致性：★★★���☆ 核心评估一致，CHEESE更详细                  │
│ • 完整性：医生简洁实用，CHEESE系统全面                          │
│ • 临床价值：两者均符合临床规范，各有侧重                        │
└────────────────────────────────────────────────────────────────┘
```

### 示例3：统计对比图

```
┌─────────────────────────────────────────────┐
│ 诊断任务准确率对比                           │
├─────────────────────────────────────────────┤
│                                             │
│  100% ┤ ████████████ CHEESE (35/35)        │
│       ┤                                     │
│   80% ┤ ████████░░░░ 医生 (28/35)          │
│       ┤                                     │
│   60% ┤                                     │
│       ┤                                     │
│   40% ┤                                     │
│       ┤                                     │
│   20% ┤                                     │
│       ┤                                     │
│    0% ┤ ░░░░░░░░░░░░ GPT-5.1 (0/35)        │
│       ┤ ░░░░░░░░░░░░ DeepSeek-R1 (0/35)    │
│       └─────────────────────────────────    │
│                                             │
│  在35个CHEESE优势案例上的表现               │
└─────────────────────────────────────────────┘
```

## 🔧 制作对比图的工具推荐

### Python可视化

```python
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 准备数据
data = {
    '模型': ['CHEESE', '医生', 'GPT-5.1', 'DeepSeek-R1', 'Qwen3-235B', 'Kimi-K2', 'Grok-4'],
    '正确数': [35, 28, 0, 0, 0, 0, 0],
    '总数': [35, 35, 35, 35, 35, 35, 35]
}

df = pd.DataFrame(data)
df['准确率'] = df['正确数'] / df['总数'] * 100

# 绘制条形图
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(df['模型'], df['准确率'], color=['#2ecc71', '#3498db', '#e74c3c', '#e74c3c', '#e74c3c', '#e74c3c', '#e74c3c'])

# 添加数值标签
for i, (bar, value) in enumerate(zip(bars, df['准确率'])):
    ax.text(value + 2, bar.get_y() + bar.get_height()/2, 
            f'{value:.0f}% ({df.iloc[i]["正确数"]}/{df.iloc[i]["总数"]})',
            va='center', fontsize=10)

ax.set_xlabel('准确率 (%)', fontsize=12)
ax.set_title('诊断任务准确率对比\n(35个CHEESE优势案例)', fontsize=14, fontweight='bold')
ax.set_xlim(0, 110)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('cheese_advantage_comparison.png', dpi=300, bbox_inches='tight')
plt.show()
```

### Word表格

可以直接在Word中制作对比表格：
1. 插入3列表格
2. 列标题：标准答案 | 医生答案 | CHEESE答案
3. 从文档中复制粘贴内容
4. 美化格式（边框、底色、字体）

### PowerPoint对比图

适合在论文Presentation中展示：
1. 使用SmartArt图形
2. 选择"对比"或"流程图"布局
3. 左侧：医生答案
4. 右侧：CHEESE答案
5. 中间：标准答案（或对比箭头）

## 📈 推荐的对比展示方式

### 用于Nature论文

#### 主图(Main Figure)
- **Panel A**: 准确率对比条形图（CHEESE vs 医生 vs 其他AI模型）
- **Panel B**: 典型案例对比（2-3个代表性案例的详细对比）
- **Panel C**: 任务分布热力图（各任务上的表现）

#### 补充材料(Extended Data)
- **Extended Data Fig X**: 所有35个案例的详细对比表格
- **Extended Data Table X**: 医生与CHEESE的一致性分析
- **Extended Data Fig Y**: 管理任务质量评分对比

### 用于Presentation

#### 幻灯片1：总体对比
- 标题：CHEESE在骨科诊断中的优势
- 内容：准确率对比图 + 核心数据

#### 幻灯片2-4：典型案例展示
- 每个幻灯片展示1个案例
- 左侧：病历信息
- 右侧：三栏对比（标准答案 | 医生 | CHEESE）
- 底部：对比分析

#### 幻灯片5：管理任务对比
- 开放式任务的质量对比
- AI评分对比

## 🎯 关键对比指标

### 定量指标
- **准确率**：医生 vs CHEESE在35个优势案例上
- **一致性**：医生与CHEESE答案的一致率
- **响应时间**：医生完成时间 vs CHEESE推理时间

### 定性指标
- **推理质量**：推理过程的完整性和逻辑性
- **临床价值**：答案的临床适用性
- **可解释性**：推理过程的可理解程度

## 📝 注意事项

1. **保护隐私**：所有展示的病历数据已脱敏
2. **公平对比**：基于相同案例，避免cherry-picking
3. **说明背景**：标注这些是CHEESE优势案例
4. **客观分析**：承认医生在某些案例上的优势
5. **临床意义**：强调对临床实践的价值

---

**文件位置**：
- Word文档：`医生评测问卷_CHEESE优势展示.docx`
- JSON数据：`selected_cases_cheese_advantage.json`
- 本指南：`comparison_display_guide.md`
