import requests
import json

# =========================
#
# =========================
JUDGE_API_URL = "http://localhost:8000"  #
JUDGE_API_KEY = None  # API, API
JUDGE_MODEL = "checkpoints/model"  # model

TIMEOUT_SEC = 30

# =========================
#
# =========================
def _headers():
    headers = {"Content-Type": "application/json"}
    if JUDGE_API_KEY:
        headers["Authorization"] = f"Bearer {JUDGE_API_KEY}"
    return headers

def test_model():
    system_message = "You are a helpful assistant."
    user_message = "What is the capital of France?"

    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 100
    }

    try:
        # POST
        response = requests.post(JUDGE_API_URL, headers=_headers(), json=payload, timeout=TIMEOUT_SEC)

        # yes or no
        response.raise_for_status()  #,

        # result
        result = response.json()

        print("Response from model:")
        print(json.dumps(result, indent=2))  # outputJSONcontent

    except requests.exceptions.RequestException as e:
        print(f"Error while calling the model API: {e}")

#
if __name__ == "__main__":
    test_model()
