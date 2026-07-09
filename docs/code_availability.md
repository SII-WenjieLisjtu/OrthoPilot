# Code availability

This repository contains the source code, prompts, configuration templates and analysis scripts used to support the OrthoPilot manuscript.

## Included

- OrthoPilot agent runtime and configuration templates in `orthopilot_agent/`.
- Tool Plaza MCP-style server interfaces and tool configuration templates in `tool_plaza/`.
- CHEESE training, inference, distillation and evaluation scripts in `cheese/`.
- ORACLE open-response evaluation scripts in `oracle/`.
- OrthoBench construction and visualization scripts in `orthobench/`.
- Manuscript analysis scripts in `analyses/`.
- A deterministic synthetic demo in `demo/`.

## Not included

The public code release intentionally excludes patient-level clinical records, generated patient-derived evaluation data, model weights, LoRA adapters, retrieval indexes, vector databases, logs, caches, private endpoints and API keys.

## Configuration placeholders

Sensitive or site-specific values are represented by placeholders such as `YOUR_API_KEY`, `YOUR_API_BASE_URL`, `YOUR_HOST`, `YOUR_PORT`, `/path/to/model`, `/path/to/input.jsonl` and `/path/to/output.jsonl`.

Provide real values through environment variables or local configuration files that are not committed to version control.
