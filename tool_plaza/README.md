# Tool Plaza configuration

This directory contains public Tool Plaza interface templates for OrthoPilot. It provides adapter code, example tool configuration files, a public service manifest, and a local service-control skeleton. It does not include patient data, private hospital services, model weights, retrieval indexes, credentials, or large database files.

## Installation profiles

Use separate environments when inspecting different layers. This avoids installing private or heavyweight dependencies for the synthetic demo.

### 1. MCP adapter environment

Use this environment when you want to inspect or launch the MCP-style adapters in `tool_plaza/mcp_servers/`.

```bash
python -m venv .venv-tool-plaza
source .venv-tool-plaza/bin/activate
pip install -r tool_plaza/requirements.txt
```

This installs common adapter dependencies such as `fastmcp`, `aiohttp`, `httpx`, `requests`, `openai`, `anthropic`, `pydantic`, and `PyYAML`. Some adapters also require provider-specific credentials, optional Python packages or external runtimes.

### 2. Public Tool Plaza API server environment

Use this environment when you want to run the retained public FastAPI tool server in `tool_plaza/bone_tools_api/`.

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

Useful endpoints:

```text
http://localhost:8766/health
http://localhost:8766/tools
http://localhost:8766/docs
```

The public API server can start without the excluded CPubMed and MedicalBook data files. When those files are absent, the corresponding tools are skipped and the remaining retained tools stay available. If you supply local MedicalBook data and enable embedding retrieval, install `FlagEmbedding` in that local environment.

### 3. Optional local service environment

Use this only if you have your own local services, governed data, or model weights. The public repository does not provide these assets.

Examples of optional local services:

- EHR adapter backend
- hospital similar-case backend
- MedRAG retrieval endpoint
- MedRAG translation sidecar
- PMC-Patients retrieval endpoint
- Fathom web-search sandbox
- local OpenAI-compatible vLLM model endpoint

Start commands for these services must be provided through local environment variables. Do not commit those commands if they include private paths, model locations, endpoints, or credentials.

## One-click service skeleton

The public service-control script is:

```bash
bash tool_plaza/start_all_services.sh status
bash tool_plaza/start_all_services.sh start
bash tool_plaza/start_all_services.sh stop
```

The script reads the service table embedded in `tool_plaza/start_all_services.sh` and mirrors `tool_plaza/service_manifest.json`. It starts only the retained public knowledge-tool API by default. Use the public API server environment, or install `tool_plaza/bone_tools_api/requirements.txt` in the active environment, before running `start`. Other services are reported in `status` and are started only when you provide a local start command through an environment variable.

## Service manifest

`tool_plaza/service_manifest.json` defines the public service names, default local URLs, health paths, environment variables, and matching tool config files.

| Service | Default URL | Health path | Runtime URL variable | Start command variable | Public config |
| --- | --- | --- | --- | --- | --- |
| `ehr` | `http://localhost:9000` | `/health` | `EHR_BASE_URL` | `EHR_START_COMMAND` | `tool_configs/tool-ehr.yaml` |
| `similar-case` | `http://localhost:9999` | `/health` | `HOSPITAL_SIMILAR_URL` | `SIMILAR_CASE_START_COMMAND` | `tool_configs/tool-similar-case.yaml` |
| `knowledge-graph` | `http://localhost:8766` | `/health` | `KG_BASE_URL` | `KG_START_COMMAND` | `tool_configs/tool-knowledge-graph.yaml` |
| `medrag-translate` | `http://localhost:8888` | `/health` | `MEDRAG_TRANSLATE_BASE_URL` | `MEDRAG_TRANSLATE_START_COMMAND` | none |
| `medrag` | `http://localhost:8000` | `/health` | `MEDRAG_BASE_URL` | `MEDRAG_START_COMMAND` | `tool_configs/tool-medrag.yaml` |
| `pmc-patients` | `http://localhost:9001` | `/health` | `PMC_PATIENTS_URL` | `PMC_PATIENTS_START_COMMAND` | none |
| `fathom-search` | `http://localhost:8904` | `/docs` | `FATHOM_SANDBOX_URL` | `FATHOM_SEARCH_START_COMMAND` | `tool_configs/tool-web-search.yaml` |
| `qwen3-vllm` | `http://localhost:8080/v1` | `/models` | `OPENAI_BASE_URL` | `VLLM_START_COMMAND` | none |

## Environment variables by adapter

### EHR

```bash
export EHR_BASE_URL="http://localhost:9000"
export EHR_START_COMMAND="your-local-ehr-command"
```

The public repository includes the MCP adapter template only. It does not include a hospital EHR backend.

### Similar-case retrieval

