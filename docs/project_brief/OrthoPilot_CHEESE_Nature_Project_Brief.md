# OrthoPilot / CHEESE — Nature 正刊论文内容总纲（Project Brief）

> 目的：让团队里的其他 agent/协作者在不读全稿的情况下，快速对齐本文的**核心故事、系统方法、数据与实验、benchmark 与评测框架**，并能据此继续推进**多中心回顾性实验方案**与全文撰写。

---

## Abstract（原文完整保留）

Medical large language models have advanced rapidly, yet most existing agents remain confined to static dialogue and isolated tasks. This makes them difficult to embed into real clinical workflows and sustain evidence‑based decision making across an entire care pathway. Orthopaedic care spans triage, diagnosis, treatment selection, perioperative management, and rehabilitation follow‑up, with broad disease coverage and evidence distributed across in‑hospital multimodal examinations. Consequently, clinical agency and evidence‑grounded reasoning, along with the evolution of external medical knowledge, are critical requirements for any deployable intelligence in this domain. Here we present OrthoPilot, a clinical‑grade orthopaedic agent system, together with its core reasoning engine, CHEESE (Clinical Holistic Evidence‑to‑Execution Synthesis Engine), which is trained via reinforcement learning to acquire sequential decision-making capabilities spanning the entire care pathway. We built OrthoPilot by leveraging a comprehensive longitudinal orthopaedic cohort of 180,000 patients spanning 2004 to 2024, which integrates multimodal data (electronic health records, medical imaging, laboratory results). The system orchestrates multiple specialised agents that actively acquire key information and perform evidence‑based reasoning at critical decision points along the entire care pathway, thereby producing structured, actionable clinical recommendations. To evaluate OrthoPilot, we introduce a full-pathway clinical benchmark spanning patient cases from 1,000 diseases, including both common and rare conditions, across diverse care stages. We performed multicentre retrospective validation on 6,796 cases from 60 collaborating hospitals across regions and a prospective study of 4,621 cases from Ruijin Hospital. OrthoPilot achieved state‑of‑the‑art performance on most tasks, significantly outperforming existing medical LLMs and general‑purpose AI assistants. Furthermore, using open‑ended clinical queries and panel evaluation by orthopaedic specialists, we found that OrthoPilot generated more accurate, evidence‑grounded, and clinically preferable responses than baseline chatbots. As an interactive, multimodal AI copilot that seamlessly integrates patient‑specific context with external evidence, OrthoPilot may potentially find impactful applications in orthopaedic education, research, and human‑in‑the‑loop clinical decision making across the entire care continuum.
---

## 1. 一句话定位与核心主张

**我们提出临床级骨科智能体 OrthoPilot 与核心推理引擎 CHEESE，采用“院内信息世界 + 院外知识世界”的双证据范式支撑临床自主性与循证推理，使系统能贯穿骨科全流程关键节点生成可执行建议，并在大队列开发基础上完成多中心回顾性与单中心前瞻性验证，同时建立全流程临床级 benchmark 与评测框架。**

---

## 2. 关键问题与缺口（Why）

### 2.1 现有医学智能体的主要局限
- 多数仍停留在**静态对话**与**孤立任务**（单点 QA、单病种、单阶段），难以嵌入真实临床工作流并贯穿诊疗全过程。
- 临床级落地的瓶颈不是“能否生成答案”，而是：
  - **临床自主性（clinical agency）**：能在不同环节主动发现信息缺口、主动获取关键证据、持续推进下一步决策。
  - **循证能力（evidence-grounded reasoning）**：能将结论锚定在患者事实与外部医学证据上，适应外部知识的演进与更新。

### 2.2 为什么骨科是严苛且具有代表性的验证场景
- 诊疗链路长：从入院评估到出院与康复随访。
- 病种跨度大，决策节点密集。
- 证据形态复杂且分散：院内多模态（EHR、影像、检验、病理、会诊） + 院外循证知识（指南、文献、教材、决策库等）。

---

## 3. 系统方法（What & How）

### 3.1 系统组成
- **OrthoPilot**：临床级骨科智能体系统（统一智能体范式）。
- **CHEESE**：Clinical Holistic Evidence-to-Execution Synthesis Engine  
  - 定位：从“证据”到“临床行动建议”的推理引擎。
  - 训练：通过强化学习获得**跨阶段的序列决策能力**（贯穿整个 care pathway 的 decision-making）。

### 3.2 “工具广场 Tool Plaza”与双证据世界范式
我们将医疗系统抽象为两个互补的证据世界，并由 OrthoPilot 统一调度与整合：

#### A. 院内信息世界 In-hospital information world（患者上下文）
院内工具（与临床能动性相关）：
- 影像检查
- 检验检查
- 病理检查
- 科室会诊
- 相似病理检索

