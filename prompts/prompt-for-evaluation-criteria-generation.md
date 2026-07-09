# Prompt for Evaluation Criteria Generation

**Source files**
- `oracle/task_all_gen_async.py`
- `oracle/API_fast.py`

## Rewritten prompt
Given a reference answer for a specific clinical task, extract the complete scoring rubric under the predefined concern categories for that task.

For every concern category, organize the expected content into three non-overlapping levels:
- `primary`
- `secondary`
- `additional`

Follow these rules strictly:
1. Classify each item only according to the supplied concern definitions.
2. Keep the three levels mutually exclusive.
3. If a level has no valid item, return an empty list rather than fabricating content.
4. Split compound content into separate atomic items whenever possible.
5. Do not repeat the same item in more than one place.
6. For each extracted item, provide a short classification rationale explaining why it belongs to that concern and level.

Return valid JSON only. Do not include commentary outside the JSON structure.