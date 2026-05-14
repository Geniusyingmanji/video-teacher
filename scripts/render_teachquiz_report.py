"""Render TeachQuiz-T outputs to Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="TeachQuiz-T pilot report")
    args = ap.parse_args()

    eval_dir = Path(args.eval_dir)
    agg = json.loads((eval_dir / "aggregate.json").read_text(encoding="utf-8"))
    rows = load_jsonl(eval_dir / "per_case.jsonl")
    valid = [r for r in rows if "error" not in r and r.get("valid")]
    valid.sort(key=lambda r: r.get("learning_gain", 0), reverse=True)

    lines: list[str] = []
    A = lines.append
    A(f"# {args.title}")
    A("")
    A("## Headline")
    A("")
    A("| Metric | Value |")
    A("|---|---|")
    A(f"| N total | {agg['n_total']} |")
    A(f"| N scored | {agg['n_scored']} |")
    A(f"| N valid | {agg['n_valid']} |")
    overall = agg["overall"]
    A(f"| Pre/no-video score | {overall['pre_score']} |")
    A(f"| Post/generated-video score | {overall['post_video_score']} |")
    A(f"| Random-video score | {overall['random_video_score']} |")
    A(f"| Learning gain | {overall['learning_gain']} |")
    A(f"| Normalized gain | {overall['normalized_gain']} |")
    A(f"| Positive gain rate | {overall['positive_gain_rate']} |")

    A("")
    A("## Per Case")
    A("")
    A("| Case | Discipline | Task | Pre | Post | Random | Gain | Normalized |")
    A("|---|---|---|---|---|---|---|---|")
    for r in valid:
        rand = r["random_video"]["score"] if r.get("random_video") else "—"
        A(
            f"| {r['id']} | {r.get('discipline')} | {r.get('task_type')} | "
            f"{r['pre']['score']} | {r['post_video']['score']} | {rand} | "
            f"{r['learning_gain']} | {r['normalized_gain']} |"
        )

    errors = [r for r in rows if "error" in r]
    if errors:
        A("")
        A("## Errors")
        A("")
        for r in errors:
            A(f"- {r.get('id')}: {r.get('error')}")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
