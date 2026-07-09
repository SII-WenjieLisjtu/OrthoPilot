#!/usr/bin/env python3
"""
trajectory_enhancer.py - Enhance generated medical-search trajectories.

This public template loads an existing trajectory, asks a local model endpoint to generate
additional search-supported reasoning, and writes an OrthoPilot-compatible trajectory file.

Example:
    python3 trajectory_enhancer.py \
        --input data/examples/T1/example_traj/patient_test_original.json \
        --output outputs/patient_test_enhanced.json \
        --model-url http://localhost:8000 \
        --executors http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "inference"))

from re_call_medical import ReCallMedical  # type: ignore
from medical_trajectory_generator import MEDICAL_SCHEMAS  # type: ignore

try:
    from transformers import AutoTokenizer  # type: ignore
except Exception:  # pragma: no cover
    AutoTokenizer = None

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None


class SimpleTokenizer:
    """Fallback tokenizer used when transformers is unavailable."""

    def __call__(self, text: str, return_tensors=None, add_special_tokens=False):
        tokens = text.split()
        return {"input_ids": list(range(len(tokens)))}


def load_trajectory(path: Path) -> List[Dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Trajectory file must contain a JSON list.")
    return data


def find_final_answer_entry(trajectory: List[Dict[str, str]]) -> Dict[str, str]:
    for entry in reversed(trajectory):
        if entry.get("role") == "gpt" and "<answer>" in entry.get("content", ""):
            return entry
    raise ValueError("No final <answer> entry found in trajectory.")


def extract_diagnosis_and_basis(answer_content: str) -> Tuple[str, str]:
    diagnosis_match = re.search(r"Diagnosis[: ]\s*([^.;;\n]+)", answer_content, re.IGNORECASE)
    basis_match = re.search(r"Basis[: ]\s*([^<]+)", answer_content, re.IGNORECASE)
    diagnosis = diagnosis_match.group(1).strip() if diagnosis_match else ""
    basis = basis_match.group(1).strip().rstrip(".") if basis_match else ""
    return diagnosis, basis


def extract_patient_data(trajectory: List[Dict[str, str]]) -> Dict[str, str]:
    """Extract patient data from an ehr.basic.get_patient tool response."""
    for entry in trajectory:
        if entry.get("role") != "user":
            continue
        content = entry.get("content", "")
        if "ehr.basic.get_patient" not in content:
            continue
        try:
            match = re.search(r'"data":\s*(\{.*\})\s*}', content)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
    return {}


def python_literal(data: Dict) -> str:
    return repr(data)


def build_env(patient: Dict[str, str]) -> str:
    env = f"""
from search_api import search_urls as _search_urls, query_url as _query_url
PATIENT_DATA = {python_literal(patient)}

def get_patient():
 return PATIENT_DATA

def get_lab_results(*args, **kwargs):
 raise NotImplementedError("This task is not implemented in the public example.")

def get_imaging(*args, **kwargs):
 raise NotImplementedError("This task is not implemented in the public example.")

def search_guidelines(query, domain=None, top_k=5, _search=_search_urls):
 if domain:
  q = (domain + " " + query).strip()
 else:
  q = query
 return _search(query=q, top_k=top_k)

def search_differential_diagnosis(symptoms=None, age=None, specialty=None, top_k=5, _search=_search_urls):
 keywords = []
 if symptoms:
  keywords.extend(symptoms if isinstance(symptoms, (list, tuple)) else [symptoms])
 if age:
  keywords.append(str(age))
 if specialty:
  keywords.append(str(specialty))
 q = " ".join(filter(None, keywords)) or " "
 return _search(query=q, top_k=top_k)

def search_web(query, top_k=10, _search=_search_urls):
 return _search(query=query, top_k=top_k)

def visit_url(url, goal, _visit=_query_url):
 return _visit(url=url, goal=goal)
