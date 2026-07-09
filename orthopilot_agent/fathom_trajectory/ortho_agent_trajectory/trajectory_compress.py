"""Trajectory compression utility for public OrthoPilot trajectory examples.

The script reads JSONL trajectory records, asks an OpenAI-compatible model to
rewrite each trajectory into a concise search-and-answer trace, and writes the
compressed JSONL output.
"""

import json
import argparse
import os
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

REWRITE_PROMPT = """You are a clinical trajectory editor.

Patient question:
{question}

Final answer:
{final_answer}

Original trajectory:
{trajectory}

Task:
Rewrite the trajectory into a concise and faithful trace. Keep only the steps needed to support the final answer.

Required structure:
1. A short <think> block that summarizes the clinical question and what evidence is needed.
2. One or two <search> blocks with focused search queries.
3. Matching <information> blocks with a title, URL if available, and a short evidence snippet.
4. A final <think> block explaining how the evidence supports the answer.
5. The unchanged final answer inside <answer>...</answer>.

Do not invent evidence. Preserve clinical meaning. Return only the rewritten trajectory.
"""

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load records from a JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def save_jsonl(data: List[Dict[str, Any]], file_path: Path):
    """Write items to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def trajectory_to_text(trajectory: List[Dict[str, str]]) -> str:
    """,(GPT user)"""
    text_parts = []
    for turn in trajectory:
        role = turn.get('role', '')
        content = turn.get('content', '')

        # skipsystem
        if role == 'system':
            continue

        # GPT user content
        if content:
            text_parts.append(content)

    return '\n\n'.join(text_parts)


def extract_final_answer(trajectory: List[Dict[str, str]]) -> str:
    """answer"""
    for turn in reversed(trajectory):
        if turn.get('role') == 'gpt':
            content = turn.get('content', '')
            # <answer>
            import re
            match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
            if match:
                return match.group(1).strip()
    return ""


def compress_trajectory(trajectory: List[Dict[str, str]], question: str, client: OpenAI) -> str:
    """GPT-4o,output"""

    # ()
    trajectory_text = trajectory_to_text(trajectory)

    # answer
    final_answer = extract_final_answer(trajectory)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": REWRITE_PROMPT.format(
                    question=question,
                    final_answer=final_answer,
                    trajectory=trajectory_text
                )}
            ],
            temperature=0.3
        )

        #
        rewritten_output = response.choices[0].message.content.strip()
        return rewritten_output

    except Exception as e:
        print(f"error: failed to compress trajectory: {e}")
        return trajectory_text


def save_single_item(item: Dict[str, Any], output_path: Path, lock: threading.Lock):
    """Append one item to a JSONL file."""
    with lock:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def process_single_item(item: Dict[str, Any], idx: int, total: int, client: OpenAI, rl_instruction: str, output_path: Path, lock: threading.Lock) -> None:
    """"""
    print(f"\n[{idx + 1}/{total}] start processing: {item.get('question', '')[:50]}...")

    if 'trajectory' not in item or not isinstance(item['trajectory'], list):
        print(f"[{idx + 1}/{total}] skip: valid trajectory")
        return

    try:
        # generateoutput
        rewritten_output = compress_trajectory(item['trajectory'], item.get('question', ''), client)

        #
        compressed_item = {
            'input': item.get('question', ''),
            'instruction': rl_instruction,
            'output': rewritten_output
        }

        # save
        save_single_item(compressed_item, output_path, lock)
        print(f"[{idx + 1}/{total}] save")

    except Exception as e:
        print(f"[{idx + 1}/{total}]: {e}")


def compress_dataset(input_path: Path, output_path: Path, api_key: str, base_url: str = None, max_workers: int = 5):
    """"""

    # OpenAI
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    #
    print(f": {input_path}")
    data = load_jsonl(input_path)
    print(f"Loaded {len(data)} records")
    print(f" {max_workers} \n")

    # RLinstruction
    rl_instruction = """yes clinician,.patient,,.,,.answer<think></think><answer></answer>, result<search></search><information></information>."""

    # output file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    #
    lock = threading.Lock()

    #
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, item in enumerate(data):
            future = executor.submit(
                process_single_item,
                item, idx, len(data), client, rl_instruction, output_path, lock
            )
            futures.append(future)

        # task
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"error: {e}")

    print(f"\nTask complete. Result saved to: {output_path}")


def main():
    # load scripts/.env file
    env_path = Path(__file__).parent.parent / 'scripts' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment file: {env_path}\n")

    parser = argparse.ArgumentParser(description=" ()")
    parser.add_argument(
        '--input',
        type=str,
        default='data//T1/output/search_r1.jsonl',
        help='inputJSONLfilepath'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data//T1/output/search_r1_compressed.jsonl',
        help='outputJSONLfilepath'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API Key (defaultOPENAI_API_KEYtext)'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default=None,
        help='OpenAI Base URL (defaultOPENAI_BASE_URL)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help=' (default: 5)'
    )

    args = parser.parse_args()

    #
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    base_url = args.base_url or os.getenv('OPENAI_BASE_URL')

    if not api_key:
        print("error: API Key. --api-key OPENAI_API_KEY ")
        return

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"error: input file does not exist: {input_path}")
        return

    print(f":")
    print(f" API Key: {api_key[:10]}...")
    print(f" Base URL: {base_url or 'default'}")
    print(f": {args.workers}")
    print()

    compress_dataset(input_path, output_path, api_key, base_url, args.workers)


if __name__ == '__main__':
    main()
