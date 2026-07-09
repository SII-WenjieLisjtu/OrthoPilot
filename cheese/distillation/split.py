# import json
# import random
# import argparse
# from pathlib import Path
# from typing import List, Dict, Any


# THINK_PATTERN = "<think>\n\n</think>\n\n"


# def has_empty_think(sample: Dict[str, Any]) -> bool:
#     """
#     判断该 sample 是否在 gpt 的 value 中包含 <think>\n\n</think>\n\n
#     """
#     conversations = sample.get("conversations", [])
#     for turn in conversations:
#         if turn.get("from") == "gpt":
#             value = turn.get("value", "")
#             if THINK_PATTERN in value:
#                 return True
#     return False


# def process_one_file(
#     input_path: Path,
#     output_path: Path,
#     keep_ratio: float,
#     rng: random.Random,
# ):
#     with input_path.open("r", encoding="utf-8") as f:
#         data: List[Dict[str, Any]] = json.load(f)

#     with_think = []
#     without_think = []

#     for sample in data:
#         if has_empty_think(sample):
#             with_think.append(sample)
#         else:
#             without_think.append(sample)

#     # 随机保留 0.15
#     keep_n = int(len(with_think) * keep_ratio)
#     kept_with_think = rng.sample(with_think, keep_n) if keep_n > 0 else []

#     final_data = kept_with_think + without_think

#     # 写出
#     output_path.parent.mkdir(parents=True, exist_ok=True)
#     with output_path.open("w", encoding="utf-8") as f:
#         json.dump(final_data, f, ensure_ascii=False, indent=2)

#     # 打印统计信息
#     print("=" * 80)
#     print(f"文件名: {input_path.name}")
#     print(f"  含 '<think>...</think>' 原始数量 : {len(with_think)}")
#     print(f"  含 '<think>...</think>' 保留数量 : {len(kept_with_think)}")
#     print(f"  不含 '<think>...</think>' 数量     : {len(without_think)}")
#     print(f"  最终写出总数量                   : {len(final_data)}")


# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--input_dir", required=True, type=str, help="输入 json 文件夹")
#     parser.add_argument("--output_dir", required=True, type=str, help="输出 json 文件夹")
#     parser.add_argument("--keep_ratio", type=float, default=0.15, help="think 数据保留比例")
#     parser.add_argument("--seed", type=int, default=42, help="随机种子，保证可复现")
#     args = parser.parse_args()

#     input_dir = Path(args.input_dir)
#     output_dir = Path(args.output_dir)

#     assert input_dir.exists(), f"输入目录不存在: {input_dir}"

#     rng = random.Random(args.seed)

#     json_files = sorted(input_dir.glob("*.json"))
#     assert json_files, "输入目录中没有 json 文件"

#     for json_file in json_files:
#         out_file = output_dir / json_file.name
#         process_one_file(
#             input_path=json_file,
#             output_path=out_file,
#             keep_ratio=args.keep_ratio,
#             rng=rng,
#         )

#     print("\n全部文件处理完成 ✅")


# if __name__ == "__main__":
#     main()


import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


THINK_PATTERN = "<think>\n\n</think>\n\n"


def has_empty_think(sample: Dict[str, Any]) -> bool:
    """
    判断该 sample 是否在 gpt 的 value 中包含 <think>\n\n</think>\n\n
    """
    conversations = sample.get("conversations", [])
    for turn in conversations:
        if turn.get("from") == "gpt":
            value = turn.get("value", "")
            if THINK_PATTERN in value:
                return True
    return False


def process_one_file(
    input_path: Path,
    output_path: Path,
):
    with input_path.open("r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    removed = []
    kept = []

    for sample in data:
        if has_empty_think(sample):
            removed.append(sample)
        else:
            kept.append(sample)

    # 写出
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    # 打印统计信息
    print("=" * 80)
    print(f"文件名: {input_path.name}")
    print(f"  原始总数量                       : {len(data)}")
    print(f"  含 '<think>...</think>' 被删除数量: {len(removed)}")
    print(f"  最终保留数量                     : {len(kept)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, type=str, help="输入 json 文件夹")
    parser.add_argument("--output_dir", required=True, type=str, help="输出 json 文件夹")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    assert input_dir.exists(), f"输入目录不存在: {input_dir}"

    json_files = sorted(input_dir.glob("*.json"))
    assert json_files, "输入目录中没有 json 文件"

    for json_file in json_files:
        out_file = output_dir / json_file.name
        process_one_file(
            input_path=json_file,
            output_path=out_file,
        )

    print("\n全部文件处理完成 ✅")


if __name__ == "__main__":
    main()

