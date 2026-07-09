# Prompt for Task 8 Evaluation

**Source files**
- `oracle/task8promt.py`
- `oracle/task_all_gen_async.py`

## Rewritten prompt
Task name: postoperative orders.

Concern definitions:
- Nursing and diet
 - `primary`: specify the nursing level and the basic dietary recommendation.
 - `secondary`: none expected as an independent rubric level for this concern.
 - `additional`: provide individualized fasting or dietary advice according to the procedure and patient status.
- Vital-sign monitoring and surgical-site care
 - `primary`: state that vital signs should be monitored.
 - `secondary`: include routine wound-care measures such as observing bleeding or drainage, limb immobilization, or dressing change.
 - `additional`: add special orders related to the postoperative course, such as drain care.
- Laboratory tests
 - `primary`: recommend standard postoperative laboratory reassessment.
 - `secondary`: add individualized tests based on the diagnosis and comorbidities.
 - `additional`: none expected.
- Imaging follow-up
 - `primary`: recommend standard postoperative imaging reassessment.
 - `secondary`: add individualized imaging or cardiopulmonary follow-up when indicated by the diagnosis or comorbidities.
 - `additional`: none expected.
- Drug therapy
 - `primary`: recommend standard postoperative analgesia and antibiotic use.
 - `secondary`: add symptom-directed treatment based on comorbidities or test results, and nutritional support when appropriate.
 - `additional`: provide concrete drug names or dosing details.
- Consultation
 - `primary`: none expected as a routine requirement.
 - `secondary`: request rehabilitation or medical consultation when indicated by the procedure or severe comorbidity.
 - `additional`: state the specific consultation purpose.

Criteria-generation guidance:
Build the rubric across all six concern categories. Use empty lists when a level is intentionally absent. Preserve the concern hierarchy even when one level is conceptually unused.

Judging guidance:
Judge coverage item by item using the supplied rubric. Keep the exact structure, including empty branches, and return valid JSON only.

## Scoring weights
```json
{
 "Nursing and diet": {"primary": 5, "secondary": 2, "additional": 1},
 "Vital-sign monitoring and surgical-site care": {"primary": 5, "secondary": 2, "additional": 1},
 "Laboratory tests": {"primary": 5, "secondary": 2, "additional": 1},
 "Imaging follow-up": {"primary": 5, "secondary": 2, "additional": 1},
 "Drug therapy": {"primary": 5, "secondary": 2, "additional": 1},
 "Consultation": {"primary": 5, "secondary": 2, "additional": 1}
}
```