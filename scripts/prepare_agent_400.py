"""Build an agent-ready view of the frozen 400 candidates and expose coverage gaps."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/prompts/candidate_400.jsonl"
OUTPUT = ROOT / "data/prompts/candidate_400_agent_ready.jsonl"
REPORT = ROOT / "data/curated/candidate_400_agent_coverage.json"


def build() -> dict:
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 400 or len({r["id"] for r in rows}) != 400:
        raise ValueError("Expected exactly 400 unique candidates")
    available = ROOT / "data/first_frames_repaired_v1"
    counts = defaultdict(Counter)
    policies = Counter()
    for row in rows:
        counts[row["discipline"]][row["task_type"]] += 1
        source = row.get("source") or {}
        source_before = source.get("local_before_path") or source.get("source_image_path")
        repaired = available / f"{row['id']}.png"
        original = ROOT / "data/first_frames" / f"{row['id']}.png"
        # Only the eleven SVG-derived repairs are versioned here; unchanged
        # openings live in the original tracked 60-frame directory.
        candidates = [repaired, original] if (available / f"{row['id']}.svg").is_file() else [original, repaired]
        if source_before:
            candidates.extend([ROOT / "data/sources/grade/selected_assets/before" / f"{row['id']}.png",
                               ROOT / source_before,
                               ROOT / "data/sources/grade/data/sources/grade/full" / source_before])
        frame = None
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                with Image.open(candidate) as im:
                    im.verify()
            except (OSError, ValueError):
                continue
            frame = candidate
            break
        # Only a verified input image counts; a target/gt image leaks the answer.
        row["first_frame_policy"] = "available_optional" if frame else "none"
        if frame:
            row["first_frame_path"] = str(frame.relative_to(ROOT)).replace("\\", "/")
        row["video_goal"] = "knowledge_point" if row["task_type"] == "explanation" else "solve_problem"
        policies[row["first_frame_policy"]] += 1
    OUTPUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    # 14 disciplines x ~28.6 items: each needs both video goals, roughly half each.
    matrix = {d: {"knowledge_point": c["explanation"], "solve_problem": c["problem_solving"],
                  "total": sum(c.values()), "gap_to_14_each": {
                      "knowledge_point": max(0, 14 - c["explanation"]),
                      "solve_problem": max(0, 14 - c["problem_solving"]),
                  }} for d, c in sorted(counts.items())}
    report = {"candidate_count": len(rows), "release_ready": False,
              "first_frame_policy": dict(policies), "by_discipline": matrix,
              "note": "Coverage gaps are selection targets, not fabricated tasks. Source truth and image rights still require human review."}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
