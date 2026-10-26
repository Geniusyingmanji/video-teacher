"""Fail a pipeline stage when per-case outputs are incomplete or contain errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.pipeline_preflight import read_jsonl
from generation.runners.provenance import file_sha256


STANDARD_DIMS = {"conceptual_correctness", "narrative_structure", "visual_quality",
                 "pedagogical_clarity", "didactic_affordances", "audience_appropriateness"}


def check_artifacts(prompt_rows: list[dict], records: list[dict], kind: str) -> dict:
    expected = {row["id"] for row in prompt_rows}
    latest = {row["id"]: row for row in records if isinstance(row.get("id"), str)}
    missing = sorted(expected - set(latest))
    failed = []
    for case_id in sorted(expected & set(latest)):
        row = latest[case_id]
        if kind == "generation":
            video = Path(row.get("video_path", ""))
            bad = (row.get("status") != "ok" or not video.is_file() or
                   not row.get("video_sha256") or
                   (video.is_file() and file_sha256(video) != row.get("video_sha256")))
        elif kind == "standard":
            bad = ("error" in row or any(
                isinstance(value, dict) and "error" in value for value in row.values()) or
                not STANDARD_DIMS.issubset(row) or "aggregate_score" not in row)
        else:
            bad = ("error" in row or
                   not isinstance(row.get("pre"), dict) or "score" not in row["pre"] or
                   not isinstance(row.get("post_video"), dict) or
                   "score" not in row["post_video"] or
                   not isinstance(row.get("random_video"), dict) or
                   "score" not in row["random_video"])
        if bad:
            failed.append(case_id)
    return {"kind": kind, "expected": len(expected), "present": len(expected) - len(missing),
            "missing": missing, "failed": failed,
            "complete": bool(expected) and not missing and not failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--kind", choices=("generation", "standard", "teachquiz"), required=True)
    args = parser.parse_args()
    report = check_artifacts(read_jsonl(args.prompts), read_jsonl(args.manifest), args.kind)
    print(json.dumps(report, ensure_ascii=False))
    if not report["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
