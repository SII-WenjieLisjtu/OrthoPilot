# Prompt for Task 5 Evaluation

**Source files**
- `/path/to/orthopilot/gen_validation/task5promt.py`
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
Task name: perioperative readiness assessment.

Concern definitions:
- Clear surgical decision
  - `primary`: state explicitly whether surgery can proceed.
  - `secondary`: if surgery should not proceed yet, state the reason or the required corrective step.
  - `additional`: note special patient-specific risks, such as infectious exposure or major comorbid risk factors.

Criteria-generation guidance:
Build a complete rubric covering all concern categories. Each extracted item must be assigned to `primary`, `secondary`, or `additional`, with no overlap between levels. Empty levels must remain empty lists. Split compound recommendations into separate items and attach a short reason for each classification.

Judging guidance:
Given a student answer and the rubric, decide whether each rubric item is covered. Use a strict clinical grading standard, but allow close paraphrases when the clinical meaning is retained. Preserve the rubric structure exactly and return valid JSON only.

## Scoring weights
```json
{
  "Clear surgical decision": {"primary": 5, "secondary": 2, "additional": 1}
}
```