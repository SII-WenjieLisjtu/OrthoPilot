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
- figure generation, table export, reader-study case selection, benchmark data construction, calibration scripts and paper-result artifact builders;
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

Create a clean Python environment and install the minimal dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Alternatively, with conda:

```bash
conda create -n orthopilot-demo python=3.12 -y
conda activate orthopilot-demo
pip install -r requirements.txt
```

Typical installation time on a normal desktop or workstation is 5 to 15 minutes, depending on network speed and cached packages.

The root `requirements.txt` is intended for the synthetic demo and lightweight source inspection. Install component-specific dependencies only for the workflow you need to inspect or run.

## Component-specific dependencies

| Component | Path | Main dependencies | Notes |
| --- | --- | --- | --- |
| Synthetic demo | `demo/` | Python standard library only | Runs on CPU. It does not require model weights, private APIs or hospital services. |
| OrthoPilot agent runtime | `orthopilot_agent/` | `mcp`, OpenAI-compatible LLM clients, `pydantic`, `pyyaml`, `httpx` | Requires configured model endpoints and Tool Plaza services for full agent execution. |
| Tool Plaza interfaces | `tool_plaza/` | `fastapi`, `uvicorn`, `pydantic`, `requests`, `httpx`, `openai`; optional tool-specific packages | Interface templates are provided. Site-specific services and credentials must be configured locally. |
| CHEESE training and inference | `cheese/` | `torch`, `transformers`, `datasets`, `accelerate`, `openai`, `requests`; training backends as needed | Requires local checkpoints or an OpenAI-compatible endpoint. Model weights and training data are not included. |
| ORACLE framework | `oracle/` | `openai`, `httpx`, `pydantic`, `pandas`, `tqdm` | Requires evaluator model access and controlled response/rubric files that are not included. |

For reviewer installation, start with the root `requirements.txt` and the deterministic demo. Install component-specific dependencies only when needed.

## Demo

A deterministic synthetic demo is provided in `demo/`. It uses no real patient data, no model weights and no private services.

Run from the repository root:

```bash
python demo/run_demo.py \
 --input demo/synthetic_case.json \
 --output demo_output.json
```

Expected runtime is less than one minute on a normal CPU. The generated JSON should match `demo/expected_output.json` except for formatting.

The demo loads a synthetic musculoskeletal case, collects simulated evidence fields and emits a structured OrthoPilot-style management recommendation. It is intended only to verify installation and repository wiring.

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

Tool Plaza templates are located in `tool_plaza/`. Replace site-specific values locally:

```
OPENAI_API_KEY
https://api.openai.com/v1
localhost
8000
checkpoints/model
data/input.jsonl
outputs/output.jsonl
```

Never commit credentials, hospital endpoints or patient-derived files.

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
