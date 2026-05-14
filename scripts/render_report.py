"""Render eval results into a human-readable PILOT_REPORT.md."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_jsonl(p):
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_report(
    prompts_path: str, gen_manifest: str, eval_dir: str, out_md: str, model_label: str
) -> None:
    prompts = {c["id"]: c for c in load_jsonl(prompts_path)}
    gen = load_jsonl(gen_manifest)
    per_case = load_jsonl(Path(eval_dir) / "per_case.jsonl")
    agg = json.loads(Path(Path(eval_dir) / "aggregate.json").read_text())

    # Generation stats
    n_total = len(prompts)
    n_gen_ok = sum(1 for r in gen if r.get("status") == "ok")
    n_gen_err = sum(1 for r in gen if r.get("status") != "ok")
    times = [r["elapsed_s"] for r in gen if r.get("status") == "ok"]
    mean_t = round(sum(times) / max(1, len(times)), 1) if times else 0

    lines: list[str] = []
    A = lines.append
    A(f"# rise-teacher pilot report\n")
    A(f"_v0.1 — {model_label}_\n")
    A(f"## Run summary\n")
    A(f"- prompts: **{n_total}** (12 disciplines × 5 cases)")
    A(f"- generation: {n_gen_ok} ok / {n_gen_err} failed")
    A(f"- mean generation wallclock: **{mean_t}s / video**")
    A(f"- evaluated: **{agg['n_total']}** videos × {len(agg['per_dim_mean'])} dims via GPT-5.5 keyless\n")
    A(f"## Headline scores (1..5, higher better)\n")
    A(f"| Dimension | Mean |")
    A(f"|---|---|")
    for d, m in agg["per_dim_mean"].items():
        A(f"| {d} | {m} |")
    A(f"| **Aggregate (weighted)** | **{agg['mean_aggregate']}** |")
    A(f"| **Strict accuracy** | **{agg['strict_accuracy']*100:.1f}%** |\n")
    A(f"## Per discipline\n")
    A(f"| Discipline | N | Mean | Strict acc |")
    A(f"|---|---|---|---|")
    for d, v in sorted(agg["per_discipline"].items(), key=lambda kv: -kv[1]["mean"]):
        A(f"| {d} | {v['n']} | {v['mean']} | {v['strict_acc']*100:.1f}% |")
    if agg.get("per_difficulty"):
        A(f"\n## Per difficulty\n")
        A(f"| Difficulty | N | Mean | Strict acc |")
        A(f"|---|---|---|---|")
        for d, v in sorted(agg["per_difficulty"].items()):
            A(f"| {d} | {v['n']} | {v['mean']} | {v['strict_acc']*100:.1f}% |")

    A(f"\n## Per task type\n")
    A(f"| Task | N | Mean | Strict acc |")
    A(f"|---|---|---|---|")
    for d, v in agg["per_task_type"].items():
        A(f"| {d} | {v['n']} | {v['mean']} | {v['strict_acc']*100:.1f}% |")
    A("")

    # Top / bottom 5 by aggregate
    valid = [r for r in per_case if "aggregate_score" in r]
    valid.sort(key=lambda r: r["aggregate_score"], reverse=True)
    A(f"## Top 5 cases by aggregate\n")
    for r in valid[:5]:
        c = prompts.get(r["id"], {})
        A(f"- **{r['id']}** ({c.get('discipline','?')} / {c.get('task_type','?')}) — agg **{r['aggregate_score']}**, strict {r.get('strict_pass')}")
    A(f"\n## Bottom 5 cases by aggregate\n")
    for r in valid[-5:]:
        c = prompts.get(r["id"], {})
        A(f"- **{r['id']}** ({c.get('discipline','?')} / {c.get('task_type','?')}) — agg **{r['aggregate_score']}**, strict {r.get('strict_pass')}")
    A("")

    # Failure mode counter on conceptual_correctness rubric checks
    rubric_fail = Counter()
    for r in valid:
        cc = r.get("conceptual_correctness", {})
        for chk in cc.get("rubric_results") or []:
            if chk.get("verdict") == "FAIL":
                rubric_fail[chk.get("check", "<unnamed>")] += 1
    if rubric_fail:
        A(f"## Most-failed rubric checks (conceptual_correctness)\n")
        for k, v in rubric_fail.most_common(10):
            A(f"- ({v}× fail) {k[:120]}")
        A("")

    A(f"## Notes\n")
    A(f"- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.")
    A(f"- Dimension subset for this pilot: {', '.join(agg['per_dim_mean'].keys())}.")
    A(f"- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.")
    A(f"- Source files: prompts at `{prompts_path}`, manifest at `{gen_manifest}`, eval at `{eval_dir}`.")

    Path(out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_md}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-label", default="Wan2.2-TI2V-5B")
    args = ap.parse_args()
    write_report(args.prompts, args.manifest, args.eval_dir, args.out, args.model_label)


if __name__ == "__main__":
    main()
