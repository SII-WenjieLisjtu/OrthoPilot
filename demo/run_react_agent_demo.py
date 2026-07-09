import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest


TOOLS = {
    "case_summary": "Summarize the synthetic case context.",
    "evidence_lookup": "Return synthetic evidence relevant to the requested topic.",
    "safety_check": "Return safety checks for the synthetic recommendation.",
}


SYSTEM_PROMPT = """You are running the public OrthoPilot ReAct demo on a synthetic musculoskeletal case.
Use only the listed tools and the synthetic case content. Do not claim access to private data,
hospital systems, model weights or retrieval indexes. Return one JSON object with these keys:
reasoning_summary, action, action_input, final_answer. Use action=null only when the answer is final.
"""


def run_tool(name: str, tool_input: str, case: Dict[str, Any]) -> str:
    context = case.get("patient_context", {})
    if name == "case_summary":
        parts = [
            f"Age: {context.get('age', 'unknown')}",
            f"Presentation: {context.get('presentation', 'not provided')}",
            f"Imaging: {context.get('imaging', 'not provided')}",
        ]
        comorbidities = context.get("comorbidities", [])
        if comorbidities:
            parts.append("Comorbidities: " + ", ".join(comorbidities))
        return "\n".join(parts)
    if name == "evidence_lookup":
        topic = tool_input.strip() or "management"
        return (
            f"Synthetic evidence for {topic}: displaced femoral neck fracture in an older adult "
            "usually requires prompt perioperative assessment, fracture-stability review, "
            "shared surgical planning and early mobilization planning."
        )
    if name == "safety_check":
        return (
            "Safety checks: verify identity and laterality, review anticoagulant exposure, "
            "assess perioperative medical risk, and document that this synthetic demo is not clinical advice."
        )
    return f"Unknown tool: {name}"


def extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def openai_chat(messages: List[Dict[str, str]], model: str, base_url: str, api_key: str, timeout: int) -> str:
    payload = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode("utf-8")
    req = urlrequest.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def deterministic_step(case: Dict[str, Any], step: int, observation: Optional[str]) -> Dict[str, Any]:
    if step == 0:
        return {
            "reasoning_summary": "The agent first needs the synthetic case context.",
            "action": "case_summary",
            "action_input": "full case",
            "final_answer": None,
        }
    if step == 1:
        return {
            "reasoning_summary": "The agent has the case context and now checks management evidence.",
            "action": "evidence_lookup",
            "action_input": "femoral neck fracture surgical planning",
            "final_answer": None,
        }
    if step == 2:
        return {
            "reasoning_summary": "The agent checks safety constraints before finalizing.",
            "action": "safety_check",
            "action_input": "perioperative fracture care",
            "final_answer": None,
        }
    return {
        "reasoning_summary": "The agent combines the synthetic case, retrieved evidence and safety checks.",
        "action": None,
        "action_input": None,
        "final_answer": (
            "Synthetic recommendation: confirm the displaced left femoral neck fracture, complete perioperative "
            "risk assessment, review anticoagulant exposure, discuss arthroplasty-based management when appropriate, "
            "and plan early postoperative mobilization. This is a demo output only and not clinical advice."
        ),
    }


def build_user_prompt(case: Dict[str, Any], trajectory: List[Dict[str, str]]) -> str:
    return json.dumps(
        {
            "case": case,
            "available_tools": TOOLS,
            "trajectory_so_far": trajectory,
            "instruction": "Choose the next ReAct action or provide the final answer.",
        },
        indent=2,
    )


def run_agent(case: Dict[str, Any], backend: str, model: str, base_url: str, api_key: str, timeout: int, max_steps: int) -> Dict[str, Any]:
    trajectory: List[Dict[str, str]] = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    last_observation: Optional[str] = None

    for step in range(max_steps):
        if backend == "openai":
            messages.append({"role": "user", "content": build_user_prompt(case, trajectory)})
            content = openai_chat(messages, model, base_url, api_key, timeout)
            decision = extract_json(content)
            messages.append({"role": "assistant", "content": content})
        else:
            decision = deterministic_step(case, step, last_observation)

        action = decision.get("action")
        if not action:
            return {
                "case_id": case["case_id"],
                "mode": f"react_{backend}",
                "model": model if backend == "openai" else "deterministic-scripted",
                "trajectory": trajectory,
                "final_answer": decision.get("final_answer", "No final answer returned."),
            }

        if action not in TOOLS:
            observation = f"Unsupported action in public demo: {action}"
        else:
            observation = run_tool(action, str(decision.get("action_input") or ""), case)
        trajectory.append(
            {
                "reasoning_summary": str(decision.get("reasoning_summary") or ""),
                "action": str(action),
                "action_input": str(decision.get("action_input") or ""),
                "observation": observation,
            }
        )
        last_observation = observation

    return {
        "case_id": case["case_id"],
        "mode": f"react_{backend}",
        "model": model if backend == "openai" else "deterministic-scripted",
        "trajectory": trajectory,
        "final_answer": "The agent reached the step limit before producing a final answer.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the public OrthoPilot ReAct-style synthetic demo.")
    parser.add_argument("--input", default="demo/react_case.json", help="Path to a synthetic ReAct demo case JSON file.")
    parser.add_argument("--output", required=True, help="Path for the generated output JSON file.")
    parser.add_argument("--backend", choices=["deterministic", "openai"], default="deterministic")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("OPENAI_TIMEOUT", "60")))
    parser.add_argument("--max-steps", type=int, default=4)
    args = parser.parse_args()

    if args.backend == "openai" and not args.api_key:
        raise SystemExit("OPENAI_API_KEY is required for --backend openai. Use a placeholder such as EMPTY for local vLLM if your server accepts it.")

    case = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run_agent(case, args.backend, args.model, args.base_url, args.api_key, args.timeout, args.max_steps)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote ReAct demo output to {output_path}")


if __name__ == "__main__":
    main()
