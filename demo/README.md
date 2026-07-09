# Demo

This directory contains public synthetic demos for reviewers. They do not use real patient data, model weights, private services or committed API keys.

## Deterministic demo

From the repository root:

```bash
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
```

The generated JSON should match `demo/expected_output.json` except for formatting. This demo should finish in less than one minute on a normal desktop CPU.

## ReAct-style agent demo

The ReAct-style demo shows the agent loop with a synthetic case, public placeholder tools and either a deterministic scripted backend or an OpenAI-compatible model endpoint.

Run without external services:

```bash
python demo/run_react_agent_demo.py \
 --input demo/react_case.json \
 --output react_demo_output.json
```

Run with an API provider:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
python demo/run_react_agent_demo.py \
 --backend openai \
 --input demo/react_case.json \
 --output react_demo_output.json
```

Run with a local OpenAI-compatible vLLM server:

```bash
export OPENAI_API_KEY="EMPTY"
export OPENAI_BASE_URL="http://localhost:8000/v1"
export OPENAI_MODEL="local-model-name"
python demo/run_react_agent_demo.py \
 --backend openai \
 --input demo/react_case.json \
 --output react_demo_output.json
```

## Scope

The deterministic demo is a miniature representation of the OrthoPilot data flow. The ReAct-style demo shows action, observation and final-answer wiring for public inspection. Both demos use synthetic musculoskeletal cases only. They are not clinical decision support tools and are not reproduction scripts for manuscript results.
