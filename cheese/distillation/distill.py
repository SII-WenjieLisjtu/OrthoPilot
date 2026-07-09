import os
from openai import OpenAI

# 配置常量
API_BASE = "http://YOUR_HOST:YOUR_PORT"
API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")
MODEL = "/path/to/model"

# 1. 泛化后的系统提示词
SYSTEM_PROMPT = """你是一个具备深厚骨科医学素养的AI助手。请根据提供的医学问题，严格按照以下格式直接输出内容，严禁包含任何前言、引导语、后缀或其他叙述：

<think>
以医学专家视角，独立分析病历中的外伤机制、关键症状及体征，将临床线索与解剖定位及诊疗规范整合为一段自然连贯的叙述性段落。在推理过程中不能给出提及用户需求以及正确答案，直接进行思考；需通过逻辑分析自然推导出最可能的临床诊断。
</think>
<answer>
直接输出与所提供的正确答案内容完全一致的文本。
</answer>

除此之外，不要生成任何其他内容。"""

# 2. 格式化的用户输入模板
def get_user_content(question, answer):
    return f"医学问题：\n{question}\n\n参考答案（仅用于输出控制）：\n{answer}. 输出的思考过程请不要包括用户需求等表达。"

def main():
    client = OpenAI(
        base_url=API_BASE,
        api_key=API_KEY,
    )

    # 定义原始问题和标准答案（此处以 A 为例）
    raw_question = (
        "患者因外伤后左上肢疼痛3天就诊。3天前因暴力撞击导致左上肢疼痛，伴有肿胀，无发热，无肢体麻木。"
        "患者曾至其他医院就诊，行X线检查提示左侧上肢存在骨折。接诊医生建议手术治疗，患者随后来我院急诊就诊，急诊拟以收治入院。\n\n"
        "根据下方入院记录内容，选择最有可能的入院诊断。请只写选项字母：\n\n"
        "A. 肱骨干骨折\nB. 肱骨头骨折\nC. 尺骨骨折\nD. 桡骨远端骨折\nE. 肩胛骨骨折"
    )
    ground_truth = "A"

    # 使用新函数组装内容
    user_content = get_user_content(raw_question, ground_truth)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2, # 保持低随机性以确保推理严谨
        max_tokens=8192,
    )

    print("--- 蒸馏出的思考过程 ---")
    print(resp.choices[0].message.content)

if __name__ == "__main__":
    main()