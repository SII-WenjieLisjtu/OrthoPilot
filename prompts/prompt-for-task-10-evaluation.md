# Prompt for Task 10 Evaluation

**Source files**
- `/path/to/orthopilot/gen_validation/task10promt.py`
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
Task name: rehabilitation consultation and internal-medicine management.

Concern definitions:
- Exercise prescription: operative plan
  - `primary`: state the intraoperative diagnosis and the name of the procedure.
  - `secondary`: include sex, age, postoperative day, and the presence or absence of current discomfort.
  - `additional`: mention where plates, anchors, or injected agents were placed during the operation.
- Exercise prescription: rehabilitation recommendation
  - `primary`: describe wound tenderness or redness, joint-motion limitation, and relevant functional scores.
  - `secondary`: propose low-frequency electrical stimulation or mobilization and exercise therapy linked to the procedure.
  - `additional`: include balance or gait training when relevant, as well as training frequency and precautions.
- Internal-medicine management: brief history
  - `primary`: summarize current symptoms and relevant past history.
  - `secondary`: include current investigations and current medication use.
  - `additional`: add sex, age, or other history details.
- Internal-medicine management: management plan
  - `primary`: recommend medication or a treatment adjustment.
  - `secondary`: propose further testing.
  - `additional`: recommend outpatient follow-up when appropriate.

Criteria-generation guidance:
Extract all required rubric items from the reference answer, keeping concern categories and levels separate. Use empty lists where needed and provide a short rationale for each extracted item.

Judging guidance:
Mark each rubric item as covered or not covered in the student answer. Preserve the evaluation structure and return valid JSON only.

## Scoring weights
```json
{
  "Exercise prescription: operative plan": {"primary": 5, "secondary": 2, "additional": 1},
  "Exercise prescription: rehabilitation recommendation": {"primary": 2, "secondary": 2, "additional": 1},
  "Internal-medicine management: brief history": {"primary": 5, "secondary": 2, "additional": 1},
  "Internal-medicine management: management plan": {"primary": 5, "secondary": 2, "additional": 1}
}
```