# Prompt for Main Agent Summarization

**Source files**
- `prompts/prompt-for-main-agent-system.md`
- `orthopilot_agent/miroflow_core/core/orchestrator.py`

**Runtime note**
- This prompt is used when the main-agent session ends or reaches a con or turn limit.
- The appendix version converts the original reference label into an English `References` section.

## Rewritten prompt
This is the final response stage. No further tool use is allowed under any circumstances.

Produce a complete report that answers the original question using everything collected during the session. If the task ended because of a limit or failure, say so clearly. If a valid answer was already established earlier, extract that answer rather than recomputing it. If the evidence remained incomplete, provide the best supported conclusion available and mark unresolved uncertainty explicitly.

Your summary should include the full reasoning trail that matters for the final answer: the main evidence gathered, relevant intermediate findings, important partial results, contradictions, and any directly useful facts or quotations. If the task could not be fully resolved, preserve the partial findings so that a downstream reader could continue from them.

Organize the answer into clear sections with specific headings. End with a `References` section listing all useful URLs as markdown links.

All reasoning must remain inside `<think>...</think>`. After `</think>`, output the entire final report inside `\boxed{...}`. Do not output a short boxed answer and a separate long answer. The boxed content must contain the full structured report.