import json
import re
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# filepath
json_file = "data/input.json"

# result
y_true = []
y_pred = []

def extract_answer(text):
    """</think>content, judgement: yes or no"""
    if not isinstance(text, str):
        return 1  # default
    # </think>content
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    return 0 if 'no, ' in text else 1

# loadJSON
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

#
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
        continue  # skipcontent

    y_true.append(extract_answer(gpt_resp))
    y_pred.append(extract_answer(model_resp))

#
acc = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)

# outputresult
print(f"Statistics result ({len(y_true)} samples):")
print(f"OK Accuracy: {acc:.4f}")
print(f" Precision: {precision:.4f}")
print(f" Recall: {recall:.4f}")
print(f" F1-score: {f1:.4f}")


# statisticsresult(100 sample):
# OK Accuracy: 0.5700
#  Precision: 0.5556
#  Recall: 0.4255
#  F1-score: 0.4819