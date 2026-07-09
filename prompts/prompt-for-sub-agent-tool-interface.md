# Prompt for Sub-Agent Tool Interface

**Source files**
- `/path/to/orthopilot/MiroFlow/config/agent_prompts/sub_worker.py`
- `/path/to/orthopilot/MiroFlow/src/utils/tool_utils.py`

## Rewritten prompt
A worker agent may be invoked as a tool when a single, well-bounded subtask needs independent evidence gathering or execution.

Provide a concise but complete subtask description. The request should define one objective, include the local background needed to act correctly, and avoid vague instructions such as “look into this generally.” The worker can search, inspect files, use tools, and return a synthesized report, but it is not intended for broad or speculative delegation.

Expected input schema:

```json
{
  "subtask": "A clearly scoped objective with enough context to execute independently."
}
```

Expected output behavior:
- returns a processed summary rather than a raw dump of search results
- focuses on the assigned subtask only
- avoids unsupported inference when exact evidence is unavailable
- reports uncertainty explicitly when needed