import requests
import json

# =========================
# 配置部分
# =========================
JUDGE_API_URL = "http://YOUR_HOST:YOUR_PORT"  # 替换成你的服务地址
JUDGE_API_KEY = None  # 如果需要API密钥，设置你的API密钥
JUDGE_MODEL = "/path/to/model"  # 替换成你实际部署的模型名称

TIMEOUT_SEC = 30

# =========================
# 测试请求
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
        # 发送POST请求
        response = requests.post(JUDGE_API_URL, headers=_headers(), json=payload, timeout=TIMEOUT_SEC)
        
        # 检查是否成功
        response.raise_for_status()  # 如果请求失败，会抛出异常
        
        # 获取返回的结果
        result = response.json()
        
        print("Response from model:")
        print(json.dumps(result, indent=2))  # 格式化输出返回的JSON内容

    except requests.exceptions.RequestException as e:
        print(f"Error while calling the model API: {e}")

# 运行测试
if __name__ == "__main__":
    test_model()
