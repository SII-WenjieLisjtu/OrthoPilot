# Tool Plaza API Server

This directory contains a FastAPI server that exposes public Tool Plaza interfaces for knowledge graph, medical book, Semantic Scholar, and utility tools.

## Quick start

```bash
pip install -r requirements.txt
bash start_server.sh
```

The default local endpoint is `http://localhost:8766`. Override it with `HOST`, `PORT`, and `WORKERS` environment variables.

## Configuration

Provide service credentials through environment variables or a local `.env` file that is not committed to the repository.

Common variables:

- `OPENAI_API_KEY`: optional key for LLM-backed MedicalBook mode.
- `OPENAI_API_BASE`: optional OpenAI-compatible base URL.
- `SEMANTIC_SCHOLAR_API_KEY`: optional key for Semantic Scholar search.
- `SERVER_PORT`: optional server port when not using `start_server.sh`.
- `SERVER_WORKERS`: optional worker count.

If an optional external API key is not configured, the corresponding tool may be unavailable while the rest of the server can still run.

## API documentation

After starting the server, open:

- Swagger UI: `http://localhost:8766/docs`
- ReDoc: `http://localhost:8766/redoc`

## Example request

```bash
curl -X POST http://localhost:8766/tools/execute \
 -H "Content-Type: application/json" \
 -d '{"tool_name":"cpubmed.search","parameters":{"entity":"diabetes","relation":"drug treatment","limit":5}}'
```

## Tool categories

- Base utilities
- CPubMed knowledge graph tools
- MedicalBook retrieval
- Semantic Scholar search

For endpoint details, see `API_GUIDE.md`. For CPubMed tool names, see `tools/cpubmed/TOOLS.md`.
