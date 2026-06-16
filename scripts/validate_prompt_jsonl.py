"""Validate rise-teacher prompt JSONL files.

This is a lightweight schema/duplicate check for candidate files. It does not
promote rows or judge educational quality.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED = [
    "id",
    "discipline",
    "subdomain",
    "task_type",
    "difficulty",
    "prompt_text",
    "expected_concepts",
    "expected_visual_elements",
    "expected_narrative_order",
    "pedagogical_target_audience",
    "discipline_specific_rubric",
    "audio_narration_required",
]

VALID_TASKS = {"explanation", "problem_solving"}
VALID_DIFFICULTIES = {"k12", "undergrad", "professional", "low", "medium", "high"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--require-first-frame", action="store_true")
    args = ap.parse_args()

    had_error = False
    seen: set[str] = set()
    counts = Counter()

    for raw_path in args.paths:
        path = Path(raw_path)
        with path.open() as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception as exc:
                    print(f"{path}:{lineno}: invalid JSON: {exc}")
                    had_error = True
                    continue
                cid = row.get("id")
                if cid in seen:
                    print(f"{path}:{lineno}: duplicate id: {cid}")
                    had_error = True
                seen.add(cid)
                for field in REQUIRED:
                    if field not in row:
                        print(f"{path}:{lineno}: missing {field}")
                        had_error = True
                if row.get("task_type") not in VALID_TASKS:
                    print(f"{path}:{lineno}: invalid task_type {row.get('task_type')!r}")
                    had_error = True
                if row.get("difficulty") not in VALID_DIFFICULTIES:
                    print(f"{path}:{lineno}: invalid difficulty {row.get('difficulty')!r}")
                    had_error = True
                for field in [
                    "expected_concepts",
                    "expected_visual_elements",
                    "expected_narrative_order",
                    "discipline_specific_rubric",
                ]:
                    if not isinstance(row.get(field), list) or not row.get(field):
                        print(f"{path}:{lineno}: {field} must be a non-empty list")
                        had_error = True
                if args.require_first_frame:
                    ff = row.get("first_frame")
                    if not isinstance(ff, dict):
                        print(f"{path}:{lineno}: first_frame must be an object")
                        had_error = True
                    else:
                        for field in ["prompt", "must_include", "avoid", "quality_checks"]:
                            if field not in ff or not ff[field]:
                                print(f"{path}:{lineno}: first_frame.{field} is required")
                                had_error = True
                counts[(row.get("discipline"), row.get("task_type"), row.get("difficulty"))] += 1

    print(f"validated_rows={len(seen)}")
    for (discipline, task_type, difficulty), n in sorted(counts.items()):
        print(f"{discipline}\t{task_type}\t{difficulty}\t{n}")
    raise SystemExit(1 if had_error else 0)


if __name__ == "__main__":
    main()
