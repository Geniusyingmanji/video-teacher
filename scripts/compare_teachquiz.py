"""Protocol-safe paired comparison of two TeachQuiz runs.

The script refuses comparisons unless both runs used the same frozen quiz,
learner, frame/scoring settings, and random-control policy. It reports the
paired case intersection, bootstrap confidence intervals, a paired sign-flip
permutation p-value, and filtered/unfiltered sensitivity results.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


COMPARABILITY_FIELDS = (
    "student", "quiz_sha256", "probe_origin", "random_control",
    "random_seed", "match_priority", "max_baseline_score", "n_frames",
    "frame_max_px", "max_questions",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_run(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    aggregate = json.loads((path / "aggregate.json").read_text(encoding="utf-8"))
    protocol = aggregate.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError(f"{path}: aggregate has no protocol metadata; legacy run is not comparable")
    rows = {row["id"]: row for row in load_jsonl(path / "per_case.jsonl") if "error" not in row}
    return protocol, rows


def validate_comparable(left: dict[str, Any], right: dict[str, Any]) -> None:
    if left.get("probe_origin") != "frozen_shared" or right.get("probe_origin") != "frozen_shared":
        raise ValueError("both runs must declare probe_origin=frozen_shared")
    if not left.get("cross_model_comparable") or not right.get("cross_model_comparable"):
        raise ValueError("both runs must declare cross_model_comparable=true")
    changed = [field for field in COMPARABILITY_FIELDS if left.get(field) != right.get(field)]
    if changed:
        raise ValueError("incomparable protocols differ in: " + ", ".join(changed))


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def paired_stats(diffs: list[float], seed: int, draws: int) -> dict[str, float | int | None]:
    if len(diffs) < 2:
        raise ValueError("paired comparison requires at least two shared cases")
    if draws < 1:
        raise ValueError("draws must be at least 1")
    rng = random.Random(seed)
    observed = mean(diffs)
    boots = sorted(mean([rng.choice(diffs) for _ in diffs]) for _ in range(draws))
    lo = boots[int(0.025 * draws)]
    hi = boots[min(draws - 1, int(0.975 * draws))]
    extreme = 0
    target = abs(observed)
    for _ in range(draws):
        permuted = mean([value if rng.random() < 0.5 else -value for value in diffs])
        extreme += abs(permuted) >= target - 1e-12
    sd = math.sqrt(sum((value - observed) ** 2 for value in diffs) / (len(diffs) - 1))
    return {
        "n": len(diffs), "mean_difference": observed,
        "ci95_low": lo, "ci95_high": hi,
        "permutation_p_two_sided": (extreme + 1) / (draws + 1),
        # A constant paired difference has zero sample variance, so its
        # standardized effect is undefined.  Use null rather than NaN to keep
        # the report valid JSON (main deliberately serializes with
        # allow_nan=False).
        "paired_standardized_effect": observed / sd if sd else None,
    }


def compare(left_rows: dict[str, dict[str, Any]], right_rows: dict[str, dict[str, Any]], *,
            valid_only: bool, metric: str, seed: int, draws: int) -> dict[str, Any]:
    shared = sorted(set(left_rows) & set(right_rows))
    if valid_only:
        shared = [case_id for case_id in shared if left_rows[case_id].get("valid") and right_rows[case_id].get("valid")]
    diffs = [float(left_rows[i][metric]) - float(right_rows[i][metric]) for i in shared]
    result = paired_stats(diffs, seed, draws)
    result["case_ids"] = shared
    result["valid_only"] = valid_only
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--left-label", default="left")
    parser.add_argument("--right-label", default="right")
    parser.add_argument("--metric", default="normalized_gain", choices=["normalized_gain", "learning_gain", "raw_gain", "control_adjusted_gain"])
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    left_protocol, left_rows = load_run(args.left)
    right_protocol, right_rows = load_run(args.right)
    validate_comparable(left_protocol, right_protocol)
    output = {
        "comparison": f"{args.left_label} - {args.right_label}",
        "metric": args.metric,
        "quiz_sha256": left_protocol["quiz_sha256"],
        "all_scored_intersection": compare(left_rows, right_rows, valid_only=False, metric=args.metric, seed=args.seed, draws=args.draws),
        "joint_valid_intersection": compare(left_rows, right_rows, valid_only=True, metric=args.metric, seed=args.seed + 1, draws=args.draws),
    }
    rendered = json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
