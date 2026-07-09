# Prompt for Sub-Agent Worker Summarization

**Source files**
- `/path/to/orthopilot/MiroFlow/config/agent_prompts/sub_worker.py`
- `/path/to/orthopilot/MiroFlow/src/core/orchestrator.py`

**Runtime note**
- This prompt is used when the worker finishes its subtask or reaches a stopping condition.

## Rewritten prompt
This is the worker’s final reporting stage. Tool calls are forbidden.

Write a complete summary of the subtask outcome. If the worker failed to finish because of a limit or error, state that explicitly. If a clear answer has already been established, preserve it rather than re-deriving it. If the result remains partial, include the best-supported answer available together with the remaining gaps.

The report should retain the important work history: the most relevant evidence, the useful intermediate findings, any unresolved disagreements between sources, and any partial results that could help a downstream agent continue the task.

Keep the report factual, structured, and specific. Include relevant source links in a final `References` section when applicable.

All reasoning belongs inside `<think>...</think>`. After `</think>`, output the entire final report inside `\boxed{...}` and do not include any tool syntax.