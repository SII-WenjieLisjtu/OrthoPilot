#!/usr/bin/env python3
"""
trajectory_enhancer.py

读取仅包含最终诊断结果的医疗轨迹, 调用实际 DeepResearch 推理链(模型 + 工具执行器),
补齐诊疗指南/鉴别诊断等搜索步骤, 并回写为完整的 OrthoPilot-compatible trajectory。

示例:
    python3 trajectory_enhancer.py \
        --input data/轨迹构建/T1/example_traj/patient_test_original.json \
        --output data/轨迹构建/T1/example_traj/patient_test_enhanced.json \
        --model-url http://YOUR_HOST:YOUR_PORT \
        --executors http://YOUR_HOST:YOUR_PORT
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

# ---------------------------------------------------------------------------
# 项目内模块导入
# ---------------------------------------------------------------------------
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
    """在未安装transformers时的兜底tokenizer。"""

    def __call__(self, text: str, return_tensors=None, add_special_tokens=False):
        tokens = text.split()
        return {"input_ids": list(range(len(tokens)))}


def load_trajectory(path: Path) -> List[Dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("轨迹文件必须是JSON数组。")
    return data


def find_final_answer_entry(trajectory: List[Dict[str, str]]) -> Dict[str, str]:
    for entry in reversed(trajectory):
        if entry.get("role") == "gpt" and "<answer>" in entry.get("content", ""):
            return entry
    raise ValueError("轨迹缺少最终<answer>步骤。")


def extract_diagnosis_and_basis(answer_content: str) -> Tuple[str, str]:
    diagnosis_match = re.search(r"入院诊断[:：]\s*([^。；;\n]+)", answer_content)
    basis_match = re.search(r"依据[:：]\s*([^<]+)", answer_content)
    diagnosis = diagnosis_match.group(1).strip() if diagnosis_match else "未明确诊断"
    basis = basis_match.group(1).strip().rstrip("。") if basis_match else ""
    return diagnosis, basis


def extract_patient_data(trajectory: List[Dict[str, str]]) -> Dict[str, str]:
    """从原始轨迹中提取 get_patient 的 tool_response 数据."""
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
    raise NotImplementedError("当前任务仅允许使用搜索工具。")

def get_imaging(*args, **kwargs):
    raise NotImplementedError("当前任务仅允许使用搜索工具。")

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
    q = " ".join(filter(None, keywords)) or "骨科 鉴别诊断"
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
        print("[warn] transformers 未安装, 退回简易tokenizer。")
        return SimpleTokenizer()
    print(f"[tokenizer] 加载 {name}")
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True)


def ensure_search_steps(trajectory: List[Dict[str, str]]):
    for entry in trajectory:
        if entry.get("role") == "gpt" and "<tool_call>" in entry.get("content", ""):
            if "search" in entry["content"].lower():
                return
    raise RuntimeError("模型未生成任何带search的工具调用, 请检查提示或环境。")


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
    raise ValueError("增强生成的轨迹缺少最终答案步骤。")


def rewrite_final_step_content(original_content: str, new_answer: str) -> str:
    think_match = re.search(r"<think>(.*?)</think>", original_content, re.DOTALL)
    think_text = think_match.group(1).strip() if think_match else "基于检索证据整合最终结论。"
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
    evidence_text = "\n\n".join(evidences) if evidences else "无检索证据。"

    system_prompt = (
        "你是骨科住院医导师, 需要基于检索到的证据帮助手术医生整理入院诊断依据。\n"
        "输出要求: (1) 用中文给出清晰的入院诊断; (2) 结合证据列出诊断依据, 建议条目化; (3) 若证据不足, 明确指出并给出补充检查建议;"
        "(4) 不添加额外的问候或总结, 直接给出内容。"
    )

    user_prompt = (
        f"原始诊断: {diagnosis or '未提供'}\n"
        f"原始依据: {original_basis or '未提供'}\n"
        f"检索证据:\n{evidence_text}\n"
        "请输出符合要求的诊断与依据总结。"
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
        raise RuntimeError("增强后的轨迹未生成最终答案, 请检查模型输出。")

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
    parser = argparse.ArgumentParser(description="使用实际DeepResearch推理链补齐医疗轨迹搜索步骤")
    parser.add_argument("--input", required=True, help="原始轨迹JSON路径")
    parser.add_argument("--output", help="增强后输出路径, 默认覆盖输入文件")
    parser.add_argument("--model-url", required=True, help="Fathom-Search推理服务URL")
    parser.add_argument("--executors", required=True, help="工具执行器URL (host_server.sh 暴露的地址)")
    parser.add_argument("--tokenizer", default=None, help="可选: HF tokenizer 名称")
    parser.add_argument("--temperature", type=float, default=0.2, help="采样温度")
    parser.add_argument("--max-new-tokens", type=int, default=2048, help="最大生成token数")
    parser.add_argument("--max-searches", type=int, default=5, help="最大搜索次数")
    parser.add_argument("--summary-model", default="gpt-4o", help="用于最终依据总结的OpenAI模型名称")
    parser.add_argument("--summary-temperature", type=float, default=0.2, help="总结调用的采样温度")
    parser.add_argument("--summary-max-tokens", type=int, default=512, help="总结回答的最大token数")
    parser.add_argument("--skip-summary", action="store_true", help="跳过OpenAI总结, 直接使用模型原答案")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件")
    parser.add_argument("--dry-run", action="store_true", help="仅打印解析结果, 不调用模型")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    output_path = Path(args.output) if args.output else input_path
    if output_path.exists() and output_path != input_path and not args.force:
        raise FileExistsError(f"输出文件已存在: {output_path} (使用 --force 覆盖)")

    trajectory = load_trajectory(input_path)
    final_entry = find_final_answer_entry(trajectory)
    final_index = trajectory.index(final_entry)
    question_index: Optional[int] = None
    for idx in range(final_index - 1, -1, -1):
        if trajectory[idx].get("role") == "user":
            question_index = idx
            break
    if question_index is None:
        raise ValueError("未在原始轨迹中找到对应的用户提问步骤, 无法继续增强。")

    diagnosis, basis = extract_diagnosis_and_basis(final_entry["content"])
    patient = extract_patient_data(trajectory)
    last_question = trajectory[question_index]["content"]

    print("=== 轨迹解析 ===")
    print(f"  入院诊断: {diagnosis}")
    print(f"  诊断依据: {basis}")
    print(f"  患者信息字段: {list(patient.keys()) if patient else '无 get_patient 数据'}")
    print("")

    if args.dry_run:
        print("dry-run 模式: 不调用模型。")
        env_preview = build_env(patient)
        print("---- 生成的执行环境 ----")
        print(env_preview)
        return

    env = build_env(patient)
    tokenizer = load_tokenizer(args.tokenizer)

    constraint_lines = [
        "仅可使用搜索工具(禁止调用检验、影像等非搜索函数);",
        "必须通过工具检索获取指南或文献证据后再回答;",
        "最终<answer>需重申原始诊断并结合检索证据阐述依据;",
        "若证据不足, 请明确说明并建议下一步检查;",
        f"搜索工具调用次数请控制在不超过 {args.max_searches} 次。"
    ]
    constraint_text = "\n".join(f"- {line}" for line in constraint_lines)
    base_instruction = last_question or "请基于患者现有信息, 仅使用搜索工具检索所需证据后再给出入院诊断与依据。"
    question = (
        f"{base_instruction}\n\n"
        f"原始诊断: {diagnosis or '未提供'}。\n"
        f"原始依据: {basis or '未提供'}。\n"
        f"{constraint_text}"
    )

    print("=== 调用 DeepResearch 模型 ===")
    _, tool_calls, generated_traj = run_agent(
        question=question,
        env=env,
        schemas=MEDICAL_SCHEMAS,
        args=args,
        tokenizer=tokenizer,
    )

    print(f"  工具调用次数: {len(tool_calls)}")
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
    print(f"\n✓ 已写入增强轨迹: {output_path}")


if __name__ == "__main__":
    main()
