# OrthoPilot

**Evidence-grounded AI for longitudinal clinical management in musculoskeletal care**

This repository contains the public source release for OrthoPilot, a research agent system for full-pathway musculoskeletal care. The release includes the agent runtime, Tool Plaza interface templates, CHEESE training and inference code, ORACLE evaluation framework code, prompt templates and a deterministic synthetic demo.

The repository is intended for code review, method inspection and lightweight execution checks. It is not a complete reproduction package for manuscript results. Patient-derived data, model weights, retrieval indexes, private service endpoints and paper-result artifact builders are not included.

## Public release scope

Included in this release:

- OrthoPilot agent runtime and configuration templates.
- Tool Plaza MCP-style interface templates.
- CHEESE training and inference scripts.
- ORACLE framework code for open-response evaluation.
- Prompt templates used by the agent and evaluation workflows.
- A deterministic synthetic demo that runs without private data or model access.

Excluded from this release:

- patient-level clinical records and patient-derived evaluation datasets;
- model weights, checkpoints, LoRA adapters and retrieval indexes;
- private hospital services, credentials, API keys and deployment endpoints;
- manuscript analysis scripts and plotting code;
- figure generation, table export, reader-study case selection, benchmark data construction and calibration scripts;
- large generated outputs, caches and logs.

## Repository contents

```
orthopilot/
|-- README.md
|-- LICENSE
|-- CITATION.cff
|-- requirements.txt
|-- demo/
|-- docs/
|-- orthopilot_agent/
|-- tool_plaza/
|-- cheese/
|-- oracle/
`-- prompts/
```

## System requirements

### Tested environment

The synthetic demo and repository checks were tested on:

- Operating system: Linux 5.15
- Python: 3.12.4
- Conda: optional. Any clean conda or virtualenv environment with Python 3.12 is suitable.
- Hardware for demo: standard CPU environment. No GPU is required.

### Optional hardware

Full CHEESE training, model inference, vLLM serving and large-scale evaluation require GPU infrastructure and model checkpoints that are not included in this public release. Hardware requirements depend on the selected model endpoint, checkpoint size and batch size.

## Installation

Use a clean Python 3.12 environment. The public release is organized into installation profiles so reviewers can run the synthetic demos without installing private-service or large-model dependencies.

### Minimal reviewer installation

Use this profile for source inspection, the deterministic demo and the ReAct-style synthetic demo without model access. These demo paths use the Python standard library.

```bash
python -m venv .venv
source .venv/bin/activate
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
python demo/run_react_agent_demo.py --input demo/react_case.json --output react_demo_output.json
```

Alternatively, with conda:

```bash
conda create -n orthopilot-demo python=3.12 -y
conda activate orthopilot-demo
python demo/run_demo.py --input demo/synthetic_case.json --output demo_output.json
python demo/run_react_agent_demo.py --input demo/react_case.json --output react_demo_output.json
```

Typical setup time on a normal desktop or workstation is less than five minutes. No GPU or private service is required for the synthetic demos. Install component-specific dependencies only when inspecting that component.

### Tool Plaza MCP adapter installation

Use this profile when inspecting or launching the MCP-style adapters under `tool_plaza/mcp_servers/`.

```bash
python -m venv .venv-tool-plaza
source .venv-tool-plaza/bin/activate
pip install -r tool_plaza/requirements.txt
```

This installs common adapter dependencies including `fastmcp`, `aiohttp`, `httpx`, `requests`, `openai`, `anthropic`, `pydantic` and `PyYAML`. Provider-specific adapters may require extra local runtimes such as Node/npm, `markitdown-mcp` or `google-genai`, as described in `tool_plaza/README.md`.

### Public Tool Plaza API server installation

Use this profile when running the retained public FastAPI tool server.

```bash
python -m venv .venv-tool-api
source .venv-tool-api/bin/activate
pip install -r tool_plaza/bone_tools_api/requirements.txt
bash tool_plaza/bone_tools_api/start_server.sh
```

Default endpoint:

```text
http://localhost:8766
```

The public API server can start without the excluded CPubMed and MedicalBook data files. When those files are absent, the corresponding tools are skipped and the remaining retained tools stay available.

### Optional model endpoint installation

The ReAct-style demo and several templates can use any OpenAI-compatible endpoint, including a local vLLM server. The repository does not include model weights.

API provider example:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

Local vLLM example:

```bash
export OPENAI_API_KEY="EMPTY"
export OPENAI_BASE_URL="http://localhost:8080/v1"
export OPENAI_MODEL="local-model-name"
```

Keep model paths, checkpoints, private endpoints and credentials outside version control. The ReAct demo reads `OPENAI_MODEL`; Tool Plaza MCP reasoning configs read `OPENAI_MODEL_NAME`; the public API server MedicalBook path reads `OPENAI_API_BASE` for its optional OpenAI-compatible base URL.

## Component-specific dependencies

| Component | Path | Main dependencies | Notes |
| --- | --- | --- | --- |
| Synthetic demos | `demo/` | Python standard library for deterministic mode; OpenAI-compatible HTTP endpoint optional for model mode | Runs on CPU. It does not require real patient data, private APIs or hospital services. |
| OrthoPilot agent runtime | `orthopilot_agent/` | OpenAI-compatible LLM clients, `pydantic`, `pyyaml`, `httpx` | Requires configured model endpoints and Tool Plaza services for full agent execution. |
| Tool Plaza MCP adapters | `tool_plaza/mcp_servers/` | `fastmcp`, `aiohttp`, `httpx`, `requests`, `openai`, `anthropic`, `pydantic`, `PyYAML`; optional provider runtimes as needed | Install `tool_plaza/requirements.txt`. Site-specific services and credentials must be configured locally. |
| Tool Plaza public API server | `tool_plaza/bone_tools_api/` | `fastapi`, `uvicorn`, `pydantic`, `requests`, `httpx`, `openai`, `pandas`, `numpy`, optional tool-specific packages | Install `tool_plaza/bone_tools_api/requirements.txt`. Large databases and private indexes are not included. |
| CHEESE training and inference | `cheese/` | `torch`, `transformers`, `datasets`, `accelerate`, `openai`, `requests`; training backends as needed | Requires local checkpoints or an OpenAI-compatible endpoint. Model weights and training data are not included. |
| ORACLE framework | `oracle/` | `openai`, `httpx`, `pydantic`, `pandas`, `tqdm` | Requires evaluator model access and controlled response/rubric files that are not included. |

For reviewer installation, start with the minimal profile and the deterministic demo. Install component-specific dependencies only for the workflow you need to inspect or run.

## Demo

Synthetic demos are provided in `demo/`. They use no real patient data, model weights, private services or committed API keys.

Run the deterministic wiring check from the repository root:

```bash
python demo/run_demo.py \
 --input demo/synthetic_case.json \
 --output demo_output.json
