"""Reproducible per-item assistant preflight for the balanced research candidates."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data/prompts/candidate_400_balanced_draft.jsonl"
LEDGER = ROOT / "data/curated/candidate_400_self_review.jsonl"
SUMMARY = ROOT / "data/curated/candidate_400_self_review_summary.json"


def review() -> dict:
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    ids = Counter(row["id"] for row in rows)
    counts = defaultdict(Counter)
    records = []
    for row in rows:
        issues = []
        case_id = row["id"]
        prompt = row.get("prompt_text", "")
        if ids[case_id] != 1:
            issues.append("duplicate_id")
        if not prompt or len(prompt) > 500 or "\ufffd" in prompt or "<image>" in prompt:
            issues.append("prompt_invalid")
        if row.get("task_type") not in {"explanation", "problem_solving"}:
            issues.append("invalid_task_type")
        if row.get("video_goal") != ("knowledge_point" if row.get("task_type") == "explanation" else "solve_problem"):
            issues.append("task_goal_mismatch")
        if not row.get("expected_concepts") or not row.get("discipline_specific_rubric"):
            issues.append("missing_answer_or_rubric")
        order, beats = row.get("expected_narrative_order", []), row.get("narrative_beats", [])
        if not (1 <= len(order) <= 4) or len(order) != len(beats):
            issues.append("invalid_short_clip_beats")
        if float(row.get("target_duration_s") or 0) > 5 or float(row.get("target_duration_s") or 0) <= 0:
            issues.append("duration_out_of_scope")
        frame = row.get("first_frame_path")
        frame_sha = None
        if frame:
            path = ROOT / frame
            if frame not in tracked or not path.is_file() or "/gt/" in frame:
                issues.append("unavailable_or_answer_leaking_image")
            else:
                frame_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if row.get("curation", {}).get("source_target_use") == "rejected_do_not_score" and \
                row.get("source", {}).get("target_image_path"):
            issues.append("rejected_target_still_linked")
        counts[row["discipline"]][row["task_type"]] += 1
        records.append({"id": case_id, "discipline": row["discipline"], "task_type": row["task_type"],
                        "status": "pass_assistant_preflight" if not issues else "needs_fix",
                        "issues": issues, "first_frame_path": frame, "first_frame_sha256": frame_sha,
                        "review_scope": "answer/rubric presence, five-second scope, text integrity, task coverage, tracked input image and target-image exclusion"})
    for discipline, per_task in counts.items():
        if any(per_task[t] not in (14, 15) for t in ("explanation", "problem_solving")):
            raise ValueError(f"Unbalanced discipline: {discipline}")
    if len(rows) != 400 or len(counts) != 14:
        raise ValueError("Expected 400 items over 14 disciplines")
    LEDGER.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    summary = {"items": len(rows), "pass_assistant_preflight": sum(r["status"] == "pass_assistant_preflight" for r in records),
               "needs_fix": sum(r["status"] == "needs_fix" for r in records),
               "items_with_tracked_optional_frame": sum(bool(r["first_frame_sha256"]) for r in records),
               "release_ready": False,
               "limit": "Automated per-item preflight plus assistant review of flagged and high-risk cases; not independent specialist or visual-content certification."}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(review(), ensure_ascii=False, indent=2))
