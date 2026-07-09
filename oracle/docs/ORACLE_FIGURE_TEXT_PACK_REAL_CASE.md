# ORACLE Figure Real Case Text Pack

## Titles
- Eval example
- Ground-truth answer
- Model response
- ORACLE evaluation framework
- Physician rubric
- LLM extraction
- Scoring sheet

## Eval example
- Male, 18 years old, admitted for recurrent right shoulder dislocation.
- Postoperative day 1 after arthroscopic labral repair and capsular reconstruction.
- Right shoulder pain, limited range of motion, peri-incisional tenderness, and resting NRS pain score 2–3.
- Consultation question: please assess the patient and propose a rehabilitation plan addressing pain management, functional recovery, and ADL support.

## 中文核对
- 男性，18岁，因右肩复发性脱位入院。
- 关节镜下盂唇修复及肩关节囊重建术后1天。
- 右肩疼痛、活动受限、术区压痛，静息疼痛NRS 2–3分。
- 会诊问题：请评估患者情况，并提出后续康复方案，覆盖疼痛管理、功能恢复及ADL干预。

## Ground-truth answer
- Postoperative right shoulder pain with limited range of motion after labral repair and capsular reconstruction.
- Peri-incisional tenderness, resting NRS pain score 2–3, and preserved distal strength.
- Recommend systematic rehabilitation evaluation and treatment to relieve pain, maintain strength, improve shoulder range of motion, and support ADL recovery.
- Follow-up assessment and escalation advice should also be included.

## 中文核对
- 盂唇修复及肩关节囊重建术后存在右肩疼痛和活动受限。
- 伴术区压痛、静息NRS 2–3分，远端肌力尚可。
- 建议进行系统性康复评定与治疗，以缓解疼痛、维持肌力、改善肩关节活动度并促进ADL恢复。
- 还应包含随访评估及病情加重时的处理建议。

## Model response
- Postoperative day 1 after right shoulder labral repair and capsular reconstruction.
- Right shoulder pain, limited range of motion, peri-incisional tenderness, and resting NRS pain score 2–3.
- An individualized rehabilitation plan is needed to support functional recovery.

## 中文核对
- 右肩盂缘修复及肩关节囊重建术后1天。
- 存在右肩疼痛、活动受限、术区压痛，静息疼痛NRS 2–3分。
- 需制定个体化康复方案以促进功能恢复。

## Physician rubric
### Concern 1: Current status
- Primary: current discomfort and relevant history
- Secondary: examination / test results and current medication
- Additional: sex, age, and other history

### Concern 2: Treatment recommendations
- Primary: summary of current status and treatment plan
- Secondary: additional tests or examinations
- Additional: follow-up or escalation advice

## 中文核对
### Concern 1: Current status / 具体情况
- Primary：当前不适与相关病史
- Secondary：检查结果与目前用药
- Additional：性别、年龄及其他病史

### Concern 2: Treatment recommendations / 治疗建议
- Primary：当前情况总结与治疗方案
- Secondary：补充检验检查
- Additional：随访或病情加重时的建议

## LLM extraction label
- LLM extracts criterion entities from the ground-truth answer under the physician rubric.

## 中文核对
- LLM在医生rubric约束下，从GT回答中提取criterion实体。

## Scoring sheet headers
- Criterion
- Concern
- Level
- Present in response

## Scoring sheet rows
- Postoperative right shoulder pain and limited range of motion | Current status | Primary | Yes
- Peri-incisional tenderness, resting NRS pain score 2–3, and preserved distal strength | Current status | Secondary | Yes
- No medication information mentioned | Current status | Secondary | Yes
- No other past medical history mentioned | Current status | Additional | Yes
- Systematic rehabilitation evaluation and treatment for pain relief, strength maintenance, range-of-motion recovery, and ADL improvement | Treatment recommendations | Primary | Yes
- Rehabilitation 5 days/week, twice daily, with gentle technique | Treatment recommendations | Secondary | No
- Follow-up assessment and escalation advice | Treatment recommendations | Additional | No

## 中文核对
- 术后右肩疼痛及活动受限 | 具体情况 | 主要 | 是
- 术区压痛、静息NRS 2–3分及远端肌力尚可 | 具体情况 | 次要 | 是
- 未提及用药信息 | 具体情况 | 次要 | 是
- 未提及其他既往病史 | 具体情况 | 附加 | 是
- 系统性康复评定与治疗，以缓解疼痛、维持肌力、改善活动度和ADL | 治疗建议 | 主要 | 是
- 康复每周5天、每日2次且手法轻柔 | 治疗建议 | 次要 | 否
- 随访评估及病情加重时的处理建议 | 治疗建议 | 附加 | 否
