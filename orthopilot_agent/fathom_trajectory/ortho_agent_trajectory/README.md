# 医疗诊断轨迹工具说明

本仓库在原始 Fathom-DeepResearch 基础上补充了骨科诊断轨迹相关工具, 目标是
- 生成符合 `the OrthoPilot trajectory JSON schema` 规范的 JSON 轨迹;
- 在已有诊断结果的前提下补齐完整的搜索调用过程;
- 保持原项目代码最小侵入, 仅通过新增脚本实现。


---

## 1. 启动依赖服务 (与 `scripts/quick_inference.sh` 一致)
在运行任意脚本前, 请先在不同终端启动:

```bash
serving/start_fathom_search_4b.sh
serving/start_fathom_synthesizer_4b.sh   # 若只需轨迹生成可省略摘要模型
serving/host_server.sh 8904 256
```

其中 `host_server.sh` 会对医疗环境函数(`get_patient`, `search_guidelines` 等)进行实际执行。若有自定义端口, 对应地在脚本参数中调整 `--model-url` 与 `--executors`。

---

## 2. 两个核心脚本的定位
| 场景 | 使用脚本 | 说明 |
| --- | --- | --- |
| **从一个问题出发, 让模型全程推理并记录轨迹** | `medical_trajectory_generator.py` | 直接向 Fathom-Search 模型提问, 模型会自行决定调用工具和搜索。适合全流程生成新案例。 |
| **已握有最终诊断结果, 希望补全缺失的搜索步骤** | `trajectory_enhancer.py` | 读取现有轨迹, 构造医疗环境并驱动模型生成搜索调用, 最后把新的过程插入原轨迹。适合“还原”既有诊断数据。 |

两个脚本都依赖相同的模型 / 执行器服务, 只是入口和数据流不同:
- `medical_trajectory_generator.py` 需要一个自然语言问题 (`--question`) 并输出新的轨迹文件。
- `trajectory_enhancer.py` 需要已有的轨迹 JSON (`--input`), 解析其中的患者信息和最终诊断, 再补齐搜索步骤。

> 若仅需把原始轨迹补齐搜索过程, 直接使用 `trajectory_enhancer.py` 即可; 无需再调用生成器。

---

## 3. 常用命令
### 3.1 生成新的医疗轨迹
```bash
python3 medical_trajectory_generator.py \
  --question "患者入院, 请基于检查结果给出入院诊断与依据" \
  --model-url http://YOUR_HOST:YOUR_PORT \
  --executors http://YOUR_HOST:YOUR_PORT \
  --tokenizer FractalAIResearch/Fathom-Search-4B \
  --max-searches 5 \
  --output-path data/轨迹构建/T1/output/trajectory.json
```

### 3.2 补齐已有轨迹的搜索过程
```bash
python3 trajectory_enhancer.py \
  --input data/轨迹构建/T1/example_traj/patient_test_original.json \
  --output data/轨迹构建/T1/example_traj/patient_test_enhanced.json \
  --model-url http://YOUR_HOST:YOUR_PORT \
  --executors http://YOUR_HOST:YOUR_PORT \
  --max-searches 5
```
- `--dry-run` 可用于检查解析出的诊断/环境而不调用模型。
- `--force` 允许覆盖已存在的输出文件。

更新了新的，使用`trajectory_enhancer_r1.py`
---

## 4. 数据约定
- 输入与输出路径均位于 `data/轨迹构建/T1/` 下; 已有示例 `example_traj/patient_17082300000392_trajectory.json`。
- 轨迹文件需保持数组结构, 元素为 `{role, content}` 对象, 与 trajectory example兼容。
- 增强脚本会保留原始诊断文本, 仅在最终 `<answer>` 中加入对检索结果的引用。

---

## 5. 常见问题
- **出现“模型未生成任何带 search 的工具调用”**: 检查模型/工具服务是否就绪, 或适当调高 `--temperature`、放宽 `--max-new-tokens`。
- **需要自定义医疗工具返回值**: 修改 `trajectory_enhancer.py` 中 `build_env` 函数, 将真实接口返回写入 `PATIENT_DATA`/`GUIDELINE_RESULT` 等变量即可。
- **想完全手动编辑轨迹**: 直接修改对应 JSON 文件即可, 但需遵守 `<think>/<tool_call>/<tool_response>/<answer>` 标签格式。

---

## 6. 目录速览
- `medical_trajectory_generator.py`: 全流程生成脚本。
- `trajectory_enhancer.py`: 轨迹补齐脚本。
- `scripts/simple_example.sh`: 调用生成器的示例脚本。
- `data/轨迹构建/T1/`: 所有输入输出轨迹存放目录。

如需进一步扩展(例如新增实验脚本或批处理流程), 建议继续复用以上结构, 保持 README 为唯一说明文件。
