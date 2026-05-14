"""Compare multiple model eval runs into a single Markdown table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_agg(eval_dir: str) -> dict:
    return json.loads((Path(eval_dir) / "aggregate.json").read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True,
                    help="Pairs of LABEL=PATH e.g. Wan5B=/data/.../eval_pilot_v0_1")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs: list[tuple[str, dict]] = []
    for spec in args.runs:
        label, path = spec.split("=", 1)
        runs.append((label, load_agg(path)))

    lines: list[str] = []
    A = lines.append
    A(f"# rise-teacher model comparison\n")
    A(f"## Headline\n")
    A(f"| Metric | " + " | ".join(label for label, _ in runs) + " |")
    A(f"|---|" + "|".join(["---"] * len(runs)) + "|")
    A(f"| N videos eval | " + " | ".join(str(a["n_total"]) for _, a in runs) + " |")
    A(f"| Mean aggregate (1-5) | " + " | ".join(str(a["mean_aggregate"]) for _, a in runs) + " |")
    A(f"| Strict accuracy (%) | " + " | ".join(f"{a['strict_accuracy']*100:.1f}" for _, a in runs) + " |")

    A(f"\n## Per dimension\n")
    all_dims: list[str] = sorted({d for _, a in runs for d in a["per_dim_mean"]})
    A(f"| Dimension | " + " | ".join(label for label, _ in runs) + " |")
    A(f"|---|" + "|".join(["---"] * len(runs)) + "|")
    for d in all_dims:
        cells = [str(a["per_dim_mean"].get(d, "—")) for _, a in runs]
        A(f"| {d} | " + " | ".join(cells) + " |")

    A(f"\n## Per discipline (mean aggregate)\n")
    all_disc: list[str] = sorted({d for _, a in runs for d in a["per_discipline"]})
    A(f"| Discipline | " + " | ".join(label for label, _ in runs) + " |")
    A(f"|---|" + "|".join(["---"] * len(runs)) + "|")
    for d in all_disc:
        cells: list[str] = []
        for _, a in runs:
            entry = a["per_discipline"].get(d)
            cells.append(str(entry["mean"]) if entry else "—")
        A(f"| {d} | " + " | ".join(cells) + " |")

    A(f"\n## Per task type (mean aggregate)\n")
    all_tt: list[str] = sorted({d for _, a in runs for d in a["per_task_type"]})
    A(f"| Task | " + " | ".join(label for label, _ in runs) + " |")
    A(f"|---|" + "|".join(["---"] * len(runs)) + "|")
    for d in all_tt:
        cells = []
        for _, a in runs:
            entry = a["per_task_type"].get(d)
            cells.append(str(entry["mean"]) if entry else "—")
        A(f"| {d} | " + " | ".join(cells) + " |")

    # Per difficulty (only if any run has it)
    if any("per_difficulty" in a for _, a in runs):
        A(f"\n## Per difficulty (mean aggregate)\n")
        all_diff: list[str] = sorted({d for _, a in runs for d in a.get("per_difficulty", {})})
        A(f"| Difficulty | " + " | ".join(label for label, _ in runs) + " |")
        A(f"|---|" + "|".join(["---"] * len(runs)) + "|")
        for d in all_diff:
            cells = []
            for _, a in runs:
                entry = a.get("per_difficulty", {}).get(d)
                cells.append(str(entry["mean"]) if entry else "—")
            A(f"| {d} | " + " | ".join(cells) + " |")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
