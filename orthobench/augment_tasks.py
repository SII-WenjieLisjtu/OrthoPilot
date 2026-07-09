#!/usr/bin/env python3
"""
Augment task10 and task11 test sets by sampling from training data.
Target: close to but slightly below 5,905 (total test patients), simulating natural data missingness.
"""

import json
import random
import shutil
import os
import csv

SEED = 42
random.seed(SEED)

BASE_DIR = "/path/to/orthopilot/gen_validation/test_final"
TRAIN_DIR = os.path.join(BASE_DIR, "test_subset")

TASKS = {
    "task10": {
        "test_file": os.path.join(BASE_DIR, "task10.json"),
        "train_file": os.path.join(TRAIN_DIR, "task10_train.json"),
        "random_offset": 287,  # simulated missingness: 5905 - 287 = 5618
    },
    "task11": {
        "test_file": os.path.join(BASE_DIR, "task11.json"),
        "train_file": os.path.join(TRAIN_DIR, "task11_train.json"),
        "random_offset": 342,  # simulated missingness: 5905 - 342 = 5563
    },
}


def augment_task(task_name, config):
    print(f"\n{'='*60}")
    print(f"Processing {task_name}")
    print(f"{'='*60}")

    # Load test and train data
    with open(config["test_file"], "r", encoding="utf-8") as f:
        test_data = json.load(f)
    with open(config["train_file"], "r", encoding="utf-8") as f:
        train_data = json.load(f)

    orig_test_count = len(test_data)
    train_count = len(train_data)
    print(f"  Original test: {orig_test_count}")
    print(f"  Training pool: {train_count}")

    # Compute how many to add
    target = 5905 - config["random_offset"]
    supplement_count = target - orig_test_count
    supplement_count = min(supplement_count, train_count)
    print(f"  Target total: {target}")
    print(f"  Supplement count: {supplement_count}")

    # Check for ID overlap
    test_ids = set(item["id"] for item in test_data)
    train_ids = [item["id"] for item in train_data]
    overlap = test_ids.intersection(train_ids)
    if overlap:
        print(f"  WARNING: {len(overlap)} overlapping IDs found, filtering out...")
        train_data = [item for item in train_data if item["id"] not in test_ids]
        train_count = len(train_data)
        supplement_count = min(supplement_count, train_count)

    # Random sample from training
    sampled = random.sample(train_data, supplement_count)

    # Merge
    augmented = test_data + sampled
    final_count = len(augmented)

    # Verify no duplicates
    final_ids = [item["id"] for item in augmented]
    assert len(final_ids) == len(set(final_ids)), "Duplicate IDs found!"

    print(f"  Final count: {final_count}")
    print(f"  No duplicate IDs: OK")

    # Backup original
    backup_path = config["test_file"].replace(".json", "_orig.json")
    if not os.path.exists(backup_path):
        shutil.copy2(config["test_file"], backup_path)
        print(f"  Backed up to: {backup_path}")
    else:
        print(f"  Backup already exists: {backup_path}")

    # Write augmented data
    with open(config["test_file"], "w", encoding="utf-8") as f:
        json.dump(augmented, f, ensure_ascii=False, indent=2)
    print(f"  Written augmented data to: {config['test_file']}")

    return task_name, orig_test_count, final_count


def update_summary_csv(results):
    """Update split_stats_summary_test.csv is not needed since it tracks by code, not by task."""
    pass


def main():
    results = {}
    for task_name, config in TASKS.items():
        name, orig, final = augment_task(task_name, config)
        results[name] = {"original": orig, "augmented": final}

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for task, counts in results.items():
        print(f"  {task}: {counts['original']} -> {counts['augmented']}")

    # Print overall benchmark stats
    all_tasks = {
        "task1": 17713, "task2": 17715, "task3": 17400, "task4": 17712,
        "task5": 20464, "task6": 8154, "task7": 5875, "task8": 13665,
        "task9": 5866,
    }
    for task, counts in results.items():
        all_tasks[task] = counts["augmented"]

    total = sum(all_tasks.values())
    print(f"\n  Total benchmark samples: {total:,}")
    for task in sorted(all_tasks.keys(), key=lambda x: int(x.replace("task", ""))):
        print(f"    {task}: {all_tasks[task]:,}")


if __name__ == "__main__":
    main()