"""
    return env.strip()


def load_tokenizer(name: Optional[str]):
    if not name:
        return SimpleTokenizer()
    if AutoTokenizer is None:
        print("[warn] transformers is unavailable; using fallback token counting.")
        return SimpleTokenizer()
    print(f"[tokenizer] load {name}")
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True)


def ensure_search_steps(trajectory: List[Dict[str, str]]):
    for entry in trajectory:
        if entry.get("role") == "gpt" and "<tool_call>" in entry.get("content", ""):
            if "search" in entry["content"].lower():
                return
    raise RuntimeError("The model did not generate a search tool call.")


def collect_tool_evidence(trajectory: List[Dict[str, str]]) -> List[str]:
    pattern = re.compile(r"<tool_response>(.*?)</tool_response>", re.DOTALL)
    evidences: List[str] = []
    for entry in trajectory:
        if entry.get("role") != "user":
            continue
        content = entry.get("content", "")
        for match in pattern.findall(content):
            evidences.append(match.strip())
    return evidences


def extract_generated_final_step(trajectory: List[Dict[str, str]]) -> Dict[str, str]:
    for step in reversed(trajectory):
        if step.get("role") == "gpt" and "<answer>" in step.get("content", ""):
            return step
    raise ValueError("No generated final answer was found.")


def rewrite_final_step_content(original_content: str, new_answer: str) -> str:
    think_match = re.search(r"<think>(.*?)</think>", original_content, re.DOTALL)
    think_text = think_match.group(1).strip() if think_match else "Reasoning omitted."
    return f"<think>{think_text}</think><answer>{new_answer}</answer>"


def summarize_answer(
    diagnosis: str,
    original_basis: str,
    evidences: List[str],
    args: argparse.Namespace,
) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None or args.skip_summary:
        return None

    client = OpenAI(api_key=api_key)
    evidence_text = "\n\n".join(evidences) if evidences else "No tool evidence was collected."

    system_prompt = (
        "You are a clinician. Produce a concise final answer that includes: "
        "(1) the diagnosis; (2) the supporting basis; (3) evidence from searches; "
        "and (4) any uncertainty that remains."
    )

    user_prompt = (
        f"Diagnosis: {diagnosis or ''}\n"
        f"Original basis: {original_basis or ''}\n"
        f"Evidence:\n{evidence_text}\n"
        "Write the final answer."
    )

    try:
        response = client.chat.completions.create(
            model=args.summary_model,
            temperature=args.summary_temperature,
            max_tokens=args.summary_max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as exc:
        print(f"[warn] OpenAI summarization failed: {exc}")
        return None


def merge_trajectory(
    original: List[Dict[str, str]],
    generated: List[Dict[str, str]],
    question_index: int,
    final_step_override: Optional[str] = None,
) -> List[Dict[str, str]]:
    prefix = original[: question_index + 1]

    suffix_steps: List[Dict[str, str]] = []
    final_step: Optional[Dict[str, str]] = None
    for step in generated[2:]:
        if step.get("role") == "gpt" and "<answer>" in step.get("content", ""):
            final_step = step
            break
        suffix_steps.append(step)

    if final_step is None:
        raise RuntimeError("The model output did not include a final answer.")

    suffix_steps.append({
        "role": "gpt",
        "content": final_step_override if final_step_override is not None else final_step["content"],
    })
    return prefix + suffix_steps


def run_agent(
    question: str,
    env: str,
    schemas: List[Dict[str, object]],
    args: argparse.Namespace,
    tokenizer,
):
    agent = ReCallMedical(executor_url=args.executors, max_searches=args.max_searches)
    transcript, tool_calls, trajectory = agent.run(
        env=env,
        func_schemas=json.dumps(schemas, ensure_ascii=False, indent=2),
        question=question,
        model_url=args.model_url,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        tokenizer=tokenizer,
    )
    return transcript, tool_calls, trajectory


def main():
    parser = argparse.ArgumentParser(description="DeepResearch trajectory enhancer")
    parser.add_argument("--input", required=True, help="Input trajectory JSON path")
    parser.add_argument("--output", help="Output path. Defaults to overwriting the input file")
    parser.add_argument("--model-url", required=True, help="Fathom-Search model endpoint URL")
    parser.add_argument("--executors", required=True, help="Executor service URL")
    parser.add_argument("--tokenizer", default=None, help="Optional Hugging Face tokenizer name or path")
    parser.add_argument("--temperature", type=float, default=0.2, help="Generation temperature")
    parser.add_argument("--max-new-tokens", type=int, default=2048, help="Maximum generated tokens")
    parser.add_argument("--max-searches", type=int, default=5, help="Maximum search tool calls")
    parser.add_argument("--summary-model", default="gpt-4o", help="OpenAI model used for optional summarization")
    parser.add_argument("--summary-temperature", type=float, default=0.2, help="Summarization temperature")
    parser.add_argument("--summary-max-tokens", type=int, default=512, help="Maximum summarization tokens")
    parser.add_argument("--skip-summary", action="store_true", help="Skip OpenAI summarization and keep the model answer")
    parser.add_argument("--force", action="store_true", help="Overwrite the output file if it already exists")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated environment and exit")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = Path(args.output) if args.output else input_path
    if output_path.exists() and output_path != input_path and not args.force:
        raise FileExistsError(f"Output file already exists: {output_path}; pass --force to overwrite it")

    trajectory = load_trajectory(input_path)
    final_entry = find_final_answer_entry(trajectory)
    final_index = trajectory.index(final_entry)
    question_index: Optional[int] = None
    for idx in range(final_index - 1, -1, -1):
        if trajectory[idx].get("role") == "user":
            question_index = idx
            break
    if question_index is None:
        raise ValueError("No user question was found before the final answer.")

    diagnosis, basis = extract_diagnosis_and_basis(final_entry["content"])
    patient = extract_patient_data(trajectory)
    last_question = trajectory[question_index]["content"]

    print("=== Parsed trajectory ===")
    print(f"Diagnosis: {diagnosis}")
    print(f"Basis: {basis}")
    print(f"Patient fields: {list(patient.keys()) if patient else 'no get_patient payload'}")
    print("")

    if args.dry_run:
        print("dry-run: model call skipped.")
        env_preview = build_env(patient)
        print("---- Generated environment ----")
        print(env_preview)
        return

    env = build_env(patient)
    tokenizer = load_tokenizer(args.tokenizer)

    constraint_lines = [
        "Use external search support before finalizing the answer.",
        "Keep reasoning inside <think>...</think>.",
        "Put the final response inside <answer>...</answer>.",
        "Use concise, clinically faithful language.",
        f"Use at most {args.max_searches} searches.",
    ]
    constraint_text = "\n".join(f"- {line}" for line in constraint_lines)
    base_instruction = last_question or "Review the patient trajectory and answer the clinical question."
    question = (
        f"{base_instruction}\n\n"
        f"Current diagnosis: {diagnosis or ''}.\n"
        f"Current basis: {basis or ''}.\n"
        f"{constraint_text}"
    )

    print("=== DeepResearch model ===")
    _, tool_calls, generated_traj = run_agent(
        question=question,
        env=env,
        schemas=MEDICAL_SCHEMAS,
        args=args,
        tokenizer=tokenizer,
    )

    print(f"Tool calls: {len(tool_calls)}")
    ensure_search_steps(generated_traj)

    final_step = extract_generated_final_step(generated_traj)
    final_content_override: Optional[str] = None
    evidences = collect_tool_evidence(generated_traj)
    summary_text = summarize_answer(diagnosis, basis, evidences, args)
    if summary_text:
        final_content_override = rewrite_final_step_content(final_step["content"], summary_text)

    merged = merge_trajectory(
        original=trajectory,
        generated=generated_traj,
        question_index=question_index,
        final_step_override=final_content_override,
    )

    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK: {output_path}")


if __name__ == "__main__":
    main()
