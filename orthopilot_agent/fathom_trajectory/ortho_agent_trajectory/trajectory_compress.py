

"""
轨迹压缩工具 - Trajectory Compression Tool

【背景】
已使用 Fathom-DeepResearch/ortho_agent_trajectory/trajectory_enhancer_r1.py
构造了轨迹数据,现需要对轨迹结果进行压缩和精简。

【输入文件】
- 路径: Fathom-DeepResearch/data/轨迹构建/T1/output/search_r1.jsonl
- 格式: JSONL (每行一个JSON对象)

【输出文件】
- 路径: Fathom-DeepResearch/data/轨迹构建/T1/output/search_r1_compressed.jsonl
- 格式: JSONL (压缩后的轨迹数据)

【压缩要求】
1. 使用模型: gpt-4o
2. 搜索步骤精简: 只保留与最终结果强相关的搜索步骤(1~2个)
3. 强相关判断标准:
   - 该搜索步骤直接贡献于最终答案
   - 该搜索结果被后续推理或结论引用
   - 去除冗余、重复或探索性的搜索

【处理流程】
1. 读取原始轨迹文件 (search_r1.jsonl)
2. 对每条轨迹调用 GPT-4o 进行分析和压缩
3. 保留核心搜索步骤,移除冗余信息
4. 保存压缩后的轨迹数据

【注意事项】
- 保持轨迹的逻辑连贯性
- 确保压缩后仍能反映问题解决的关键路径
- 保留必要的上下文信息以便后续使用
- 最终只在开头加入一些简单的使用说明，不要写额外的readme；尽量保持代码的简洁，不要太冗余

【使用方法】
python ortho_agent_trajectory/trajectory_compress.py \
    --input data/轨迹构建/T1/output/search_r1.jsonl \
    --output data/轨迹构建/T1/output/search_r1_compressed.jsonl
    --workers 10
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

REWRITE_PROMPT = """你是一名资深骨科住院医生。请基于以下信息,重写一个完整的、逻辑连贯的入院诊断推理过程。

【患者问题】
{question}

【最终诊断(必须保持不变)】
{final_answer}

【原始搜索信息(供参考)】
{trajectory}

【重写任务】
从头开始构建一个完整的诊断推理过程,要求:

1. **初始分析** - 在第一个<think>中:
   - 分析患者主诉、现病史、专科情况、辅助检查
   - 提出初步诊断思路
   - 明确需要检索的关键问题

2. **搜索与推理** - 选择1-2个最关键的搜索:
   - <search>: 使用完整、明确的搜索词(不要只写"诊断标准",要写清楚是什么疾病的诊断标准)
   - <information>: 从原始搜索结果中选择1-2个最相关的网页,保留完整URL和snippet
   - <think>: 分析搜索结果,引用来源时只提及网站名称或文献名称,不要写URL
     例如: "根据中华骨科杂志2018年指南..." 或 "根据妙佑医疗国际的诊疗建议..."

3. **逻辑推理** - 确保:
   - 推理过程连贯,每步有明确依据
   - 语句通顺,无语病
   - 去除"我现在需要..."等元认知表述
   - <think>中不要出现URL链接
   - 推理过程必须能够支撑最终诊断

4. **最终诊断** - 在<answer>中给出诊断
   - **重要**: <answer>标签中的内容必须完全等于【最终诊断】,一个字都不能改变

【特别要求】
- <search>必须是完整明确的查询词(如"骨关节炎诊断标准"而非"诊断标准")
- <information>只保留1-2个最相关的网页结果,必须包含完整URL和snippet
- <think>中引用时只提及来源名称,不写URL
- 推理过程要符合医学逻辑,简洁明了
- <answer>内容必须与【最终诊断】完全一致

【输出格式示例】
<think>患者主诉左髋疼痛1年余,影像学显示关节间隙狭窄、股骨头坏死。根据临床表现,初步考虑退行性骨关节病,需检索诊断标准进行确认。</think>

<search>髋关节骨关节炎诊断标准</search>

<information>
### 1. 骨关节炎诊疗指南（2018年版） - 中华骨科杂志
**URL**: https://cmab.yiigle.com/uploads/guide_html/骨关节炎诊疗指南（2018年版）.html
**Snippet**: X线检查为OA明确临床诊断的"金标准"，髋关节间隙变窄是本病特征...

---

### 2. 骨关节炎- 诊断与治疗- 妙佑医疗国际
**URL**: https://www.mayoclinic.org/zh-hans/diseases-conditions/osteoarthritis/diagnosis-treatment/drc-20351930
**Snippet**: X线检查可通过关节中骨骼之间的间隙变窄来发现软骨流失...
</information>

<think>根据中华骨科杂志2018年指南,X线显示关节间隙变窄是骨关节炎的典型表现。患者影像学符合该标准,结合病史和年龄,诊断为老年性髋关节病。</think>

<answer>{final_answer}</answer>

