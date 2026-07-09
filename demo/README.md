# Demo

This directory contains a deterministic synthetic demo for reviewers. It does not use real patient data, model weights, private services or API keys.

## Run

From the repository root:

```bash
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
```

## Expected output

The generated JSON should match `demo/expected_output.json` except for formatting.

## Expected runtime

The demo should finish in less than one minute on a normal desktop CPU.

## Scope

The demo is a miniature representation of the OrthoPilot data flow. It loads a synthetic musculoskeletal case, collects simulated evidence fields and emits a structured management recommendation. It is not a clinical decision support tool.
