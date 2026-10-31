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
import math
import time
import traceback
from pathlib import Path

from PIL import Image

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


def dimension_score(result: dict) -> float | None:
    """Extract a finite dimension score without treating a valid zero as missing."""
    value = result.get("score")
    if value is None:
        value = result.get("final_score")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def load_jsonl(path: str) -> list[dict]:
    out: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def latest_successful_manifest(records: list[dict]) -> list[dict]:
    """Use the latest attempt per case, including failures that supersede old clips."""
    latest: dict[str, dict] = {}
    for record in records:
        if record.get("id"):
            latest[record["id"]] = record
    return [record for record in latest.values() if record.get("status") == "ok"]


def evaluate_one(
    case: dict, video_path: str, n_frames: int, frame_max_px: int,
    dims: dict, weights: dict,
    detail_frame_max_px: int = 0,
    rubric_version: str = "legacy",
) -> dict:
    """Returns dict of dim_name -> dim_output, plus aggregate score."""
    try:
        needs_detail = detail_frame_max_px > frame_max_px and any(
            name in dims for name in ("pedagogical_clarity", "didactic_affordances")
        )
        detail_frames = extract_frames(
            video_path, n=n_frames,
            resize_max=detail_frame_max_px if needs_detail else frame_max_px,
        )
        if needs_detail:
            frames = [
                image.resize(
                    (max(1, round(image.width * frame_max_px / max(image.size))),
                     max(1, round(image.height * frame_max_px / max(image.size)))),
                    Image.Resampling.LANCZOS,
                ) if max(image.size) > frame_max_px else image
                for image in detail_frames
            ]
        else:
            frames = detail_frames
    except Exception as e:
        return {"error": f"frame_extract_failed: {e}", "id": case["id"]}

    out: dict = {
        "id": case["id"],
        "evaluation_config": {
            "n_frames": n_frames,
            "frame_max_px": frame_max_px,
            "detail_frame_max_px": detail_frame_max_px,
            "dimensions": list(dims),
        },
    }
    if rubric_version != "legacy":
        out["evaluation_config"]["rubric_version"] = rubric_version
    weighted_sum = 0.0
    weight_sum = 0.0
    for dim_name, dim_mod in dims.items():
        try:
            review_frames = detail_frames if needs_detail and dim_name in (
                "pedagogical_clarity", "didactic_affordances"
            ) else frames
            r = dim_mod.score(case, review_frames)
            out[dim_name] = r
            s = dimension_score(r)
            if s is None:
                raise ValueError(f"{dim_name} returned no finite score")
            w = weights[dim_name]
            weighted_sum += s * w
            weight_sum += w
        except Exception as e:
            out[dim_name] = {"error": str(e)[:300]}
    out["aggregate_score"] = (
        round(weighted_sum / weight_sum, 3) if weight_sum > 0 else None
    )
    if weight_sum == 0:
        out["error"] = "all_dimensions_failed"
    binaries = [out[d].get("binary", "FAIL") for d in dims if d in out]
    out["strict_pass"] = all(b == "PASS" for b in binaries)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--frame-max-px", type=int, default=832,
                    help="Source frame resolution for new evaluations; use 384 to reproduce old runs")
    ap.add_argument("--detail-frame-max-px", type=int, default=832,
                    help="Resolution for clarity/layout judges in --extended mode")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--extended", action="store_true",
                    help="Include pedagogical_clarity and didactic_affordances dims.")
    ap.add_argument("--rubric-6x6", action="store_true",
                    help="Score 36 evidence-backed criteria across all six teaching dimensions")
    args = ap.parse_args()
    if args.frame_max_px <= 0 or args.detail_frame_max_px <= 0:
        ap.error("frame resolution limits must be positive")
    if args.rubric_6x6:
        from eval.rubric_6x6 import DIMENSIONS
        dims = DIMENSIONS
        weights = EXTENDED_WEIGHTS
    else:
        dims = ALL_DIMS if args.extended else CORE_DIMS
        weights = EXTENDED_WEIGHTS if args.extended else CORE_WEIGHTS
    evaluation_config = {
        "n_frames": args.n_frames,
        "frame_max_px": args.frame_max_px,
        "detail_frame_max_px": args.detail_frame_max_px,
        "dimensions": list(dims),
    }
    if args.rubric_6x6:
        evaluation_config["rubric_version"] = "6x6-v1"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = {c["id"]: c for c in load_jsonl(args.prompts)}
    manifest = latest_successful_manifest(load_jsonl(args.manifest))
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
                    if "error" in rec or rec.get("evaluation_config") != evaluation_config:
                        continue
                    if any("error" in rec.get(d, {}) for d in dims):
                        continue
                    done_ids.add(cid)
                except Exception:
                    pass
    # Rewrite per_case_path keeping only good records so re-run appends cleanly
    if per_case_path.exists():
        good_records = {}
        with per_case_path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec["id"] in done_ids:
                        good_records[rec["id"]] = rec
                except Exception:
                    pass
        with per_case_path.open("w") as f:
            for rec in good_records.values():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[eval] resume: kept {len(good_records)} unique clean records, pruned errors/duplicates")

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
                    args.frame_max_px, dims, weights, args.detail_frame_max_px,
                    evaluation_config.get("rubric_version", "legacy"),
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
    scores_by_criterion: dict[str, dict[str, list[float]]] = {}
    aggregates: list[float] = []
    strict_pass = 0
    per_discipline: dict[str, dict] = {}
    per_task_type: dict[str, dict] = {}
    per_difficulty: dict[str, dict] = {}

    for r in results:
        if "error" in r and "aggregate_score" not in r:
            continue
        dim_scores = {}
        for dim in dims:
            dim_result = r.get(dim)
            if not isinstance(dim_result, dict) or "error" in dim_result:
                break
            value = dimension_score(dim_result)
            if value is None:
                break
            dim_scores[dim] = value
        if len(dim_scores) != len(dims):
            continue
        aggregates.append(float(r.get("aggregate_score", 0) or 0))
        if r.get("strict_pass"):
            strict_pass += 1
        for dim, value in dim_scores.items():
            scores_by_dim[dim].append(value)
            rows = r[dim].get("criteria", [])
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict) and row.get("applicable") is True:
                    scores_by_criterion.setdefault(dim, {}).setdefault(
                        str(row.get("id")), []).append(float(row["score"]))
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

    rep["n_valid"] = len(aggregates)
    rep["n_failed"] = len(results) - len(aggregates)
    rep["mean_aggregate"] = round(sum(aggregates) / max(1, len(aggregates)), 3)
    rep["strict_accuracy"] = round(strict_pass / max(1, len(aggregates)), 3)
    rep["per_dim_mean"] = {d: round(sum(v) / max(1, len(v)), 3) for d, v in scores_by_dim.items()}
    if scores_by_criterion:
        rep["per_criterion"] = {
            dim: {key: {"n": len(values), "mean": round(sum(values) / len(values), 3),
                        "low_1_or_2": sum(score <= 2 for score in values)}
                  for key, values in criteria.items()}
            for dim, criteria in scores_by_criterion.items()
        }
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
