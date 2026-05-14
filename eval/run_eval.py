"""End-to-end pilot evaluation runner.

Loads a generation manifest, samples frames from each video, scores 3 dims
via GPT-5.5 judge, writes per-case JSON + aggregate report.

Usage:
    python -m eval.run_eval \
        --prompts data/prompts/pilot_v0_1.jsonl \
        --manifest generation/outputs_data/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
        --out outputs/eval_pilot_v0_1 \
        --n-frames 8 --frame-max-px 384
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import time
import traceback
from pathlib import Path

from eval.frame_extractor import extract_frames
from eval.dimensions import (
    conceptual_correctness,
    narrative_structure,
    visual_quality,
    pedagogical_clarity,
    didactic_affordances,
    audience_appropriateness,
)


# Three "core" dims always run; the "extended" pedagogy dims toggled by --extended.
CORE_DIMS = {
    "conceptual_correctness": conceptual_correctness,
    "narrative_structure": narrative_structure,
    "visual_quality": visual_quality,
}
EXTENDED_DIMS = {
    "pedagogical_clarity": pedagogical_clarity,
    "didactic_affordances": didactic_affordances,
    "audience_appropriateness": audience_appropriateness,
}
ALL_DIMS = {**CORE_DIMS, **EXTENDED_DIMS}

# Weights — subset of plan §4.2 (re-normalised for whichever subset is used).
CORE_WEIGHTS = {
    "conceptual_correctness": 0.5,
    "narrative_structure": 0.3,
    "visual_quality": 0.2,
}
EXTENDED_WEIGHTS = {
    "conceptual_correctness": 0.28,
    "narrative_structure": 0.16,
    "pedagogical_clarity": 0.16,
    "didactic_affordances": 0.13,
    "audience_appropriateness": 0.12,
    "visual_quality": 0.15,
}


def load_jsonl(path: str) -> list[dict]:
    out: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def evaluate_one(
    case: dict, video_path: str, n_frames: int, frame_max_px: int,
    dims: dict, weights: dict,
) -> dict:
    """Returns dict of dim_name -> dim_output, plus aggregate score."""
    try:
        frames = extract_frames(video_path, n=n_frames, resize_max=frame_max_px)
    except Exception as e:
        return {"error": f"frame_extract_failed: {e}", "id": case["id"]}

    out: dict = {"id": case["id"]}
    weighted_sum = 0.0
    weight_sum = 0.0
    for dim_name, dim_mod in dims.items():
        try:
            r = dim_mod.score(case, frames)
            out[dim_name] = r
            s = r.get("score") or r.get("final_score") or 0
            try:
                s = float(s)
            except Exception:
                s = 0.0
            w = weights[dim_name]
            weighted_sum += s * w
            weight_sum += w
        except Exception as e:
            out[dim_name] = {"error": str(e)[:300], "score": 0}
    out["aggregate_score"] = (
        round(weighted_sum / weight_sum, 3) if weight_sum > 0 else 0
    )
    binaries = [out[d].get("binary", "FAIL") for d in dims if d in out]
    out["strict_pass"] = all(b == "PASS" for b in binaries)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--frame-max-px", type=int, default=384)
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--extended", action="store_true",
                    help="Include pedagogical_clarity and didactic_affordances dims.")
    args = ap.parse_args()
    dims = ALL_DIMS if args.extended else CORE_DIMS
    weights = EXTENDED_WEIGHTS if args.extended else CORE_WEIGHTS

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = {c["id"]: c for c in load_jsonl(args.prompts)}
    manifest = [m for m in load_jsonl(args.manifest) if m.get("status") == "ok"]
    if args.limit > 0:
        manifest = manifest[: args.limit]

    print(f"[eval] {len(manifest)} videos to evaluate")

    # Resume support — only skip cases with all dims successfully scored (no errors).
    per_case_path = out_dir / "per_case.jsonl"
    done_ids = set()
    if per_case_path.exists():
        with per_case_path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    cid = rec["id"]
                    # Skip if top-level error or any dim has an error key
                    if "error" in rec:
                        continue
                    if any("error" in rec.get(d, {}) for d in dims):
                        continue
                    done_ids.add(cid)
                except Exception:
                    pass
    # Rewrite per_case_path keeping only good records so re-run appends cleanly
    if per_case_path.exists() and done_ids:
        good_lines = []
        with per_case_path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec["id"] in done_ids:
                        good_lines.append(line if line.endswith("\n") else line + "\n")
                except Exception:
                    pass
        with per_case_path.open("w") as f:
            f.writelines(good_lines)
        print(f"[eval] resume: kept {len(done_ids)} clean records, pruned errors")

    tasks = [m for m in manifest if m["id"] not in done_ids]
    print(f"[eval] {len(tasks)} new (skipping {len(done_ids)} already-evaluated)")

    started = time.time()
    with per_case_path.open("a") as out_f:
        with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            future_to_case = {}
            for m in tasks:
                case = prompts.get(m["id"])
                if not case:
                    continue
                fut = ex.submit(
                    evaluate_one, case, m["video_path"], args.n_frames,
                    args.frame_max_px, dims, weights,
                )
                future_to_case[fut] = m["id"]
            for i, fut in enumerate(cf.as_completed(future_to_case)):
                cid = future_to_case[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"id": cid, "error": f"{type(e).__name__}: {e}",
                           "traceback": traceback.format_exc()[:600]}
                out_f.write(json.dumps(res, ensure_ascii=False) + "\n")
                out_f.flush()
                agg = res.get("aggregate_score", "?")
                strict = res.get("strict_pass", "?")
                wall = (time.time() - started) / 60.0
                print(f"[eval] [{i+1}/{len(tasks)}] {cid}: agg={agg} strict={strict} (wall {wall:.1f}m)")

    # Aggregate report
    all_results = load_jsonl(str(per_case_path))
    report = aggregate(all_results, prompts, dims)
    with (out_dir / "aggregate.json").open("w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[eval] done. report -> {out_dir/'aggregate.json'}")


def aggregate(results: list[dict], prompts: dict[str, dict], dims: dict) -> dict:
    rep: dict = {"n_total": len(results)}
    scores_by_dim: dict[str, list[float]] = {d: [] for d in dims}
    aggregates: list[float] = []
    strict_pass = 0
    per_discipline: dict[str, dict] = {}
    per_task_type: dict[str, dict] = {}
    per_difficulty: dict[str, dict] = {}

    for r in results:
        if "error" in r and "aggregate_score" not in r:
            continue
        aggregates.append(float(r.get("aggregate_score", 0) or 0))
        if r.get("strict_pass"):
            strict_pass += 1
        for dim in dims:
            if dim in r:
                s = r[dim].get("score") or r[dim].get("final_score") or 0
                try:
                    s = float(s)
                except Exception:
                    s = 0.0
                scores_by_dim[dim].append(s)
        case = prompts.get(r["id"], {})
        d = case.get("discipline", "unknown")
        t = case.get("task_type", "unknown")
        diff = case.get("difficulty", "unknown")
        per_discipline.setdefault(d, {"n": 0, "sum": 0.0, "pass": 0})
        per_discipline[d]["n"] += 1
        per_discipline[d]["sum"] += float(r.get("aggregate_score", 0) or 0)
        per_discipline[d]["pass"] += int(bool(r.get("strict_pass")))
        per_task_type.setdefault(t, {"n": 0, "sum": 0.0, "pass": 0})
        per_task_type[t]["n"] += 1
        per_task_type[t]["sum"] += float(r.get("aggregate_score", 0) or 0)
        per_task_type[t]["pass"] += int(bool(r.get("strict_pass")))
        per_difficulty.setdefault(diff, {"n": 0, "sum": 0.0, "pass": 0})
        per_difficulty[diff]["n"] += 1
        per_difficulty[diff]["sum"] += float(r.get("aggregate_score", 0) or 0)
        per_difficulty[diff]["pass"] += int(bool(r.get("strict_pass")))

    rep["mean_aggregate"] = round(sum(aggregates) / max(1, len(aggregates)), 3)
    rep["strict_accuracy"] = round(strict_pass / max(1, len(aggregates)), 3)
    rep["per_dim_mean"] = {d: round(sum(v) / max(1, len(v)), 3) for d, v in scores_by_dim.items()}
    rep["per_discipline"] = {
        d: {
            "n": v["n"],
            "mean": round(v["sum"] / max(1, v["n"]), 3),
            "strict_acc": round(v["pass"] / max(1, v["n"]), 3),
        }
        for d, v in per_discipline.items()
    }
    rep["per_task_type"] = {
        d: {
            "n": v["n"],
            "mean": round(v["sum"] / max(1, v["n"]), 3),
            "strict_acc": round(v["pass"] / max(1, v["n"]), 3),
        }
        for d, v in per_task_type.items()
    }
    rep["per_difficulty"] = {
        d: {
            "n": v["n"],
            "mean": round(v["sum"] / max(1, v["n"]), 3),
            "strict_acc": round(v["pass"] / max(1, v["n"]), 3),
        }
        for d, v in per_difficulty.items()
    }
    return rep


if __name__ == "__main__":
    main()
