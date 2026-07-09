# Reproduction map

This file maps retained public source components to the framework workflows described in the OrthoPilot manuscript. The public release supports source inspection and a deterministic synthetic demo. Exact numerical reproduction requires controlled clinical datasets, model checkpoints, retrieval indexes, evaluation rubrics and deployment infrastructure that are not included.

| Public framework component | Public code path | Required private or controlled inputs | Public demo available |
| --- | --- | --- | --- |
| OrthoPilot agent framework | `orthopilot_agent/` | Agent configuration, model endpoint, Tool Plaza services and clinical context inputs | `demo/run_demo.py` gives a deterministic miniature workflow |
| Tool Plaza evidence interfaces | `tool_plaza/` | Hospital data services, external knowledge services, configured endpoints and credentials | Simulated evidence fields in `demo/synthetic_case.json` |
| CHEESE training and inference recipe | `cheese/` | Controlled training data, model checkpoint or OpenAI-compatible endpoint and task JSONL input | Command template in `README.md` |
| ORACLE evaluation framework | `oracle/` | Rubrics, response files, evaluator model endpoint and controlled task data | Source inspection only |
| Prompts | `prompts/` | Task-specific runtime configuration and governed input data | Prompt source inspection only |
| Synthetic demo | `demo/` | No private inputs | Fully runnable on CPU |

## Excluded result-building assets

The public release does not include manuscript analysis scripts, plotting code, figure generation, table export, reader-study case selection, benchmark data construction, calibration scripts or paper-result artifact builders. These materials depend on controlled patient-derived datasets or institution-specific research assets.

## Reviewer demo

Run the synthetic demo to verify installation and repository wiring without private data or model services:

```bash
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
```

The output should match `demo/expected_output.json` except for insignificant JSON formatting differences.

## Interpretation

The demo is a functional smoke test. It should not be interpreted as a clinical benchmark, a validation study or a reproduction of manuscript metrics.
