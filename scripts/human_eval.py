"""Prepare and analyse a blinded human validation study for rise-teacher.

The study deliberately keeps the model judge score out of the rater packet.
It exports deterministic, stratified assignments, accepts one JSON object per
rating, and reports ordinal inter-rater reliability plus judge--human
agreement with non-parametric bootstrap confidence intervals.

Examples
--------
python scripts/human_eval.py export --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest /data/.../manifest.jsonl --judge /data/.../per_case.jsonl \
  --out data/human_eval/session_01 --n-cases 60 --raters 3 --seed 20260806
python scripts/human_eval.py analyse --assignments data/human_eval/session_01/assignments.jsonl \
  --responses data/human_eval/session_01/responses.jsonl --judge /data/.../per_case.jsonl \
  --out docs/analysis/human_validation.md
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

DIMENSIONS = (
    "conceptual_correctness", "narrative_structure", "visual_quality",
    "pedagogical_clarity", "didactic_affordances", "audience_appropriateness",
)
SCALE = (1, 2, 3, 4, 5)
RUBRICS = {
    "conceptual_correctness": "Factual correctness and faithful depiction of the required concepts.",
    "narrative_structure": "A teachable, correctly ordered progression through the required steps.",
    "visual_quality": "Legibility, visual coherence, and absence of distracting artifacts.",
    "pedagogical_clarity": "Clear chunking, emphasis, signposting, and readable presentation.",
    "didactic_affordances": "Useful labels, diagrams, arrows, formulas, and other teaching aids.",
    "audience_appropriateness": "Vocabulary, depth, pacing, and assumptions fit the stated audience.",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_no}: each row must be an object")
                rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def score(record: dict[str, Any], dimension: str) -> float | None:
    value = record.get(dimension)
    if isinstance(value, dict):
        value = value.get("score", value.get("final_score"))
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def stratified_sample(cases: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    """Select as evenly as possible over discipline × task type × difficulty."""
    if n > len(cases):
        raise ValueError(f"requested {n} cases, but only {len(cases)} are usable")
    rng = random.Random(seed)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        groups[(str(case.get("discipline", "unknown")), str(case.get("task_type", "unknown")),
                str(case.get("difficulty", "unknown")))].append(case)
    for group in groups.values():
        rng.shuffle(group)
    keys = sorted(groups)
    selected: list[dict[str, Any]] = []
    # Round-robin makes every non-empty stratum represented before oversampling.
    while len(selected) < n and any(groups.values()):
        progressed = False
        for key in keys:
            if groups[key] and len(selected) < n:
                selected.append(groups[key].pop())
                progressed = True
        if not progressed:
            break
    return selected


def export(args: argparse.Namespace) -> None:
    prompts = {r["id"]: r for r in read_jsonl(Path(args.prompts))}
    manifests = {r["id"]: r for r in read_jsonl(Path(args.manifest)) if r.get("status", "ok") == "ok"}
    judges = {r["id"]: r for r in read_jsonl(Path(args.judge))}
    usable = []
    for cid, case in prompts.items():
        if cid not in manifests or cid not in judges:
            continue
        available = [d for d in DIMENSIONS if score(judges[cid], d) is not None]
        if not available:
            continue
        usable.append({**case, "_video_path": manifests[cid].get("video_path"), "_dimensions": available})
    sampled = stratified_sample(usable, args.n_cases, args.seed)
    if args.raters < 2:
        raise ValueError("--raters must be at least 2 for reliability estimation")
    rows = []
    rng = random.Random(args.seed + 1)
    for rater_idx in range(1, args.raters + 1):
        order = list(sampled)
        rng.shuffle(order)
        for position, case in enumerate(order, 1):
            rows.append({
                "schema_version": 1, "assignment_id": f"s{args.seed}-r{rater_idx}-{position:03d}",
                "rater_id": f"rater_{rater_idx:02d}", "position": position, "case_id": case["id"],
                "video_path": case["_video_path"], "discipline": case.get("discipline"),
                "task_type": case.get("task_type"), "difficulty": case.get("difficulty"),
                "target_audience": case.get("pedagogical_target_audience"),
                "prompt_text": case.get("prompt_text"), "expected_concepts": case.get("expected_concepts", []),
                "expected_narrative_order": case.get("expected_narrative_order", []),
                "dimensions": case["_dimensions"], "rubrics": {d: RUBRICS[d] for d in case["_dimensions"]},
            })
    out = Path(args.out)
    write_jsonl(out / "assignments.jsonl", rows)
    rater_files = []
    for rater_idx in range(1, args.raters + 1):
        rater_id = f"rater_{rater_idx:02d}"
        relative_path = Path("raters") / f"{rater_id}.jsonl"
        write_jsonl(out / relative_path, (row for row in rows if row["rater_id"] == rater_id))
        rater_files.append(relative_path.as_posix())
    (out / "study_manifest.json").write_text(json.dumps({
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "seed": args.seed,
        "n_cases": len(sampled), "n_raters": args.raters, "n_assignments": len(rows),
        "rater_assignment_files": rater_files,
        "dimensions": list(DIMENSIONS), "blinding": "Model identity and automated scores are omitted from assignments.",
    }, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {len(rows)} blinded assignments ({len(sampled)} cases × {args.raters} raters) "
        f"and {len(rater_files)} rater packets to {out}"
    )


def rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        average_rank = (i + 1 + j) / 2
        for index, _ in ordered[i:j]:
            result[index] = average_rank
        i = j
    return result


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    denom = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom else float("nan")


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(rank(xs), rank(ys))


def bootstrap_spearman(xs: list[float], ys: list[float], seed: int, draws: int = 5000) -> tuple[float, float, float]:
    if len(xs) != len(ys):
        raise ValueError("bootstrap inputs must have the same length")
    if draws < 1:
        raise ValueError("bootstrap draws must be positive")
    point = spearman(xs, ys)
    if len(xs) < 4:
        return point, float("nan"), float("nan")
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        indices = [rng.randrange(len(xs)) for _ in xs]
        value = spearman([xs[i] for i in indices], [ys[i] for i in indices])
        if math.isfinite(value):
            values.append(value)
    if not values:
        return point, float("nan"), float("nan")
    values.sort()
    lo_index = max(0, math.ceil(.025 * len(values)) - 1)
    hi_index = min(len(values) - 1, math.ceil(.975 * len(values)) - 1)
    return point, values[lo_index], values[hi_index]


def krippendorff_alpha_ordinal(matrix: list[list[float | None]]) -> float:
    """Krippendorff alpha for ordinal 1--5 ratings; handles missing values."""
    units = [[value for value in row if value is not None] for row in matrix]
    units = [row for row in units if len(row) >= 2]
    values = [value for row in units for value in row]
    if len(units) < 2 or len(set(values)) < 2:
        return float("nan")
    counts = Counter(values)
    n = len(values)
    # Ordinal distance based on cumulative category counts (Krippendorff 2018).
    categories = sorted(counts)
    cumulative = {c: sum(counts[x] for x in categories if x <= c) for c in categories}
    def delta(a: float, b: float) -> float:
        lo, hi = sorted((a, b))
        return (sum(counts[c] for c in categories if lo <= c <= hi) - (counts[lo] + counts[hi]) / 2) ** 2
    observed_num = sum(sum(delta(a, b) for a in row for b in row if a != b) / (len(row) - 1) for row in units)
    observed = observed_num / len(values)
    expected = sum(counts[a] * counts[b] * delta(a, b) for a in categories for b in categories if a != b) / (n * (n - 1))
    return 1 - observed / expected if expected else float("nan")


def fmt(value: float) -> str:
    return "NA" if not math.isfinite(value) else f"{value:.3f}"


def json_number(value: float) -> float | None:
    """Return a strict-JSON representation for a possibly non-finite statistic."""
    return value if math.isfinite(value) else None


def analyse(args: argparse.Namespace) -> None:
    assignments = {r["assignment_id"]: r for r in read_jsonl(Path(args.assignments))}
    responses = read_jsonl(Path(args.responses))
    judges = {r["id"]: r for r in read_jsonl(Path(args.judge))}
    scores_by_dim: dict[str, dict[str, list[float]]] = {d: defaultdict(list) for d in DIMENSIONS}
    rejected: list[str] = []
    seen: set[tuple[str, str]] = set()
    for response in responses:
        aid = response.get("assignment_id")
        assignment = assignments.get(aid)
        if not assignment:
            rejected.append(f"unknown assignment_id: {aid}"); continue
        key = (str(aid), str(response.get("rater_id")))
        if response.get("rater_id") != assignment["rater_id"] or key in seen:
            rejected.append(f"invalid or duplicate response: {aid}"); continue
        seen.add(key)
        for dim in assignment["dimensions"]:
            value = response.get("scores", {}).get(dim)
            if isinstance(value, bool) or not isinstance(value, int) or value not in SCALE:
                rejected.append(f"{aid}: {dim} must be integer 1..5"); continue
            scores_by_dim[dim][assignment["case_id"]].append(float(value))
    lines = ["# Human Validation of Automated Evaluation\n", "This report was generated from blinded ordinal ratings. Model identities and GPT scores were excluded from rater assignments.\n"]
    lines += [f"- Assignments: {len(assignments)}; accepted response records: {len(seen)}; rejected fields/records: {len(rejected)}.", "- Reliability: Krippendorff's ordinal alpha across raters on the same video.", "- Validity: Spearman correlation between the per-video mean human rating and the automated judge, with a case-bootstrap 95% CI.\n", "| Dimension | Videos rated | Mean ratings/video | Ordinal alpha | Judge-human rho [95% CI] |", "|---|---:|---:|---:|---:|"]
    machine_readable: dict[str, Any] = {"n_assignments": len(assignments), "n_accepted": len(seen), "rejected": rejected, "dimensions": {}}
    for dim_index, dim in enumerate(DIMENSIONS):
        per_case = scores_by_dim[dim]
        ids = sorted(cid for cid, values in per_case.items() if cid in judges and score(judges[cid], dim) is not None)
        matrix = [per_case[cid] for cid in ids]
        human = [mean(per_case[cid]) for cid in ids]
        automated = [score(judges[cid], dim) for cid in ids]
        alpha = krippendorff_alpha_ordinal(matrix)
        rho, lo, hi = bootstrap_spearman(automated, human, args.seed + dim_index)
        mean_ratings = mean([len(v) for v in matrix]) if matrix else float("nan")
        lines.append(f"| {dim} | {len(ids)} | {fmt(mean_ratings)} | {fmt(alpha)} | {fmt(rho)} [{fmt(lo)}, {fmt(hi)}] |")
        machine_readable["dimensions"][dim] = {
            "n_videos": len(ids),
            "mean_ratings_per_video": json_number(mean_ratings),
            "ordinal_alpha": json_number(alpha),
            "spearman_rho": json_number(rho),
            "ci95": [json_number(lo), json_number(hi)],
        }
    if rejected:
        lines += ["\n## Data-quality exclusions\n", *[f"- {item}" for item in rejected]]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(
        json.dumps(machine_readable, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out} and {Path(args.out).with_suffix('.json')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    exp = sub.add_parser("export", help="create blinded, stratified rater assignments")
    exp.add_argument("--prompts", required=True); exp.add_argument("--manifest", required=True); exp.add_argument("--judge", required=True)
    exp.add_argument("--out", required=True); exp.add_argument("--n-cases", type=int, default=60); exp.add_argument("--raters", type=int, default=3); exp.add_argument("--seed", type=int, default=20260806); exp.set_defaults(func=export)
    ana = sub.add_parser("analyse", help="validate ratings and calculate reliability/agreement")
    ana.add_argument("--assignments", required=True); ana.add_argument("--responses", required=True); ana.add_argument("--judge", required=True); ana.add_argument("--out", required=True); ana.add_argument("--seed", type=int, default=20260806); ana.set_defaults(func=analyse)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
