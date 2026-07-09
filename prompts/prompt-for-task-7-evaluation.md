# Prompt for Task 7 Evaluation

**Source files**
- `/path/to/orthopilot/gen_validation/task7promt.py`
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
Task name: surgical plan prediction.

Concern definitions:
- Initial preparation before incision
  - `primary`: describe completion of general anesthesia and routine disinfection and draping of the operative field.
  - `secondary`: describe patient positioning.
  - `additional`: describe special preparatory handling such as tourniquet placement.
- Entry phase
  - `primary`: describe the incision site and approach, including layered opening of skin, subcutaneous tissue, fascia, and exposure of the target site.
  - `secondary`: report incision length.
  - `additional`: describe special exposure maneuvers used to access the joint or deep operative field.
- Lesion management
  - `primary`: describe the entry point, implanted material, and fixation process.
  - `secondary`: describe resected tissue or released soft tissue.
  - `additional`: report fluoroscopic confirmation or satisfactory implant positioning.
- Irrigation and closure
  - `primary`: describe wound irrigation and routine or layered closure.
  - `secondary`: mention pressure dressing or equivalent closure-related measures.
  - `additional`: indicate completion of the operative procedure.

Criteria-generation guidance:
Construct the rubric so that every item belongs to one and only one concern level. Avoid duplicated extraction of the same operative detail. If a category or level is absent, keep it as an empty list.

Judging guidance:
For each rubric item, determine whether the student answer covers it. Preserve the original rubric structure, use a strict medical-school grading standard, and return valid JSON only.

## Scoring weights
```json
{
  "Initial preparation before incision": {"primary": 5, "secondary": 2, "additional": 1},
  "Entry phase": {"primary": 5, "secondary": 2, "additional": 1},
  "Lesion management": {"primary": 5, "secondary": 2, "additional": 1},
  "Irrigation and closure": {"primary": 5, "secondary": 2, "additional": 1}
}
```