作用：稳定对齐患者级事实、补齐关键证据缺口、支撑跨环节一致性。

#### B. 院外知识世界 External knowledge world（循证与世界知识更新）
院外工具（检索与搜索）：
- 诊断指南搜索
- Google 搜索
- Wikipedia 搜索
- PubMed 搜索
- 教材搜索
- 临床决策库
- 知识图谱
- 医学书籍

作用：提供可更新的循证支撑、覆盖全病种知识、补齐外部依据。

---

## 4. 全流程任务图谱（Full-pathway task graph）

按时间顺序定义骨科全流程关键节点任务（用于 benchmark 构建与全体系评测）：

1. 入院诊断  
2. 术前医嘱预测  
3. 科室会诊（术前）  
4. 围手术期判断（能否手术/风险评估）  
5. 术前诊断（更精细诊断与鉴别）  
6. 手术方案预测  
7. 术中诊断  
8. 术后医嘱预测  
9. 科室会诊（术后）  
10. 出院总结  
11. 康复建议  

> 这些任务以开放式输出与结构化建议为主，贴近真实临床“建议—执行”的使用形态，而非单纯分类问题。

---

## 5. 数据与证据链（Data & Evidence）

### 5.1 大队列开发与系统化评估基础
- **瑞金医院 2004–2024 连续 20 年纵向全流程综合队列**
- **规模：180,000 骨科患者**
- **多模态整合：EHR、医学影像、检验结果**（及与全流程任务相关的医嘱/手术/出院/康复等记录）

用途：系统开发、全流程任务定义、benchmark 构建、内部评估与分析。

### 5.2 多中心回顾性外部验证
- **跨地区 60 家合作医院**
- **6,796 例回顾性病例**
用途：验证跨机构泛化能力与稳定性，避免仅在开发中心有效。

### 5.3 单中心前瞻性验证
- **4,621 例前瞻性实验**
用途：在接近真实工作流条件下验证可用性与稳定性。

---

## 6. Full-pathway clinical benchmark（Benchmark）

我们构建覆盖**全病种、全流程、关键决策节点**的临床级 benchmark：
- 覆盖不同疾病谱与临床阶段
- 覆盖院内多模态证据与院外循证证据的联合推理需求
- 以 11 个任务节点为统一评测接口，形成全流程评估闭环

---

## 7. 临床级评测框架（Evaluation Framework）

### 7.1 为什么不使用 BLEU/ROUGE 等机器翻译指标
- BLEU、ROUGE 等主要衡量**表面 n-gram 重合**，无法反映临床回答的**医学关键实体覆盖**与**临床可用性**。
- 临床问题的正确性往往取决于是否覆盖关键医学事实、诊断要点、处置要点，而非文本相似度。

### 7.2 我们提出的“Rubric → 打分表 → 关键实体覆盖”框架（核心思想）
总体思路：将评测从“文本相似”转为“关键医学实体覆盖与层级匹配”，并将医生 rubric 结构化、可规模化执行。

#### Step A：基于医生 rubric，从 GT 答案中自动提取“打分表 Scorecard”
- 输入：医生制定的 rubric（按任务类型/维度定义评判点） + 对应样本的 GT 答案。
- 方法：使用 LLM 将 GT 答案解析为**多维度打分表**（Scorecard）。
- 结构：打分表由多个维度组成（例如：具体情况、诊断依据、治疗建议、医嘱要点、随访/康复要点等，具体维度可按任务调整）。
- **最小评分单元**：每个维度被拆分为若干条关键医学实体或关键临床要点（key medical entities / key clinical items），来自 GT 中的可验证信息。
- 可扩展层级：每个维度内可进一步区分层级（例如 primary / secondary / additional），以匹配临床重要性。

输出：对每个样本生成一个结构化 scorecard（维度 × 关键实体条目 × 层级）。

#### Step B：评测阶段，从模型回答中提取“覆盖判定”
- 输入：模型回答 + 该样本对应的 scorecard。
- 方法：使用 LLM 判断模型回答是否**覆盖**每一条关键实体（覆盖 True/False 或覆盖程度标签）。
- 输出：得到每条关键实体的覆盖矩阵（按维度与层级组织）。

#### Step C：计算 Recall 与分层维度得分
- 对每个维度计算关键实体覆盖的 recall：
  - recall_dim = 覆盖的关键实体数 / 该维度关键实体总数
- 对层级分别计算 recall（例如 primary/secondary/additional），并可给出：
  - 分层得分：recall_primary、recall_secondary、recall_additional
  - 聚合得分：加权或非加权汇总为维度总分与样本总分
- 最终形成多粒度评测输出：
  - 样本级：总体 recall + 分维度 recall + 分层级 recall
  - 任务级：在全体样本上的均值/分布/置信区间
  - 全流程级：11 个节点任务的汇总与分解表现

