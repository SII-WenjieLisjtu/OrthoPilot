import requests
import json
# Execute a tool
response = requests.post(
    "http://localhost:8000",
    json={
        "tool_name": "cpubmed.search",
        "parameters": {
            "entity": "",
            "relation": "clinical_manifestation",
            "limit": 5
        }
    }
)

result = response.json()
print(result)
# zifu = json.loads(result['data'])['summary']

# # breakpoint()
# print(zifu)