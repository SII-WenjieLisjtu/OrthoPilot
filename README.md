# OrthoPilot

**Evidence-grounded AI for longitudinal clinical management in musculoskeletal care**

This repository contains source code, prompts, configuration templates and analysis scripts accompanying the manuscript **"Evidence-grounded AI for longitudinal clinical management in musculoskeletal care"**.

OrthoPilot is a clinical agent system for full-pathway musculoskeletal care. It combines the CHEESE reasoning backbone, Tool Plaza evidence interfaces, OrthoBench benchmark utilities and ORACLE open-response evaluation scripts.

This public release is intended for code review, method inspection and lightweight demonstration. It does not include patient-level records, model weights, retrieval indexes or private hospital deployment assets.

## Repository contents

```text
orthopilot/
├── README.md                         # This file
├── LICENSE                           # Apache License 2.0
├── CITATION.cff                      # Citation metadata
├── requirements.txt                  # Minimal Python dependencies
├── demo/                             # Deterministic synthetic demo
├── docs/                             # Code availability and reproduction notes
│   ├── code_availability.md
│   ├── reproduction_map.md
│   └── methods/
├── orthopilot_agent/                 # Agent runtime, configs and trajectory code
│   ├── miroflow_core/
│   ├── configs/
│   ├── skills/
│   └── fathom_trajectory/
├── tool_plaza/                       # Tool Plaza interfaces and MCP-style servers
│   ├── mcp_servers/
│   ├── tool_configs/
│   └── bone_tools_api/
├── cheese/                           # CHEESE training, inference and evaluation scripts
├── oracle/                           # ORACLE open-response evaluation framework
├── orthobench/                       # OrthoBench construction and visualization scripts
├── analyses/                         # Manuscript analysis scripts
└── prompts/                          # Agent, tool-use and evaluation prompts
```

## System requirements

### Tested environment

The lightweight demo and repository checks were tested on:

- Operating system: Linux 5.15
- Python: 3.12.4
- Conda: optional; any clean conda or virtualenv environment with Python 3.12 is suitable
- Hardware for demo: standard CPU environment. No GPU is required for the deterministic demo.

### Optional hardware

Full CHEESE training, model inference, vLLM serving and large-scale evaluation require GPU infrastructure and model checkpoints that are not included in this public release. The exact hardware requirements depend on the selected model endpoint and batch size.

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

Typical installation time on a normal desktop or workstation is 5 to 15 minutes, depending on network speed and whether PyTorch wheels are already cached.

Some scripts require optional dependencies such as PyTorch, Transformers, vLLM, FastAPI, FAISS, LLaMA-Factory or VERL. These are not vendored in this repository.

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
  --input_file /path/to/input.jsonl \
  --output_file /path/to/output.jsonl \
  --model_name /path/to/model-or-endpoint
```

Update model paths or endpoint settings before use. API keys should be provided through environment variables and should not be committed.

### Inspect ORACLE evaluation code

```bash
cd oracle/scripts
python task_all_gen_async.py --help
```

ORACLE scoring of open-ended clinical management responses requires rubric files, model access and response files prepared according to the manuscript methods.

### Configure Tool Plaza servers

Tool Plaza server templates are located in `tool_plaza/tool_configs/`. They point to canonical MCP-style server modules in `tool_plaza/mcp_servers/`.

Site-specific values should be replaced locally:

```text
YOUR_API_KEY
YOUR_API_BASE_URL
YOUR_HOST
YOUR_PORT
/path/to/model
/path/to/input.jsonl
/path/to/output.jsonl
```

### Run OrthoBench and analysis scripts

OrthoBench utilities are in `orthobench/`. Manuscript analysis scripts are in `analyses/`. These scripts require source data tables that are controlled-access and are not included in this public repository.

## Reproducing manuscript results

A code-to-manuscript map is provided in `docs/reproduction_map.md`.

Exact reproduction of quantitative manuscript results requires controlled clinical datasets, model checkpoints, retrieval indexes and deployment infrastructure described in the paper. These assets are excluded from this release because they contain patient-derived data or institution-specific resources.

## Data availability and privacy

This repository intentionally excludes:

- patient-level clinical records;
- raw or generated evaluation data derived from clinical records;
- model weights, checkpoints and LoRA adapters;
- retrieval indexes, vector databases and local cache files;
- hospital-specific deployment secrets, API keys and private endpoints;
- large third-party dependency repositories.

The included demo data are synthetic and do not correspond to any real patient.

## Code availability

See `docs/code_availability.md` for a summary of included and excluded assets.

## License

This software is released under the Apache License 2.0. See `LICENSE`.

## Citation

Citation metadata are provided in `CITATION.cff`. Please cite the associated manuscript if you use this code.

## Clinical-use disclaimer

This repository is provided for research review and reproducibility support. It is not a medical device and must not be used for clinical decision-making without appropriate validation, regulatory review and institutional approval.
