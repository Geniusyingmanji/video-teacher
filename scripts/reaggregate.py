"""Re-compute aggregate.json from an existing per_case.jsonl without re-running eval.

Useful when aggregate() logic changes (e.g., adding per_difficulty breakdown)
and you don't want to re-run all GPT-5.5 calls.

Usage:
    python scripts/reaggregate.py --eval-dir /data/zyf/rise-teacher/outputs/eval_pilot_v0_1
    python scripts/reaggregate.py --eval-dir /data/.../eval_pilot_v0_1_wan13b --prompts data/prompts/pilot_v0_1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make sure the project root is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.run_eval import aggregate, load_jsonl, CORE_DIMS, EXTENDED_DIMS, ALL_DIMS


def detect_dims(per_case_path: str) -> dict:
    """Detect which dims are present in the per_case.jsonl."""
    all_dim_names = set(ALL_DIMS.keys())
    found = set()
    for rec in load_jsonl(per_case_path):
        for d in all_dim_names:
            if d in rec and isinstance(rec[d], dict):
                found.add(d)
    return {d: ALL_DIMS[d] for d in found if d in ALL_DIMS}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True, help="Directory with per_case.jsonl + aggregate.json")
    ap.add_argument("--prompts", default="data/prompts/pilot_v0_1.jsonl")
    args = ap.parse_args()

    eval_dir = Path(args.eval_dir)
    per_case_path = eval_dir / "per_case.jsonl"
    agg_path = eval_dir / "aggregate.json"

    if not per_case_path.exists():
        print(f"ERROR: {per_case_path} not found")
        sys.exit(1)

    prompts = {c["id"]: c for c in load_jsonl(args.prompts)}
    results = load_jsonl(str(per_case_path))
    dims = detect_dims(str(per_case_path))
    print(f"Detected dims: {list(dims.keys())}")

    report = aggregate(results, prompts, dims)
    with agg_path.open("w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Re-aggregated {eval_dir} → {agg_path}")
    print(f"  mean_aggregate: {report['mean_aggregate']}")
    print(f"  per_difficulty: {report.get('per_difficulty', 'not available')}")


if __name__ == "__main__":
    main()
