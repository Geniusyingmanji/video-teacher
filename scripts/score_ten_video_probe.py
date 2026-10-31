"""Reproducible offline diagnostic trial for the ten controlled probe videos."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from eval.benchmark_operators import decode_video, signal_quality, temporal_consistency
from eval.run_benchmark_v2 import file_sha256, read_jsonl, unique_by_id

ROOT = Path(__file__).resolve().parents[1]
CASES = ("math_exp_01", "chem_prob_01", "bio_exp_02", "phys_prob_02", "hist_exp_01")
TREATMENTS = ("focused", "negative")


def run() -> dict:
    prompts = unique_by_id(read_jsonl(ROOT / "data/prompts/pilot_v0_1.jsonl"))
    rows = []
    for treatment in TREATMENTS:
        folder = ROOT / f"results/quality_probe_{treatment}_5"
        for case_id in CASES:
            path = folder / f"{case_id}.mp4"
            frames, fps = decode_video(str(path))
            gray = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
            changes = [float(np.mean(cv2.absdiff(a, b))) / 255
                       for a, b in zip(gray, gray[1:])]
            rows.append({
                "id": case_id, "treatment": treatment,
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(path), "duration_seconds": round(len(frames) / fps, 3),
                "frame_count": len(frames), "fps": fps,
                "mean_adjacent_change": round(float(np.mean(changes)), 6),
                "max_adjacent_change": round(max(changes), 6),
                "signal_operator": signal_quality(frames),
                "temporal_operator": temporal_consistency(
                    frames, fps, len(prompts[case_id].get("expected_narrative_order") or [])),
                "eight_axis_score": None,
                "status": "diagnostics_only_visual_judge_unavailable",
            })
    by_key = {(r["id"], r["treatment"]): r for r in rows}
    pairs = []
    for case_id in CASES:
        a, b = by_key[(case_id, "focused")], by_key[(case_id, "negative")]
        pairs.append({"id": case_id,
                      "focused_minus_negative_adjacent_change": round(
                          a["mean_adjacent_change"] - b["mean_adjacent_change"], 6),
                      "focused_minus_negative_temporal_operator": round(
                          a["temporal_operator"]["score"] - b["temporal_operator"]["score"], 4),
                      "focused_minus_negative_signal_operator": round(
                          a["signal_operator"]["score"] - b["signal_operator"]["score"], 4)})
    return {"protocol": "ten_video_offline_diagnostics_v1", "n": len(rows),
            "rows": rows, "pairs": pairs,
            "warning": "CV operators are diagnostic evidence, not the eight-axis benchmark score."}


if __name__ == "__main__":
    result = run()
    out = ROOT / "results/ten_video_benchmark_trial"
    out.mkdir(parents=True, exist_ok=True)
    (out / "diagnostics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts = unique_by_id(read_jsonl(ROOT / "data/prompts/pilot_v0_1.jsonl"))
    (out / "prompts_5.jsonl").write_text(
        "".join(json.dumps(prompts[case_id], ensure_ascii=False) + "\n" for case_id in CASES),
        encoding="utf-8")
    for treatment in TREATMENTS:
        items = [r for r in result["rows"] if r["treatment"] == treatment]
        (out / f"manifest_{treatment}.jsonl").write_text(
            "".join(json.dumps({"id": r["id"], "status": "ok",
                                "video_path": str((ROOT / r["path"]).resolve())},
                               ensure_ascii=False) + "\n" for r in items),
            encoding="utf-8")
    print(json.dumps({"n": result["n"], "pairs": result["pairs"], "out": str(out)},
                     ensure_ascii=False))
