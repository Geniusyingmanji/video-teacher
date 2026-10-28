"""Fail a pipeline stage when per-case outputs are incomplete or contain errors."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.pipeline_preflight import read_jsonl
from generation.runners.provenance import file_sha256


STANDARD_DIMS = {"conceptual_correctness", "narrative_structure", "visual_quality",
                 "pedagogical_clarity", "didactic_affordances", "audience_appropriateness"}


def finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_artifacts(prompt_rows: list[dict], records: list[dict], kind: str) -> dict:
    expected = {row["id"] for row in prompt_rows}
    latest = {row["id"]: row for row in records if isinstance(row.get("id"), str)}
    missing = sorted(expected - set(latest))
    unexpected = sorted(set(latest) - expected)
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
                not finite_number(row.get("aggregate_score")) or
                any(not isinstance(row.get(dim), dict) or
                    not finite_number(row[dim].get("score")) for dim in STANDARD_DIMS))
        else:
            bad = ("error" in row or
                   any(not isinstance(row.get(part), dict) or
                       not finite_number(row[part].get("score"))
                       for part in ("pre", "post_video", "random_video")) or
                   not finite_number(row.get("normalized_gain")))
        if bad:
            failed.append(case_id)
    return {"kind": kind, "expected": len(expected), "present": len(expected) - len(missing),
            "missing": missing, "unexpected": unexpected, "failed": failed,
            "complete": bool(expected) and not missing and not unexpected and not failed}


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
