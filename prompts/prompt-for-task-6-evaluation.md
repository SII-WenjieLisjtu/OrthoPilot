# Prompt for Task 6 Evaluation

**Source files**
- `/path/to/orthopilot/gen_validation/task6promt.py`
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
Task name: preoperative orders.

Concern definitions:
- Nursing and diet
  - `primary`: provide nursing and diet recommendations.
  - `secondary`: specify the nursing level and the type of diet.
  - `additional`: include individualized dietary or nursing precautions.
- Routine preoperative tests and examinations
  - `primary`: recommend the necessary standard laboratory and preoperative investigations.
  - `secondary`: recommend site-specific imaging or examinations for the involved limb or joint.
  - `additional`: add special tests justified by the current illness history.
- Disease-specific preoperative management
  - `primary`: propose examinations or tests required by the patient’s special medical circumstances.
  - `secondary`: provide corresponding medication orders.
  - `additional`: request specialist consultation when indicated by the findings.
- Preoperative preparation
  - `primary`: include fasting, skin preparation, medication readiness, and other standard preoperative preparation items.
  - `secondary`: describe the medication-preparation details more specifically.
  - `additional`: mention anti-inflammatory or fluid-related preparation details while avoiding allergens when relevant.
- Surgical plan
  - `primary`: state the planned procedure name.
  - `secondary`: list the intended devices or instruments.
  - `additional`: include any special operative circumstances.

Criteria-generation guidance:
Cover every concern category and keep the three rubric levels distinct. Use empty lists when a level has no support in the reference answer. Split bundled content into atomic rubric items and provide a short reason for each classification.

Judging guidance:
Mark each rubric item as covered or not covered in the student answer. Preserve the category structure and return valid JSON only.

## Scoring weights
```json
{
  "Nursing and diet": {"primary": 5, "secondary": 2, "additional": 1},
  "Routine preoperative tests and examinations": {"primary": 5, "secondary": 2, "additional": 1},
  "Disease-specific preoperative management": {"primary": 5, "secondary": 2, "additional": 1},
  "Preoperative preparation": {"primary": 5, "secondary": 2, "additional": 1},
  "Surgical plan": {"primary": 5, "secondary": 2, "additional": 1}
}
```