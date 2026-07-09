#!/usr/bin/env python3
"""
trajectory_enhancer_r1.py — 基于 Search‑R1 模板构造“入院诊断”搜索RL轨迹（JSONL）

功能说明（请直接运行脚本，无需额外README）
- 输入：支持指定单个文件（--input-file）或遍历目录（--input-dir）。输入文件需与
  data/轨迹构建/T1/example 下样例相同结构，仅使用其中的 "basic_info" 与 "入院记录" 两部分。
- 处理（默认严格按 RL 推理输入要求）：
  1) 模型推理用问题（内部 question）仅注入入院记录的 5 项：主诉、现病史、专科情况、辅助检查、手术外伤史；默认不拼接 basic_info（可用 --include-basic-info 开启）。
  2) Prompt 字段为中文 system + 中文 user 的 Search‑R1 模板：
     - system：说明 <think>/<search>/<information>/<answer> 的工作流与输出规范；
     - user：简短问题“请阅读以下入院记录信息，回答该患者的入院诊断是什么？”。
  3) 运行 ReCallMedical 多轮搜索；生成后把 <tool_call> → <search>，<tool_response> → <information>，并保留 <think>/<answer>，得到完整 Search‑R1 轨迹。
  4) 不泄露 GT：不在问题、环境与思考/检索中出现 basic_info.入院诊断。GT 仅用于：
     - 兜底：若无任何 <answer>，补一个仅含 <answer>GT</answer> 的最终步；
     - 蒸馏（--distill-with-gt）：在内部 system 注入“教师提示”告知 GT 引导检索，并对输出轨迹在 <answer> 之外屏蔽 GT 字样。
  5) 清洗思考内容，移除“搜索次数/上限”等元信息表述。
- 输出：每个样本一行 JSON（JSONL），字段包含：
  - question: 仅含 5 项入院记录（默认）或包含去敏 basic_info 的首问文本（不含GT）。
  - golden_answers: GT 入院诊断（字符串）。
  - prompt: Search‑R1 模板数组（中文 system + 中文 user）。
  - trajectory: 多轮搜索生成的对话轨迹（含 <think>/<search>/<information>/<answer>，且已清洗/屏蔽）。

基础用法示例：
  # 默认：仅使用入院记录 5 项
  python3 trajectory_enhancer_r1.py \
    --input-dir data/轨迹构建/T1/example \
    --output-jsonl data/轨迹构建/T1/output/search_r1.jsonl \
    --model-url http://YOUR_HOST:YOUR_PORT \
    --executors http://YOUR_HOST:YOUR_PORT

  # 若希望把去敏 basic_info 也写入首问
  python3 trajectory_enhancer_r1.py \
    --include-basic-info \
    --input-file data/轨迹构建/T1/example/patient_362862863157182464.json \
    --output-jsonl data/轨迹构建/T1/output/search_r1.jsonl \
    --model-url http://YOUR_HOST:YOUR_PORT \
    --executors http://YOUR_HOST:YOUR_PORT

  # ✅ 蒸馏：内部告知GT引导检索，但不在轨迹中泄露 
  python3 ortho_agent_trajectory/trajectory_enhancer_r1.py \
    --distill-with-gt \
    --input-dir data/轨迹构建/T1/example \
    --output-jsonl data/轨迹构建/T1/output/search_r1.jsonl \
    --model-url http://YOUR_HOST:YOUR_PORT \
    --executors http://YOUR_HOST:YOUR_PORT
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import sys

# ---------------------------------------------------------------------------
# 项目内模块导入
# ---------------------------------------------------------------------------
sys.path.insert(0,  "agents/inference")

from re_call_medical import ReCallMedical  # type: ignore
from medical_trajectory_generator import MEDICAL_SCHEMAS  # type: ignore

try:
    from transformers import AutoTokenizer  # type: ignore
except Exception:
    AutoTokenizer = None

import debugpy
try:
    # 5678 is the default attach port in the VS Code debug configurations. Unless a host and port are specified, host defaults to 127.0.0.1
    debugpy.listen(("localhost", 8906))
    print("Waiting for debugger attach")
    debugpy.wait_for_client()
except Exception as e:
    pass

# ------------------------------ 工具函数 -----------------------------------

def _is_nan(x: Any) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def _sanitize(obj: Any) -> Any:
    """将 NaN/None 等不可用值替换为空字符串，递归处理 dict/list。"""
    if _is_nan(obj) or obj is None:
        return ""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def load_patient(filepath: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    basic_info = _sanitize(data.get("basic_info", {}))
    admission_list = _sanitize(data.get("入院记录", []))
    admission = admission_list[0] if isinstance(admission_list, list) and admission_list else {}
    return basic_info, admission


def patient_summary_text(basic_info: Dict[str, Any], admission: Dict[str, Any], *, admission_only: bool = False) -> str:
    """组装进入首问的文本。

    - admission_only=True: 仅使用 入院记录 的五个字段：主诉/现病史/专科情况/辅助检查/手术外伤史。
    - admission_only=False: 在不暴露GT的前提下，包含去敏的 basic_info 与较全的入院记录。
    """
    # 仅入院字段模式
    if admission_only:
        keys_order = ["主诉", "现病史", "专科情况", "辅助检查", "手术外伤史"]
        ad_lines = []
        for k in keys_order:
            v = admission.get(k, "")
            if v:
                ad_lines.append(f"{k}：{v}")
        ad_text = "\n".join(ad_lines).strip()
        return ("【入院记录】\n" + ad_text) if ad_text else ""

    # 默认模式：包含去敏 basic_info + 入院常用信息（不含GT）
    blacklist = {"入院诊断", "入院诊断编码"}
    bi_lines = []
    for k, v in basic_info.items():
        if k in blacklist or v == "":
            continue
        if k in ("姓名", "证件号码", "联系电话", "联系地址", "住院号", "EMPI"):
            continue  # 脱敏/无关
        bi_lines.append(f"{k}：{v}")

    keys_order = ["主诉", "现病史", "专科情况", "体格检查", "辅助检查", "手术外伤史", "一般健康状况"]
    ad_lines = []
    for k in keys_order:
        v = admission.get(k, "")
        if v:
            ad_lines.append(f"{k}：{v}")

    bi_text = "\n".join(bi_lines).strip()
    ad_text = "\n".join(ad_lines).strip()
    pieces = []
    if bi_text:
        pieces.append("【基本信息】\n" + bi_text)
    if ad_text:
        pieces.append("【入院记录】\n" + ad_text)
    return "\n\n".join(pieces)


CHINESE_R1_SYSTEM = (
    "你是一名资深骨科住院医生。请遵循 Search‑R1 工作流：\n"
    "- 仅使用搜索类工具；不要提出新增影像/检验/治疗建议，不做与工具无关的推断；\n"
    "- 每次获得新信息后，先在<think></think>内引用最近一次<information>的关键信息（如标题/来源/年份），再做简洁推理；\n"
    "- 若知识不足，通过<search> 中文关键词 </search> 发起检索；<search>中应为真实查询词，不使用占位符；\n"
    "- 搜索引擎会返回 <information> ... </information>；可多次检索；\n"
    "- 当已具备充分信息时，仅在<answer></answer>中给出明确的入院诊断疾病名称；不要泄露任何真实标注/工具次数等元信息，也不要解释过程。\n"
)

def build_search_r1_prompt(short_question: str, info_text: str) -> List[Dict[str, str]]:
    """生成符合本任务的 Search‑R1 提示（中文 system + 中文 user），并在 user 中附上完整入院记录文本。"""
    user_content = f"{short_question}\n\n{info_text}" if info_text else short_question
    return [
        {"role": "system", "content": CHINESE_R1_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def build_env_for_patient(patient_payload: Dict[str, Any]) -> str:
    """限制仅搜索相关函数 + 患者数据访问，避免非搜索工具。"""
    def python_literal(d: Dict[str, Any]) -> str:
        return repr(d)
    # 在构造“工具执行环境”的源码字符串，交给工具执行器运行，用来支撑代理在推理过程中实际调用搜索类工具。
    env = f"""
