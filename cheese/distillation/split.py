import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


THINK_PATTERN = "<think>\n\n</think>\n\n"


def has_empty_think(sample: Dict[str, Any]) -> bool:
    """Return whether a sample contains an empty GPT reasoning block."""
    conversations = sample.get("conversations", [])
    for turn in conversations:
        if turn.get("from") == "gpt":
            value = turn.get("value", "")
            if THINK_PATTERN in value:
                return True
    return False


def process_one_file(input_path: Path, output_path: Path):
    with input_path.open("r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    removed = []
    kept = []
    for sample in data:
        if has_empty_think(sample):
            removed.append(sample)
        else:
            kept.append(sample)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print("=" * 80)
    print(f"file: {input_path.name}")
    print(f"total samples: {len(data)}")
    print(f"removed empty-think samples: {len(removed)}")
    print(f"kept samples: {len(kept)}")


def main():
    parser = argparse.ArgumentParser(description="Remove samples with empty GPT reasoning blocks")
    parser.add_argument("--input_dir", required=True, type=str, help="Directory containing input JSON files")
    parser.add_argument("--output_dir", required=True, type=str, help="Directory for filtered JSON files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in: {input_dir}")

    for json_file in json_files:
        process_one_file(
            input_path=json_file,
            output_path=output_dir / json_file.name,
        )

    print("\nAll files processed")


if __name__ == "__main__":
    main()
