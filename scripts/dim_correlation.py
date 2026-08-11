"""Compute dimension-vs-dimension Pearson correlation on a pilot eval run.

Used to argue (or refute) that our dims carry independent signal — important
for the rise-teacher paper's eval design defense.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def load_jsonl(p):
    rows = []
    with open(p) as f:
        for l in f:
            l = l.strip()
            if l:
                rows.append(json.loads(l))
    return rows


def extract_dim_score(rec: dict, dim: str) -> float | None:
    if dim not in rec:
        return None
    sub = rec[dim]
    s = sub.get("score")
    if s is None:
        s = sub.get("final_score")
    if s is None:
        return None
    try:
        value = float(s)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-case", required=True)
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = load_jsonl(args.per_case)
    dims: list[str] = []
    for r in rows:
        for k in r:
            if isinstance(r[k], dict) and ("score" in r[k] or "final_score" in r[k]):
                if k not in dims and k not in {"error"}:
                    dims.append(k)
    print(f"detected dims: {dims}")

    # build NxK score matrix
    cols: dict[str, list[float]] = {d: [] for d in dims}
    keep_ids: list[str] = []
    for r in rows:
        if "aggregate_score" not in r:
            continue
        scores = {d: extract_dim_score(r, d) for d in dims}
        if any(v is None for v in scores.values()):
            continue
        keep_ids.append(r["id"])
        for d, v in scores.items():
            cols[d].append(v)
    print(f"using N={len(keep_ids)} cases with all dims present")

    M = np.array([cols[d] for d in dims])  # K x N
    if M.shape[1] < 3:
        print("not enough cases for correlation")
        return
    C = np.corrcoef(M)

    # render as markdown
    lines = [f"# {args.label} — dimension correlation (Pearson)", ""]
    header = "| dim | " + " | ".join(dims) + " |"
    sep = "|---|" + "|".join(["---"] * len(dims)) + "|"
    lines.append(header)
    lines.append(sep)
    for i, d in enumerate(dims):
        row = [d] + [f"{C[i, j]:+.2f}" for j in range(len(dims))]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"_N = {len(keep_ids)}_")
    md = "\n".join(lines)
    print()
    print(md)
    if args.out:
        Path(args.out).write_text(md)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