```

Expected runtime is less than one minute on a normal CPU. The generated JSON should match `demo/expected_output.json` except for formatting.

Run the public ReAct-style agent loop without external services:

```bash
python demo/run_react_agent_demo.py \
 --input demo/react_case.json \
 --output react_demo_output.json
```

Run the same ReAct-style loop with an OpenAI-compatible API or a local vLLM server by setting `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL`, then passing `--backend openai`. The demo uses synthetic placeholder tools only. It is intended to show agent-loop wiring, not clinical use or manuscript-result reproduction.

## Instructions for use

### Run CHEESE inference with an OpenAI-compatible endpoint

```bash
python cheese/inference/inference_local.py \
 --input_file data/input.jsonl \
 --output_file outputs/output.jsonl \
 --model_name checkpoints/model-or-endpoint
```

Update model paths or endpoint settings before use. API keys should be provided through environment variables and should not be committed.

### Inspect ORACLE evaluation framework code

```bash
cd oracle/scripts
python task_all_gen_async.py --help
```

ORACLE scoring of open-ended clinical management responses requires rubric files, model access and response files prepared according to the method description. These controlled inputs are not included in the public release.

### Configure Tool Plaza interfaces

Detailed Tool Plaza installation and service configuration instructions are provided in `tool_plaza/README.md`.

A public service manifest is provided at `tool_plaza/service_manifest.json`. It records service roles, default local ports, health endpoints, environment variables and matching tool config files without private paths, credentials or database files.

Inspect service status:

```bash
bash tool_plaza/start_all_services.sh status
```

Start retained or locally supplied services:

```bash
bash tool_plaza/start_all_services.sh start
```

Stop services started by the public skeleton:

```bash
bash tool_plaza/start_all_services.sh stop
```

The public script starts only commands that are available in this release or explicitly supplied through environment variables such as `EHR_START_COMMAND`, `MEDRAG_START_COMMAND` or `VLLM_START_COMMAND`. Never commit credentials, hospital endpoints, model weights, private database paths or patient-derived files.

## Reproducing manuscript results

A code-to-component map is provided in `docs/reproduction_map.md`.

The public release supports method inspection and execution of the synthetic demo. Exact reproduction of quantitative manuscript results requires controlled clinical datasets, model checkpoints, retrieval indexes, evaluation rubrics and deployment infrastructure described in the manuscript. These assets are excluded because they contain patient-derived data or institution-specific resources.

## Data availability and privacy

This repository intentionally excludes:

- patient-level clinical records;
- raw or generated evaluation data derived from clinical records;
- model weights, checkpoints and LoRA adapters;
- retrieval indexes, vector databases and local cache files;
- hospital-specific deployment secrets, API keys and private endpoints;
- manuscript analysis outputs, generated figures and exported tables.

The included demo data are synthetic and do not correspond to any real patient.

## Code availability

See `docs/code_availability.md` for a summary of included and excluded assets.

## License

This software is released under the Apache License 2.0. See `LICENSE`.

## Citation

Citation metadata are provided in `CITATION.cff`. Please cite the associated manuscript if you use this code.

## Clinical-use disclaimer

This repository is provided for research review and reproducibility support. It is not a medical device and must not be used for clinical decision-making without appropriate validation, regulatory review and institutional approval.
