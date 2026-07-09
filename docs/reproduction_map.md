# Reproduction map

This file maps manuscript components to the code paths in this repository. Exact numerical reproduction requires controlled-access clinical datasets, model checkpoints and deployment infrastructure that are not included in this public code release.

| Manuscript component | Code path | Required inputs | Public demo available |
| --- | --- | --- | --- |
| OrthoPilot hierarchical agent workflow | `orthopilot_agent/` | Agent configs, prompts, model endpoint, Tool Plaza services | `demo/run_demo.py` gives a deterministic miniature workflow |
| Tool Plaza evidence retrieval | `tool_plaza/` | Hospital data services, external search services, configured endpoints | Simulated evidence in `demo/synthetic_case.json` |
| CHEESE inference and evaluation | `cheese/inference/`, `cheese/evaluation/` | Model checkpoint or OpenAI-compatible endpoint, task JSONL input | Command templates in `README.md` |
| CHEESE training and distillation | `cheese/training/`, `cheese/distillation/` | Controlled training data, model weights, GPU training environment | Not reproducible from public assets alone |
| ORACLE open-response scoring | `oracle/` | Rubrics, model endpoint or evaluator setup, response files | Help command documented in `README.md` |
| OrthoBench construction and visualization | `orthobench/` | Controlled benchmark source tables | Scripts are included; source data are controlled-access |
| Retrospective and reader-study analyses | `analyses/` | Manuscript analysis tables and reader-study files | Figure scripts are included where data access is permitted |

## Reviewer demo

Run the synthetic demo to verify installation and repository wiring without private data or model services:

```bash
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
```

The output should match `demo/expected_output.json` except for insignificant JSON formatting differences.
