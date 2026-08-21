"""Paired uncertainty analysis for two standard-evaluation runs.

Comparisons use the shared case-id intersection.  The left-minus-right mean
difference is accompanied by a percentile case-bootstrap confidence interval,
a paired standardized effect (Cohen's dz), and a two-sided paired sign-flip
permutation p-value.  Missing dimensions are reported rather than imputed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path}:{line_number}: missing string id")
        if case_id in rows:
            raise ValueError(f"{path}:{line_number}: duplicate id {case_id!r}")
        if "error" not in row:
            rows[case_id] = row
    return rows


def score(row: dict[str, Any], metric: str) -> float | None:
    if metric == "aggregate_score":
        value = row.get(metric)
    else:
        payload = row.get(metric)
        value = payload.get("score") if isinstance(payload, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def paired_stats(differences: list[float], *, seed: int, draws: int) -> dict[str, float | int | None]:
    if len(differences) < 2:
        raise ValueError("paired comparison requires at least two scored shared cases")
    if draws < 1:
        raise ValueError("draws must be at least 1")
    observed = sum(differences) / len(differences)
    rng = random.Random(seed)
    boot = sorted(
        sum(rng.choice(differences) for _ in differences) / len(differences)
        for _ in range(draws)
    )
    low = boot[max(0, math.ceil(0.025 * draws) - 1)]
    high = boot[min(draws - 1, math.ceil(0.975 * draws) - 1)]
    target = abs(observed)
    extreme = 0
    for _ in range(draws):
        permuted = sum(value if rng.random() < 0.5 else -value for value in differences) / len(differences)
        extreme += abs(permuted) >= target - 1e-12
    variance = sum((value - observed) ** 2 for value in differences) / (len(differences) - 1)
    sd = math.sqrt(variance)
    return {
        "n": len(differences),
        "mean_difference": observed,
        "ci95_low": low,
        "ci95_high": high,
        "permutation_p_two_sided": (extreme + 1) / (draws + 1),
        "cohens_dz": observed / sd if sd else None,
    }


def compare_metric(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]], metric: str,
                   *, seed: int, draws: int) -> dict[str, Any] | None:
    case_ids: list[str] = []
    differences: list[float] = []
    for case_id in sorted(set(left) & set(right)):
        left_score, right_score = score(left[case_id], metric), score(right[case_id], metric)
        if left_score is not None and right_score is not None:
            case_ids.append(case_id)
            differences.append(left_score - right_score)
    if len(differences) < 2:
        return None
    result = paired_stats(differences, seed=seed, draws=draws)
    result["case_ids"] = case_ids
    return result


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return Holm family-wise adjusted p-values in original order."""
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def analyse(left_path: Path, right_path: Path, *, left_label: str, right_label: str,
            metrics: list[str], seed: int, draws: int) -> dict[str, Any]:
    left, right = load_rows(left_path), load_rows(right_path)
    results: dict[str, Any] = {}
    for index, metric in enumerate(metrics):
        result = compare_metric(left, right, metric, seed=seed + index, draws=draws)
        if result is not None:
            results[metric] = result
    raw_p = [result["permutation_p_two_sided"] for result in results.values()]
    for result, adjusted in zip(results.values(), holm_adjust(raw_p)):
        result["holm_adjusted_p"] = adjusted
    return {
        "comparison": f"{left_label} - {right_label}",
        "left": str(left_path),
        "right": str(right_path),
        "shared_case_ids": sorted(set(left) & set(right)),
        "draws": draws,
        "seed": seed,
        "metrics": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Standard-eval paired comparison: {report['comparison']}", "",
        "Positive differences favour the left configuration. Cases are paired by exact case ID.", "",
        f"Shared cases: {len(report['shared_case_ids'])}; bootstrap/permutation draws: {report['draws']}; seed: {report['seed']}.", "",
        "| Metric | N | Mean difference | 95% bootstrap CI | Cohen's dz | Permutation p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, value in report["metrics"].items():
        effect = "undefined" if value["cohens_dz"] is None else f"{value['cohens_dz']:.3f}"
        lines.append(
            f"| {metric} | {value['n']} | {value['mean_difference']:.4f} | "
            f"[{value['ci95_low']:.4f}, {value['ci95_high']:.4f}] | {effect} | "
            f"{value['permutation_p_two_sided']:.4f} | {value['holm_adjusted_p']:.4f} |"
        )
    lines += ["", "Cohen's dz is undefined when every paired difference is identical. Holm p-values control the family-wise error rate across the metrics in this table.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--left-label", default="left")
    parser.add_argument("--right-label", default="right")
    parser.add_argument("--metrics", nargs="+", default=[
        "aggregate_score", "conceptual_correctness", "narrative_structure", "visual_quality",
        "pedagogical_clarity", "didactic_affordances", "audience_appropriateness",
    ])
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260821)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = analyse(args.left, args.right, left_label=args.left_label, right_label=args.right_label,
                     metrics=args.metrics, seed=args.seed, draws=args.draws)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.suffix.lower() == ".json":
        rendered = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    else:
        rendered = render_markdown(report)
    args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
