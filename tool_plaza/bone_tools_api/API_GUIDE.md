# Tool Plaza API Guide

## Start the server

From the repository root, use an isolated environment for the public API server:

```bash
python -m venv .venv-tool-api
source .venv-tool-api/bin/activate
pip install -r tool_plaza/bone_tools_api/requirements.txt
bash tool_plaza/bone_tools_api/start_server.sh
```

By default, the public example server listens on `http://localhost:8766`. Override the bind address, port and worker count with `HOST`, `PORT` and `WORKERS`.

## Documentation endpoints

- Swagger UI: `http://localhost:8766/docs`
- ReDoc: `http://localhost:8766/redoc`

## Core endpoints

### `GET /`

Returns basic service metadata.

### `GET /health`

Returns server health status.

### `GET /tools`

Lists registered tools and their schemas.

### `POST /tools/execute`

Executes a registered tool.

Example:

```bash
curl -X POST http://localhost:8766/tools/execute \
 -H "Content-Type: application/json" \
 -d '{"tool_name":"echo","parameters":{"message":"public smoke test","repeat":1}}'
```

Python example:

```python
import requests

base_url = "http://localhost:8766"
resp = requests.post(
 f"{base_url}/tools/execute",
 json={
 "tool_name": "echo",
 "parameters": {"message": "public smoke test", "repeat": 1},
 },
 timeout=30,
)
print(resp.json())
```

## Configuration

Use environment variables or a local `.env` file for API keys and service settings. Do not commit private keys or deployment-specific URLs.

## Notes

- Some tools require optional external API keys.
- CPubMed and MedicalBook tools are registered only when their local data files are supplied.
- MedicalBook embedding mode requires `FlagEmbedding` in local environments that supply MedicalBook data.
- Long-running retrieval tools may need longer client timeouts.
- Check `logs/` for server and tool execution logs when debugging local runs.
