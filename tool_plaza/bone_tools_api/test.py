import requests
import json
# Execute a tool
response = requests.post(
    "http://YOUR_HOST:YOUR_PORT",
    json={
        "tool_name": "cpubmed.search",
        "parameters": {
            "entity": "髋关节退行性变",
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