> 该框架的核心优势：把临床评测从“文本相似”转为“关键医学要点是否覆盖”，且能够规模化、可解释地定位模型缺失项。

### 7.3 开放式问题与专家 Panel 评估（补充临床可信度证据）
- 在 benchmark 指标之外，使用开放式临床 query 集合与骨科专家 panel 盲评/排序偏好：
  - 评估准确性、循证性与临床偏好
- 用于验证系统在真实交互形态下的可用性与可接受性。

---

## 8. 实验与结果叙事（Experiments & Key Findings）

### 8.1 主实验：对比现有医学 LLM 与通用 AI 助手
- 在 full-pathway benchmark 的 11 个节点任务上进行系统评测
- OrthoPilot 在多数任务上达到 SOTA，并显著优于基线

### 8.2 多中心回顾性验证（60 院 6,796 例）
- 验证跨机构、跨地区泛化与稳定性
- 强调结果的外部可复现性

### 8.3 前瞻性验证（4,621 例）
- 在接近真实工作流的条件下验证系统表现与稳定性

### 8.4 专家 panel 结果
- 在开放式临床问题与盲评/排序中，OrthoPilot 被专家认为更准确、更循证、更符合临床偏好

---

## 9. 图表与写作材料规划（用于团队分工）

- **Figure 1（Intro 总览大图）**：双世界工具广场 + OrthoPilot/CHEESE + 底部 11 节点全流程任务链 + 180,000/60院6,796/4,621 证据块  
- **Figure 2（Benchmark）**：全流程 benchmark 覆盖图（病种 × 阶段 × 证据类型）  
- **Figure 3（主结果）**：11 节点任务表现总表与关键任务提升  
- **Figure 4（多中心外部验证）**：分中心/分地区稳定性展示  
- **Figure 5（前瞻性 + 专家评审）**：前瞻性结果 + 开放式专家偏好  
- **Extended Data**：亚组、错误分析、消融、案例、评分表构建与评测细则

---

## 10. 统一术语（团队写作必须一致）
英文：
- clinical-grade intelligence
- clinical agency
- evidence-grounded reasoning
- in-hospital information world
- external knowledge world
- Tool Plaza
- full-pathway clinical benchmark
- longitudinal cohort
- multicentre retrospective validation
- prospective study

中文：
- 临床级智能
- 临床自主性
- 循证推理/循证能力
- 院内信息世界
- 院外知识世界
- 工具广场
- 全流程临床级 benchmark
- 长期纵向队列
- 多中心回顾性验证
- 前瞻性实验

---

## 11. 给其他 agent 的执行清单（拿到即用）
- **写作**：围绕“静态问答不足 → 全流程临床自主性与循证能力 → 双世界范式 → 大队列与三层证据链验证”组织段落  
- **作图**：所有图都要体现“双世界 + OrthoPilot/CHEESE + 11 节点全流程”  
- **实验**：所有表格结果都能映射回 11 节点与 Scorecard-Recall 评测框架  
- **口径**：避免只讲单点任务提升，始终强调“临床自主性 + 循证推理 + 全流程能力 + 多中心/前瞻性证据链”

<!-- 我现在正在撰写nature正刊的多中心验证部分，你可以参考/path/to/orthopilot/project/OrthoPilot_CHEESE_Nature_Project_Brief.md文档中的一些大概项目信息，我们使用的内部验证数量有5905个患者的case，外部有60家医院总共6796个患者case的多中心验证，采用我们提出的Open Response Assessment for Clinical Language Evaluation（ORACLE）框架对开放式任务进行自动化评测。内部的基于瑞金医院的benchmark就是我们想提出来的对标openai healthbench的全流程临床benchmark，我希望你能够帮我基于摘要先帮我对院内推出的benchmark起一个好听的名字，类似healthbench这样。首先帮处理第一段的，针对提出的benchmark上的所有任务平均性能的我们模型CHEESE与其他模型的横向对比，表格路径为 /path/to/orthopilot/gen_validation/meta/subset/metrics_csv/all_tasks_models_summary.csv（task1-4为4个诊断任务），/path/to/orthopilot/gen_validation/meta/subset/metrics_csv/overall_summary.csv为后续task5-11的围手术期判断（能否手术/风险评估）、术前医嘱预测、手术方案预测、术后医嘱预测、出院总结、康复建议以及科室会诊。请你帮我将两个数据集的同模型的数据进行平均处理，然后帮我将所有模型分类，其中bone-14B-RL-v2是我们的CHEESE，另外我还希望你在总结完所有数据的均值之后加一个我们的agent系统的OrthoPilot的性能，其要比单模型性能提升很多，我希望绘制好看的气泡图进行对比，气泡大小代表模型的大小，将所有baseline分为多个类别，比如推理LLMS，general LLMs，medical LLMs等，按照nature正刊风格绘制非常美观的图 -->