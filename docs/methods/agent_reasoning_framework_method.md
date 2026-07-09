# Agent Reasoning Framework（Methods 初稿）

## 分层多Agent推理架构

OrthoPilot采用分层多agent架构（hierarchical multi-agent architecture）实现临床推理的自动化。系统由中央编排器（Orchestrator）驱动，其核心为主agent（CHEESE），负责高层临床推理规划、证据需求分析与多源证据综合。主agent将复杂的临床问题分解为若干独立的证据检索子任务，并委托给专用子agent（worker agent）执行。子agent在隔离的会话环境中自主完成证据收集后，生成结构化证据摘要返回主agent。这种分层设计将临床推理中的"规划与决策"和"证据获取与分析"两个认知过程显式解耦：主agent专注于临床逻辑推演与证据综合判断，子agent专注于从异构数据源中高效检索与提炼信息，两者通过结构化的任务委托与摘要传递协同工作。

## Tool Plaza：双证据世界的工具抽象

为统一建模异构医学数据源的访问接口，我们提出工具广场（Tool Plaza）的抽象层。形式化地，agent可调用的工具集合定义为：

$$\mathcal{T} = \mathcal{T}_{\text{in}} \cup \mathcal{T}_{\text{ext}} \cup \mathcal{T}_{\text{mm}}$$

其中，院内工具集 $\mathcal{T}_{\text{in}}$ 封装了电子病历系统中的结构化与非结构化数据访问能力，包括影像学检查报告查询、实验室检验结果获取、病理诊断报告检索、多学科会诊记录访问以及基于语义相似度的院内相似病例检索。院外工具集 $\mathcal{T}_{\text{ext}}$ 提供了循证医学知识的检索通道，涵盖医学知识图谱查询、循证文献检索（PubMed、医学教材、临床指南数据库）以及开放网络搜索。多模态工具集 $\mathcal{T}_{\text{mm}}$ 封装了医学影像的视觉理解能力，支持对X光、CT、MRI等影像数据的视觉问答。所有工具均通过统一的消息传递协议（Model Context Protocol, MCP）封装为标准化服务端点，agent以声明式方式调用工具而无需感知底层实现差异。这一双证据范式（dual-evidence paradigm）具有明确的临床意义：院内证据锚定患者级别的个体化事实，院外证据提供基于群体研究的、可持续更新的循证支撑，两者的交叉验证与综合是可靠临床推理的基础。

## 迭代推理循环的形式化

给定临床问题 $q$ 和患者上下文 $c$，主agent的推理过程被建模为一个迭代决策过程。在第 $t$ 步，主agent基于当前的交互历史选择下一步动作：

$$a_t = \pi_\theta(q, c, h_{<t}), \quad a_t \in \{\texttt{delegate}(\tau_k, \mathcal{T}_{\text{sub}}),\; \texttt{invoke}(f_j),\; \texttt{synthesize}\}$$

其中 $\pi_\theta$ 为主agent的策略函数，$h_{<t}$ 为截至第 $t$ 步的完整交互历史。动作空间包含三类操作：$\texttt{delegate}$ 将子任务 $\tau_k$ 委托给子agent执行，$\texttt{invoke}$ 直接调用工具 $f_j \in \mathcal{T}$，$\texttt{synthesize}$ 终止检索并进入最终综合阶段。当主agent选择委托操作时，子agent在独立会话中基于分配的子任务与可用工具集迭代执行证据收集：

$$e_k = \phi_\theta(\tau_k, \mathcal{T}_{\text{in}} \cup \mathcal{T}_{\text{ext}})$$

其中 $\phi_\theta$ 为子agent的执行策略，$e_k$ 为其返回的结构化证据摘要。最终，当所有必要证据收集完毕后，主agent综合全部证据生成结构化临床建议：

$$r = g_\theta\big(q, c, \{e_1, \ldots, e_K\}\big)$$

我们在推理循环中施加了严格的顺序工具调用约束（sequential tool-use constraint）：每一推理步仅允许执行一次工具调用。这一设计的动机在于确保因果推理链条的完整可追溯性——每一步的工具选择决策均基于前序步骤的完整信息，形成线性可审计的推理轨迹，这对于临床场景下的决策解释性至关重要。此外，系统实现了主动终止策略（early termination）：当主agent判断已收集充分证据、或检测到当前查询与历史查询高度相似时，将主动终止检索循环进入综合阶段，避免冗余工具调用。

## 子Agent机制与信息流

主agent通过任务委托机制将复杂临床问题分解为可独立执行的子任务。在架构实现上，子agent被封装为Tool Plaza中的虚拟工具端点，使得主agent以统一的工具调用语义完成任务委托，无需区分工具调用与agent委托的接口差异。子agent接收到子任务描述后，在隔离的会话环境中自主运行其推理循环，迭代调用Tool Plaza中的工具完成证据收集。子agent完成执行后，生成结构化证据摘要作为返回结果。这一设计引入了两个关键的信息流约束：其一，会话隔离（session isolation），各子agent的会话上下文相互独立，防止跨任务的信息泄露与上下文污染；其二，信息压缩（information compression），主agent接收的是子agent生成的结构化摘要而非完整的对话日志，实现了信息的有效压缩与噪声过滤，使主agent能够在有限的上下文窗口内高效整合来自多个子agent的证据。
