# Prompt for Task 11 Evaluation

**Source files**
- `oracle/task11promt.py`
- `oracle/task_all_gen_async.py`

## Rewritten prompt
Task name: other-specialty consultation assessment.

Concern definitions:
- Clinical situation
 - `primary`: summarize the patient's current symptoms or concerns and the relevant past medical history.
 - `secondary`: include current test results and current medication use.
 - `additional`: include sex, age, or other background history.
- Treatment recommendations
 - `primary`: summarize the present condition and propose medication or a treatment plan.
 - `secondary`: recommend supplementary tests or examinations.
 - `additional`: advise timely re-contact if the condition worsens, or specify outpatient follow-up after discharge.

Criteria-generation guidance:
Create a complete rubric across both concern categories. Keep `primary`, `secondary`, and `additional` separate. When a level has no valid content, return an empty list rather than filling it with placeholders.

Judging guidance:
For each rubric item, determine whether the student answer covers it. Use the same rubric structure in the output and return valid JSON only.

## Scoring weights
```json
{
 "Clinical situation": {"primary": 5, "secondary": 2, "additional": 1},
 "Treatment recommendations": {"primary": 2, "secondary": 2, "additional": 1}
}
```