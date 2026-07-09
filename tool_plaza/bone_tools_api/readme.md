# Tool Plaza API Server

This directory contains a FastAPI server that exposes retained public Tool Plaza interfaces for knowledge graph, medical book, Semantic Scholar, and utility tools. For the full service manifest and one-click service skeleton, see `../README.md`.

## Quick start

From the repository root:

```bash
python -m venv .venv-tool-api
source .venv-tool-api/bin/activate
pip install -r tool_plaza/bone_tools_api/requirements.txt
bash tool_plaza/bone_tools_api/start_server.sh
```

The default local endpoint is `http://localhost:8766`. Override it with `HOST`, `PORT`, and `WORKERS` environment variables.

## Configuration

Provide service credentials through environment variables or a local `.env` file that is not committed to the repository.

Common variables:

- `OPENAI_API_KEY`: optional key for LLM-backed MedicalBook mode.
- `OPENAI_API_BASE`: optional OpenAI-compatible base URL.
- `SEMANTIC_SCHOLAR_API_KEY`: optional key for Semantic Scholar search.
- `HOST`: server bind host used by `start_server.sh`.
- `PORT`: server port used by `start_server.sh`.
- `WORKERS`: uvicorn worker count used by `start_server.sh`.

If an optional external API key is not configured, the corresponding tool may be unavailable while the rest of the server can still run. If the excluded CPubMed or MedicalBook data files are not present, the server skips those tools and keeps the remaining retained tools available. If you supply local MedicalBook data and enable embedding retrieval, install `FlagEmbedding` in that local environment.

## API documentation

After starting the server, open:

- Swagger UI: `http://localhost:8766/docs`
- ReDoc: `http://localhost:8766/redoc`

## Example request

```bash
curl -X POST http://localhost:8766/tools/execute \
 -H "Content-Type: application/json" \
 -d '{"tool_name":"echo","parameters":{"message":"public smoke test","repeat":1}}'
```

## Tool categories

- Base utilities
- CPubMed knowledge graph tools, when local CPubMed data files are supplied
- MedicalBook retrieval, when local MedicalBook data files are supplied
- Semantic Scholar search

For endpoint details, see `API_GUIDE.md`. For CPubMed tool names, see `tools/cpubmed/TOOLS.md`.
