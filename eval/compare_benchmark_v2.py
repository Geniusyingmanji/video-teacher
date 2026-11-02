"""Paired model comparison for complete benchmark 2x8-v4 results."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from eval.benchmark_scoring import VERSION
from eval.run_benchmark_v2 import bootstrap_ci, read_jsonl


def compare(left: list[dict], right: list[dict], *, iterations: int = 10000,
            seed: int = 20261031) -> dict:
    def index(rows):
        out = {}
        for row in rows:
            if row["id"] in out:
                raise ValueError(f"duplicate case: {row['id']}")
            if row.get("version") != VERSION:
                raise ValueError("incompatible scoring version")
            if row.get("scoring", {}).get("valid") is not True:
                raise ValueError(f"invalid/incomplete case: {row['id']}")
            out[row["id"]] = row
        return out
    a, b = index(left), index(right)
    if not a or set(a) != set(b):
        raise ValueError("paired comparison requires identical nonempty case IDs")
    ids = sorted(a)
    for i in ids:
        if (not a[i].get("case_sha256") or a[i]["case_sha256"] != b[i].get("case_sha256")
                or not a[i].get("evaluation_config")
                or a[i]["evaluation_config"] != b[i].get("evaluation_config")):
            raise ValueError(f"case definition or evaluation configuration differs: {i}")
    diffs = [a[i]["scoring"]["score"] - b[i]["scoring"]["score"] for i in ids]
    observed = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    # Two-sided paired sign-flip randomisation under exchangeability of labels.
    extreme = sum(abs(sum(d * rng.choice((-1, 1)) for d in diffs) / len(diffs))
                  >= abs(observed) - 1e-12 for _ in range(iterations))
    return {"version": VERSION, "n_pairs": len(ids), "mean_left_minus_right": round(observed, 4),
            "paired_bootstrap_95_ci": bootstrap_ci(diffs, seed=seed, iterations=iterations),
            "sign_flip_p_two_sided": round((extreme + 1) / (iterations + 1), 6),
            "iterations": iterations, "seed": seed,
            "per_case_differences": dict(zip(ids, [round(x, 4) for x in diffs]))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, help="left per_case.jsonl")
    parser.add_argument("--right", required=True, help="right per_case.jsonl")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = compare(read_jsonl(args.left), read_jsonl(args.right))
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