```bash
export HOSPITAL_SIMILAR_URL="http://localhost:9999"
export PMC_PATIENTS_URL="http://localhost:9001"
export SIMILAR_CASE_START_COMMAND="your-local-similar-case-command"
export PMC_PATIENTS_START_COMMAND="your-local-pmc-patients-command"
```

The public repository includes adapter templates only. It does not include patient-derived case indexes or literature retrieval indexes.

### Knowledge graph and public Tool Plaza API

```bash
export KG_BASE_URL="http://localhost:8766"
export KG_START_COMMAND="cd tool_plaza/bone_tools_api && exec python -m uvicorn tool_server:app --host 127.0.0.1 --port 8766"
```

If `KG_START_COMMAND` is not set, `tool_plaza/start_all_services.sh start` uses the retained public Tool Plaza API command. CPubMed tools are registered only when local CPubMed data files are supplied. Optional external keys can be supplied locally. This API server path reads `OPENAI_API_BASE`, while MCP reasoning configs read `OPENAI_BASE_URL`:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-semantic-scholar-key"
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"
```

### MedRAG

```bash
export MEDRAG_BASE_URL="http://localhost:8000"
export MEDRAG_TRANSLATE_BASE_URL="http://localhost:8888"
export MEDRAG_START_COMMAND="your-local-medrag-command"
export MEDRAG_TRANSLATE_START_COMMAND="your-local-translation-command"
```

The public repository does not include retrieval corpora, indexes, model weights, or private translation services.

### Web search sandbox

```bash
export FATHOM_SANDBOX_URL="http://localhost:8904"
export FATHOM_SEARCH_START_COMMAND="your-local-search-sandbox-command"
```

The public repository includes the adapter shape only. It does not include private search infrastructure.

### OpenAI-compatible reasoning or local vLLM

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL_NAME="gpt-4o"
```

For a local vLLM endpoint:

```bash
export OPENAI_API_KEY="EMPTY"
export OPENAI_BASE_URL="http://localhost:8080/v1"
export OPENAI_MODEL_NAME="local-model-name"
export VLLM_START_COMMAND="your-local-vllm-command"
```

The public repository does not include model weights. Keep local model paths outside version control. Tool Plaza MCP reasoning configs read `OPENAI_MODEL_NAME`; the standalone ReAct demo reads `OPENAI_MODEL`.

### Image and video tools

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export GEMINI_API_KEY="your-gemini-key"
```

Only set keys for providers that you are allowed to use. Do not commit `.env` files or real keys.

### Serper search

```bash
export SERPER_API_KEY="your-serper-key"
```

This key is optional and is only needed for the Serper MCP configuration. Serper-backed tools use `npx` at runtime, so Node.js and npm must be installed locally when those adapters are enabled.

### Reading and provider-specific adapters

The reading adapter expects the `markitdown-mcp` command to be installed in the active environment. Gemini image or video paths require the `google-genai` Python package in addition to the configured `GEMINI_API_KEY`. Install these only when those optional adapters are enabled.

## Local `.env` files

A local `.env` file can be convenient during development, but it must remain outside version control. Recommended pattern:

```text
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o
KG_BASE_URL=http://localhost:8766
```

Do not put patient identifiers, hospital URLs, private network addresses, model checkpoint paths, database paths, or real credentials in committed files.

## Verification commands

After installation, run these commands from the repository root:

```bash
python demo/run_demo.py --input demo/synthetic_case.json --output /tmp/orthopilot_demo_output.json
python demo/run_react_agent_demo.py --input demo/react_case.json --output /tmp/orthopilot_react_demo_output.json
bash tool_plaza/start_all_services.sh status
bash -n tool_plaza/start_all_services.sh tool_plaza/bone_tools_api/start_server.sh
python -m json.tool tool_plaza/service_manifest.json >/dev/null
```

Optional public API smoke test. Run this from the public API server environment, or any environment where `tool_plaza/bone_tools_api/requirements.txt` has been installed:

```bash
bash tool_plaza/start_all_services.sh start
python - <<'PY'
from urllib import request
with request.urlopen('http://localhost:8766/health', timeout=5) as response:
    print(response.status)
PY
bash tool_plaza/start_all_services.sh stop
```

## Release boundary

This directory is for source inspection, adapter configuration, and synthetic local smoke tests. It is not a full deployment bundle. It intentionally excludes:

- patient-derived clinical data;
- hospital service implementations;
- private endpoints and credentials;
- model weights and local checkpoint paths;
- retrieval indexes and vector databases;
- manuscript-result analysis, plotting, table export, figure generation, reader-study selection, calibration, or benchmark data construction code.