from search_api import search_urls as _search_urls, query_url as _query_url
from kg_api import kg_search, kg_get_relations, kg_fuzzy_search, medibook_search, semanticscholar_search
from medrag_api import wikipedia_search, pubmed_search, textbooks_search, statpearls_search

def search_guidelines(query, domain=None, top_k=5, _search=_search_urls):
    if domain:
        q = (str(domain) + " " + str(query)).strip()
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
"""
    return env.strip()


def sanitize_gpt_content(content: str, banned_terms: Optional[List[str]] = None) -> str:
    """清洗GPT文本：
    - 移除“搜索上限/剩余搜索”等元信息；
    - 屏蔽 banned_terms（如GT）在<think>/<search>/<information>中的明示，但不改动<answer>内文本。
    """
    if not content:
        return content

    # 去掉常见提示语句（中文/英文）
    patterns = [
        r"最多\s*\d+\s*次搜索",
        r"搜索次数[：: ]?\d+/?\d+",
        r"剩余(可)?搜索\s*\d+\s*次",
        r"search(es)?\s*left",
        r"max\s*search(es)?",
        r"limit(ed)?\s*to\s*\d+\s*search",
        r"(建议|需要|应当|可考虑).*(MRI|CT|影像|X[-\s]?ray|检验|化验)",
        r"get_imaging|get_lab_results",
    ]
    cleaned = content
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # 屏蔽敏感词（仅<answer>之外）
    if banned_terms:
        tokens = re.split(r"(<answer>.*?</answer>)", cleaned, flags=re.DOTALL)

        def mask_text(text: str) -> str:
            out = text
            for term in banned_terms:
                if not term:
                    continue
                out = re.sub(re.escape(term), "", out)
                spaced = r"".join([re.escape(ch) + r"\s*" for ch in term])
                out = re.sub(spaced, "", out, flags=re.IGNORECASE)
            return out

        cleaned = "".join(seg if i % 2 == 1 else mask_text(seg) for i, seg in enumerate(tokens))

    return cleaned


def ensure_final_answer(trajectory: List[Dict[str, str]], golden: str) -> List[Dict[str, str]]:
    """保证最终<answer>仅为入院诊断（golden）。若已有<answer>，覆盖为golden。"""
    replaced = False
    for step in reversed(trajectory):
        if step.get("role") == "gpt" and "<answer>" in step.get("content", ""):
            content = step.get("content", "")
            # 保留原<think>，覆盖<answer>
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            think_text = think_match.group(1).strip() if think_match else "基于检索证据，已可给出结论。"
            step["content"] = f"<think>{sanitize_gpt_content(think_text)}</think><answer>{golden}</answer>"
            replaced = True
            break
    if not replaced:
        final = f"<think>基于检索证据，已可给出结论。</think><answer>{golden}</answer>"
        trajectory.append({"role": "gpt", "content": final})
    return trajectory


TOOL_CALL_RE = re.compile(r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL)
TOOL_RESP_RE = re.compile(r"<tool_response>(.*?)</tool_response>", re.DOTALL)


def _tool_call_to_search_tag(tool_call_json_str: str) -> str:
    try:
        data = json.loads(tool_call_json_str)
        name = (data.get("name") or "").strip()
        args = data.get("arguments", {}) or {}
        query = ""
        if name in ("search_guidelines", "search_web"):
            query = str(args.get("query", "")).strip()
        elif name == "search_differential_diagnosis":
            # 组装 symptoms/age/specialty 为一个查询字符串
            parts = []
            sym = args.get("symptoms")
            if sym:
                parts.extend(sym if isinstance(sym, list) else [sym])
            if args.get("age"):
                parts.append(str(args.get("age")))
            if args.get("specialty"):
                parts.append(str(args.get("specialty")))
            query = " ".join([p for p in parts if p])
        else:
            return ""  # 非搜索工具不输出
        return f"<search> {query} </search>" if query else ""
    except Exception:
        return ""


def transform_gpt_to_search_r1(content: str) -> str:
    """将 GPT 内容中的 <tool_call> 转换为 <search> 标签，保留<think>/<answer>。"""
    if not content:
        return content
    def repl(m):
        return _tool_call_to_search_tag(m.group(1))
    converted = TOOL_CALL_RE.sub(repl, content)
    return converted


def transform_user_to_information(content: str, banned_terms: Optional[List[str]] = None) -> str:
    """将 tool_response 块转换为 <information> ... </information>。"""
    if not content:
        return content
    infos: List[str] = []
    for m in TOOL_RESP_RE.finditer(content):
        inner = m.group(1)
        # 兼容 {"tool":...,"data":...} 结构
        data_str = inner
        try:
            j = json.loads(inner)
            if isinstance(j, dict) and "data" in j:
                data_str = j["data"]
                if isinstance(data_str, (dict, list)):
                    data_str = json.dumps(data_str, ensure_ascii=False)
        except Exception:
            pass
        if banned_terms:
            for term in banned_terms:
                if term:
                    data_str = re.sub(re.escape(term), "", data_str)
        infos.append(f"<information>\n{data_str}\n</information>")
    return "\n".join(infos) if infos else ""


def to_search_r1_trajectory(raw: List[Dict[str, str]], short_question: str, info_text: str, banned_terms: Optional[List[str]] = None) -> List[Dict[str, str]]:
    new_traj: List[Dict[str, str]] = []
    # 1) 固定的中文 system + 简短问题 user
    new_traj.append({"role": "system", "content": CHINESE_R1_SYSTEM})
    first_user = f"{short_question}\n\n{info_text}" if info_text else short_question
    new_traj.append({"role": "user", "content": first_user})

    # 2) 遍历原轨迹，将assistant中的<tool_call>改为<search>，将user中的<tool_response>改为<information>
    for step in raw:
        r = step.get("role")
        c = step.get("content", "")
        if r == "gpt":
            c2 = sanitize_gpt_content(transform_gpt_to_search_r1(c), banned_terms=banned_terms)
            new_traj.append({"role": "gpt", "content": c2})
        elif r == "user":
            info = transform_user_to_information(c, banned_terms=banned_terms)
            if info:
                new_traj.append({"role": "user", "content": info})
        # 跳过原 system
    # 截断：一旦出现含<answer>的assistant步，后续步骤全部丢弃
    cut_idx = None
    for i, st in enumerate(new_traj):
        if st.get("role") == "gpt" and "<answer>" in st.get("content", ""):
            cut_idx = i
            break
    if cut_idx is not None:
        new_traj = new_traj[: cut_idx + 1]
    return new_traj


def run_agent(question: str, env: str, schemas: List[Dict[str, Any]], args, tokenizer, *, distill_with_gt: bool = False, golden: str = "") -> List[Dict[str, str]]:
    teacher_hint = None
    if distill_with_gt and golden:
        teacher_hint = (
            "你已知最终入院诊断为：" + str(golden) + "。\n"
            "此信息仅用于指导更快检索相关证据；严禁在<think>/<search>/<information>中出现该疾病名称或同义表达。最终只在<answer>内给出疾病名称。"
        )
    agent = ReCallMedical(
        executor_url=args.executors,
        max_searches=args.max_searches,
        sys_prompt=None,
        teacher_hint=teacher_hint,
        suppress_logs=True,
    )
    _, _tool_calls, traj = agent.run(
        env=env,
        func_schemas=json.dumps(schemas, ensure_ascii=False, indent=2),
        question=question,
        model_url=args.model_url,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        tokenizer=tokenizer,
    )
    # 清洗 gpt 步的思考内容
    for step in traj:
        if step.get("role") == "gpt":
            step["content"] = sanitize_gpt_content(
                step.get("content", ""),
                banned_terms=[golden] if distill_with_gt and golden else None,
            )
    return traj


def load_tokenizer(name: Optional[str]):
    if not name:
        return lambda x, **_: {"input_ids": list(range(len(x.split()))) }
    if AutoTokenizer is None:
        print("[warn] transformers 未安装, 使用简易分词统计。")
        return lambda x, **_: {"input_ids": list(range(len(x.split()))) }
    print(f"[tokenizer] 加载 {name}")
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True)


def build_question(basic_info: Dict[str, Any], admission: Dict[str, Any], *, admission_only: bool) -> str:
    info_text = patient_summary_text(basic_info, admission, admission_only=admission_only)
    prefix = (
        "请阅读以下入院记录信息，结合权威指南/文献进行必要检索与推理，"
        if admission_only else
        "请阅读以下患者信息与入院记录，结合权威指南/文献进行必要检索与推理，"
    )
    return (
        f"{prefix}"
        "回答该患者的入院诊断是什么？\n\n"
        f"{info_text}"
    )


def process_one_file(filepath: Path, args, out_f):
    breakpoint()
    basic_info, admission = load_patient(filepath)
    golden = str(basic_info.get("入院诊断", "")).strip()

    # 构造 question 与 prompt（问题中不包含GT）
    admission_only = not getattr(args, "include_basic_info", False)
    # 给模型实际推理用的完整问题（含入院记录文本）
    question = build_question(basic_info, admission, admission_only=admission_only)
    # 轨迹与prompt首条 user：简短问题 + 完整入院记录文本
    short_question = "请阅读以下入院记录信息，回答该患者的入院诊断是什么？"
    # 这里是组织question的，我们其他就不用了
    # TODO
    info_text = patient_summary_text(basic_info, admission, admission_only=admission_only)
    prompt_array = build_search_r1_prompt(short_question, info_text)

    # 仅传入 basic_info/入院记录 构造 env
    # payload = {
    #     # admission_only 模式下也保留 basic_info 供工具可读（不注入到问题文本）
    #     "basic_info": {k: v for k, v in basic_info.items() if k not in ("入院诊断", "入院诊断编码")},
    #     "入院记录": admission,
    # }
    # env = build_env_for_patient(payload)
    env = build_env_for_patient({})

    # tokenizer
    tokenizer = load_tokenizer(args.tokenizer)
    # TODO：需要检查每个Prompt是啥样的
    # 运行 agent 生成轨迹，仅保留 搜索相关schema
    # ALLOWED = {"get_patient", "search_guidelines", "search_differential_diagnosis", "search_web", "visit_url"}
    # R1_SCHEMAS = [s for s in MEDICAL_SCHEMAS if s.get("name") in ALLOWED]
    R1_SCHEMAS = MEDICAL_SCHEMAS
    raw_traj = run_agent(
        question=question,
        env=env,
        schemas=R1_SCHEMAS,
        args=args,
        tokenizer=tokenizer,
        distill_with_gt=args.distill_with_gt,
        golden=golden,
    )

    # 若无答案则补全；并确保不泄露上限/GT
    trajectory = ensure_final_answer(raw_traj, golden)
    # 转换为 Search‑R1 标签轨迹，并在首条 user 中附上入院记录文本
    trajectory = to_search_r1_trajectory(
        trajectory,
        short_question,
        info_text,
        banned_terms=[golden] if args.distill_with_gt and golden else None,
    )

    record = {
        "question": question,
        "golden_answers": golden,
        "prompt": prompt_array,
        "trajectory": trajectory,
        "source_file": str(filepath),
    }
    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")


def iter_input_files(args) -> List[Path]:
    files: List[Path] = []
    if args.input_file:
        p = Path(args.input_file)
        if p.is_file() and p.suffix.lower() == ".json":
            files.append(p)
    if args.input_dir:
        d = Path(args.input_dir)
        if d.is_dir():
            for fp in sorted(d.glob("*.json")):
                files.append(fp)
    if not files:
        raise FileNotFoundError("未找到任何输入文件，请检查 --input-file 或 --input-dir")
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    return files


def main():
    parser = argparse.ArgumentParser(description="基于 Search‑R1 模板构造入院诊断搜索RL轨迹（输出JSONL）")
    parser.add_argument("--input-file", help="单个患者JSON文件路径（与example结构一致）")
    parser.add_argument("--input-dir", help="包含多个患者JSON的目录（遍历*.json）")
    parser.add_argument("--output-jsonl", required=True, help="输出JSONL路径（每行一个样本）")
    parser.add_argument("--model-url", required=True, help="Fathom-Search推理服务URL")
    parser.add_argument("--executors", required=True, help="工具执行器URL (host_server.sh 暴露的地址)")
    parser.add_argument("--tokenizer", default=None, help="可选: HF tokenizer 名称")
    parser.add_argument("--temperature", type=float, default=0.2, help="采样温度")
    parser.add_argument("--max-new-tokens", type=int, default=30000, help="最大生成token数")
    parser.add_argument("--max-searches", type=int, default=8, help="最大搜索次数（仅作为约束，不写入思考过程）")
    parser.add_argument("--distill-with-gt", action="store_true", help="蒸馏：在内部system告知真实诊断引导检索，并对输出轨迹(<think>/<search>/<information>)进行GT屏蔽")
    # 默认严格只用入院记录5项；如需包含 basic_info，请显式开启该选项
    parser.add_argument("--include-basic-info", action="store_true", help="将去敏 basic_info 一并拼入首问问题文本（默认不包含）")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少个文件（0=全部）")
    args = parser.parse_args()

    files = iter_input_files(args)
    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out_f:
        for fp in files:
            print(f"[build] {fp}")
            try:
                process_one_file(fp, args, out_f)
                # 逐条写入后立即落盘，避免缓冲导致的中途丢失
                out_f.flush()
            except Exception as e:
                print(f"[warn] 处理失败: {fp} -> {e}")

    print(f"\n✓ 已生成数据集：{out_path}")


if __name__ == "__main__":
    main()
