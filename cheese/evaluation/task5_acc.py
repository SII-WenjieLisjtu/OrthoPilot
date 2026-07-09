import json
import re
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 文件路径
json_file = "/path/to/input.json"

# 结果存储
y_true = []
y_pred = []

def extract_answer(text):
    """提取</think>后内容，并判断是否为否定类"""
    if not isinstance(text, str):
        return 1  # 默认肯定类
    # 提取</think>后的内容
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    return 0 if '否，' in text else 1

# 加载JSON数据
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 遍历每条对话
for item in data:
    conversations = item.get("conversations", [])
    gpt_resp = None
    model_resp = None

    for conv in conversations:
        if conv["from"] == "gpt":
            gpt_resp = conv["value"]
        elif conv["from"] == "bone_expert":
            model_resp = conv["value"]

    if gpt_resp is None or model_resp is None:
        continue  # 跳过缺失内容的项

    y_true.append(extract_answer(gpt_resp))
    y_pred.append(extract_answer(model_resp))

# 计算指标
acc = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)

# 输出结果
print(f"📊 统计结果（共 {len(y_true)} 条样本）:")
print(f"✅ Accuracy:  {acc:.4f}")
print(f"🎯 Precision: {precision:.4f}")
print(f"📈 Recall:    {recall:.4f}")
print(f"🏅 F1-score:  {f1:.4f}")


# 📊 统计结果（共 100 条样本）:
# ✅ Accuracy:  0.5700
# 🎯 Precision: 0.5556
# 📈 Recall:    0.4255
# 🏅 F1-score:  0.4819