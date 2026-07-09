import os
from openai import OpenAI

# Public local inference defaults.
API_BASE = os.getenv("OPENAI_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")
MODEL = os.getenv("DISTILLATION_MODEL", "checkpoints/model")

# Distillation prompt template.
SYSTEM_PROMPT = """You are an AI assistant. Generate an answer that follows the reference answer.

Wrap reasoning in <think>...</think> and the final response in <answer>...</answer>.
Keep the answer concise and faithful to the reference content."""


def get_user_content(question, answer):
    """Build the user message for distillation."""
    return f"Question:\n{question}\n\nReference answer (expected output):\n{answer}."


def main():
    client = OpenAI(
        base_url=API_BASE,
        api_key=API_KEY,
    )

    raw_question = (
        "A patient reports persistent knee pain after a twisting injury. "
        "The radiograph is negative for fracture, but the clinician suspects a meniscal injury.\n\n"
        "Which next step is most appropriate?\n\n"
        "A. Order knee MRI\nB. Start empiric antibiotics\nC. Schedule immediate hip arthroplasty\nD. Discharge without follow-up\nE. Repeat chest radiography"
    )
    ground_truth = "A"

    user_content = get_user_content(raw_question, ground_truth)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=8192,
    )

    print("--- response ---")
    print(resp.choices[0].message.content)


if __name__ == "__main__":
    main()
