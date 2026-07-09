# Tool Plaza API Guide

## Start the server

```bash
pip install -r requirements.txt
bash start_server.sh
```

By default, the public example server listens on `http://localhost:8766`.

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
 -d '{"tool_name":"cpubmed.search","parameters":{"entity":"diabetes","relation":"drug treatment","limit":5}}'
```

Python example:

```python
import requests

base_url = "http://localhost:8766"
resp = requests.post(
 f"{base_url}/tools/execute",
 json={
 "tool_name": "cpubmed.search",
 "parameters": {"entity": "diabetes", "relation": "drug treatment", "limit": 5},
 },
 timeout=30,
)
print(resp.json())
```

## Configuration

Use environment variables or a local `.env` file for API keys and service settings. Do not commit private keys or deployment-specific URLs.

## Notes

- Some tools require optional external API keys.
- Long-running retrieval tools may need longer client timeouts.
- Check `logs/` for server and tool execution logs when debugging local runs.
