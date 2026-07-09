# Prompt for Task 9 Evaluation

**Source files**
- `oracle/task9promt.py`
- `oracle/task_all_gen_async.py`

## Rewritten prompt
Task name: discharge summary.

Concern definitions:
- Reason for admission
 - `primary`: state the admission timing, reason for admission, and main diagnosis.
 - `secondary`: include prior medical history or comorbidities.
 - `additional`: note that operative contraindications or special risks were excluded when applicable.
- Investigations and diagnosis
 - `primary`: summarize the main inpatient tests and the established diagnosis.
 - `secondary`: include key findings from the investigations.
 - `additional`: mention any special risk assessment or exclusion workup.
- Operative course
 - `primary`: report the operative date, procedure name, anesthesia method, and operative outcome.
 - `secondary`: report blood loss, special maneuvers, or notable operative materials.
 - `additional`: mention special implants, intraoperative complications, or the management of those complications.
- Postoperative condition
 - `primary`: describe general postoperative condition, wound healing, and the discharge readiness conclusion.
 - `secondary`: include vital signs or major monitored indicators.
 - `additional`: mention rehabilitation progress or caregiver-related support.
- Discharge instructions
 - `primary`: include precautions, medications, rehabilitation guidance, and timing of follow-up review.
 - `secondary`: provide medication dose, rehabilitation format, or follow-up interval details.
 - `additional`: provide individualized education, long-term follow-up, or lifestyle guidance.

Criteria-generation guidance:
Extract all rubric items from the reference answer and place them into the three-level structure for each concern. Use empty lists rather than placeholders when content is absent.

Judging guidance:
Decide whether each rubric item is covered by the student answer. Preserve the rubric structure and return valid JSON only.

## Scoring weights
```json
{
 "Reason for admission": {"primary": 5, "secondary": 2, "additional": 1},
 "Investigations and diagnosis": {"primary": 5, "secondary": 2, "additional": 1},
 "Operative course": {"primary": 5, "secondary": 2, "additional": 1},
 "Postoperative condition": {"primary": 5, "secondary": 2, "additional": 1},
 "Discharge instructions": {"primary": 5, "secondary": 2, "additional": 1}
}
```