直接返回完整的重写轨迹,不要有任何额外的解释文字。"""


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """读取JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def save_jsonl(data: List[Dict[str, Any]], file_path: Path):
    """保存为JSONL文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def trajectory_to_text(trajectory: List[Dict[str, str]]) -> str:
    """将轨迹数组转换为文本,包含完整的对话流程(gpt和user消息)"""
    text_parts = []
    for turn in trajectory:
        role = turn.get('role', '')
        content = turn.get('content', '')

        # 跳过system消息
        if role == 'system':
            continue

        # 保留gpt和user的所有内容
        if content:
            text_parts.append(content)

    return '\n\n'.join(text_parts)


def extract_final_answer(trajectory: List[Dict[str, str]]) -> str:
    """从轨迹中提取最终答案"""
    for turn in reversed(trajectory):
        if turn.get('role') == 'gpt':
            content = turn.get('content', '')
            # 查找<answer>标签
            import re
            match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
            if match:
                return match.group(1).strip()
    return ""


def compress_trajectory(trajectory: List[Dict[str, str]], question: str, client: OpenAI) -> str:
    """使用GPT-4o重写完整的诊断轨迹,返回重写后的output文本"""

    # 将轨迹转换为文本(包含所有信息)
    trajectory_text = trajectory_to_text(trajectory)

    # 提取最终答案
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

        # 返回重写后的文本
        rewritten_output = response.choices[0].message.content.strip()
        return rewritten_output

    except Exception as e:
        print(f"重写失败: {e}, 保留原轨迹")
        return trajectory_text


def save_single_item(item: Dict[str, Any], output_path: Path, lock: threading.Lock):
    """追加保存单个数据项到JSONL文件(线程安全)"""
    with lock:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def process_single_item(item: Dict[str, Any], idx: int, total: int, client: OpenAI, rl_instruction: str, output_path: Path, lock: threading.Lock) -> None:
    """处理单个轨迹数据项"""
    print(f"\n[{idx + 1}/{total}] 开始处理: {item.get('question', '')[:50]}...")

    if 'trajectory' not in item or not isinstance(item['trajectory'], list):
        print(f"[{idx + 1}/{total}] 跳过: 无有效trajectory字段")
        return

    try:
        # 重写生成output
        rewritten_output = compress_trajectory(item['trajectory'], item.get('question', ''), client)

        # 创建新的三字段格式
        compressed_item = {
            'input': item.get('question', ''),
            'instruction': rl_instruction,
            'output': rewritten_output
        }

        # 立即保存
        save_single_item(compressed_item, output_path, lock)
        print(f"[{idx + 1}/{total}] 完成并已保存")

    except Exception as e:
        print(f"[{idx + 1}/{total}] 处理失败: {e}")


def compress_dataset(input_path: Path, output_path: Path, api_key: str, base_url: str = None, max_workers: int = 5):
    """使用多线程压缩整个数据集"""

    # 初始化OpenAI客户端
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    # 读取原始数据
    print(f"读取数据: {input_path}")
    data = load_jsonl(input_path)
    print(f"共加载 {len(data)} 条轨迹")
    print(f"使用 {max_workers} 个线程处理\n")

    # 定义适合RL训练的instruction
    rl_instruction = """你是一名资深骨科住院医生，能够借助医学搜索工具逐步解决入院诊断问题。面对一个患者的入院记录，你需要先思考推理过程，然后给出最终入院诊断。在思考过程中，如有需要，你可以调用搜索工具来获取医学知识。推理过程和答案分别用<think></think>和<answer></answer>标签括起来，搜索查询和结果分别用<search></search>和<information></information>标签括起来。"""

    # 清空或创建输出文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    # 创建线程锁
    lock = threading.Lock()

    # 使用线程池处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, item in enumerate(data):
            future = executor.submit(
                process_single_item,
                item, idx, len(data), client, rl_instruction, output_path, lock
            )
            futures.append(future)

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"线程执行错误: {e}")

    print(f"\n所有任务完成! 结果已保存到: {output_path}")


def main():
    # 加载 scripts/.env 文件
    env_path = Path(__file__).parent.parent / 'scripts' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"已加载环境变量: {env_path}\n")

    parser = argparse.ArgumentParser(description="轨迹压缩工具 (多线程)")
    parser.add_argument(
        '--input',
        type=str,
        default='data/轨迹构建/T1/output/search_r1.jsonl',
        help='输入JSONL文件路径'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/轨迹构建/T1/output/search_r1_compressed.jsonl',
        help='输出JSONL文件路径'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API Key (默认从环境变量OPENAI_API_KEY读取)'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default=None,
        help='OpenAI Base URL (默认从环境变量OPENAI_BASE_URL读取)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='并发线程数 (默认: 5)'
    )

    args = parser.parse_args()

    # 从环境变量或命令行获取配置
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    base_url = args.base_url or os.getenv('OPENAI_BASE_URL')

    if not api_key:
        print("错误: 未提供API Key. 请通过 --api-key 参数或设置 OPENAI_API_KEY 环境变量")
        return

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        return

    print(f"使用配置:")
    print(f"  API Key: {api_key[:10]}...")
    print(f"  Base URL: {base_url or '默认'}")
    print(f"  线程数: {args.workers}")
    print()

    compress_dataset(input_path, output_path, api_key, base_url, args.workers)


if __name__ == '__main__':
    main()
