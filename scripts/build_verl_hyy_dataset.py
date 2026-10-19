#!/usr/bin/env python3
"""Build a one-row VERL dataset for the Harbor hyy-rl prototype."""

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = REPO_ROOT / "tasks" / "hyy-rl"
INSTRUCTION_PATH = TASK_PATH / "instruction.md"
TEMPLATE_PATH = TASK_PATH / "environment" / "hyy_config.config"


def build_prompt():
    instruction = INSTRUCTION_PATH.read_text().strip()
    template = TEMPLATE_PATH.read_text().strip()
    return f"""You are completing a TRExFitter configuration for a Harbor task.

Return only the final contents of `/tmp/hyy_config.config`.
Do not include markdown fences, explanations, commands, or shell scripts.

Task instruction:
{instruction}

Starter config:
```config
{template}
```
"""


def build_row(split, index):
    return {
        "data_source": "analysisbakery/harbor-hyy-rl",
        "prompt": [
            {
                "role": "user",
                "content": build_prompt(),
            }
        ],
        "ability": "scientific-config",
        "reward_model": {
            "style": "rule",
            "ground_truth": "graded by Harbor verifier",
        },
        "extra_info": {
            "split": split,
            "index": index,
            "task_path": str(TASK_PATH),
            "candidate_format": "full_hyy_config",
            "score_key": "reward",
            "harbor_timeout_sec": 900,
        },
    }


def write_jsonl(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_parquet(rows, path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Writing parquet requires pandas and pyarrow. Install them in the VERL "
            "environment, or use --format jsonl for adapter smoke tests."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "verl_data" / "hyy_rl",
        help="Directory for train/test dataset files.",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "parquet", "both"],
        default="jsonl",
        help="Output format. VERL training normally consumes parquet.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    train_rows = [build_row("train", 0)]
    test_rows = [build_row("test", 0)]

    if args.format in {"jsonl", "both"}:
        write_jsonl(train_rows, args.output_dir / "train.jsonl")
        write_jsonl(test_rows, args.output_dir / "test.jsonl")

    if args.format in {"parquet", "both"}:
        write_parquet(train_rows, args.output_dir / "train.parquet")
        write_parquet(test_rows, args.output_dir / "test.parquet")

    print(f"Wrote hyy-rl VERL dataset to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
