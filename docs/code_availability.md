# Code availability

This repository contains a public source release for OrthoPilot and CHEESE. It is designed for code review, method inspection and lightweight execution checks with a synthetic demo.

## Included assets

- `demo/`: deterministic synthetic demo.
- `orthopilot_agent/`: OrthoPilot agent runtime, skills and configuration templates.
- `tool_plaza/`: Tool Plaza interface templates and MCP-style server adapters.
- `cheese/`: CHEESE training, inference, distillation and evaluation scripts.
- `oracle/`: ORACLE-style open-response evaluation framework code.
- `prompts/`: agent, tool-use and evaluation prompt templates.

## Excluded assets

The public release intentionally excludes the following assets:

- patient-level clinical records;
- source benchmark tables and patient-derived evaluation datasets;
- model weights, checkpoints, LoRA adapters and intermediate training outputs;
- retrieval indexes, vector databases and local cache files;
- hospital-specific deployment secrets, API keys and private endpoints;
- manuscript analysis scripts;
- plotting code;
- figure generation;
- table export;
- reader-study case selection;
- benchmark data construction;
- calibration scripts;
- paper-result builders;
- generated outputs, logs and large binary artifacts.

These exclusions protect patient privacy, institutional security and controlled research assets. They also keep the repository focused on source inspection and lightweight reproducibility checks.

## Configuration placeholders

Sensitive or site-specific values are represented by placeholders such as `OPENAI_API_KEY`, `https://api.openai.com/v1`, `localhost`, `8000`, `checkpoints/model`, `data/input.jsonl` and `outputs/output.jsonl`.

Provide real values through environment variables or local configuration files that are not committed to version control.

## Reproducibility boundary

The included synthetic demo verifies installation and repository wiring. It does not reproduce manuscript performance metrics. Exact numerical reproduction requires controlled clinical data, checkpoints, retrieval indexes and evaluator inputs described in the manuscript.
