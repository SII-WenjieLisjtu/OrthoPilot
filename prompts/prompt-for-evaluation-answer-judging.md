# Prompt for Evaluation Answer Judging

**Source files**
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
You are given a student answer and an evaluation rubric for one clinical task. For every rubric item, determine whether the student answer covers that content.

Work item by item inside the existing rubric structure. For each entry, add:
- a boolean coverage field
- a short explanation of the coverage decision

Follow these rules:
1. Judge against the rubric content itself rather than rewriting the rubric.
2. Skip rubric branches that are intentionally empty.
3. Count approximate mention as covered when the medical meaning is sufficiently aligned.
4. Ignore overly specific details that are not essential to the patient-facing clinical content, such as precise time points or equipment naming, unless they are central to the rubric item.
5. Preserve the original rubric structure and keys.
6. Remove classification-rationale fields from the output.

Return valid JSON only.