# Prompt for Evaluation Term Recall

**Source files**
- `/path/to/orthopilot/gen_validation/task_all_gen_async.py`

## Rewritten prompt
Extract the smallest shared core medical terms that overlap between the student answer and the reference answer.

Rules:
1. Return only basic medical terms rather than long phrases.
2. Light synonym normalization is allowed when needed to align equivalent wording.
3. Further segmentation is allowed if it improves term alignment.
4. Do not include specific laboratory item names, medication names, or other excluded overly detailed terms when they fall outside the intended recall scope.

Return valid JSON in the following shape only:

```json
{
  "student": ["term1", "term2"],
  "answer": ["term1", "term2"]
}
```