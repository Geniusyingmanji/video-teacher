"""Select a balanced, provisional 60-case short-video cohort from the 400 candidates.

Selection is not a content review or authorization to generate. The report
records the remaining per-item gates explicitly.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = (
    "mathematics", "physics", "chemistry", "biology", "medicine",
    "computer_science", "economics", "civics", "language_literature",
    "history", "geography", "art_music",
)
REJECT_FLAGS = {
    "manual_atomic_scope_required", "domain_expert_review_required",
    "source_target_extra_edit_rejected", "too_many_story_beats_for_short_clip",
    "source_target_food_chain_corrected",
}
KNOWN_BAD_OLD_VIDEOS = {"phys_prob_01", "chem_exp_01"}


def main() -> None:
    source = ROOT / "data/prompts/candidate_400.jsonl"
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    previous_ids = {json.loads(line)["id"] for line in
                    (ROOT / "data/prompts/pilot_v0_1.jsonl").read_text(
                        encoding="utf-8").splitlines() if line.strip()}
    audit_path = ROOT / "results/remote_60_20261031/audit_baseline/audit.jsonl"
    motion = {r["id"]: r for r in (json.loads(s) for s in
              audit_path.read_text(encoding="utf-8").splitlines() if s.strip())}
    review_path = ROOT / "data/first_frames_repaired_v1/review_report_visual_20261031.jsonl"
    frame_review = {r["id"]: r for r in (json.loads(s) for s in
                    review_path.read_text(encoding="utf-8").splitlines() if s.strip())}
    old_options = [r for r in rows if r["id"] in previous_ids
                   and r["id"] not in KNOWN_BAD_OLD_VIDEOS
                   and r["id"] in motion and motion[r["id"]].get("flags") == []
                   and frame_review.get(r["id"], {}).get("verdict") == "PASS"
                   and not frame_review[r["id"]].get("issues")
                   and r.get("target_duration_s") == 5
                   and not REJECT_FLAGS.intersection(
                       r.get("curation", {}).get("quality_flags", []))]
    old_options.sort(key=lambda r: (
        len(r.get("expected_narrative_order", [])) > 3,
        -motion[r["id"]]["motion_score"], r["id"],
    ))
    old_selected = []
    for row in old_options:
        if sum(x["discipline"] == row["discipline"] for x in old_selected) < 1:
            old_selected.append(row)
        if len(old_selected) == 10:
            break
    if len(old_selected) != 10:
        raise SystemExit(f"Only {len(old_selected)} old cases meet provisional filters")
    selected = []
    for discipline in DISCIPLINES:
        eligible = [r for r in rows if r["discipline"] == discipline
                    and r["id"] not in previous_ids
                    and (r.get("target_duration_s") == 5 or
                         (r.get("target_duration_s") is None and
                          "five-second" in r["prompt_text"].lower()))
                    and r.get("curation", {}).get("status") not in
                    {"exclude_content_quality", "draft_needs_content_repair"}
                    and not REJECT_FLAGS.intersection(
                        r.get("curation", {}).get("quality_flags", []))]
        # Prefer a single action and a concrete visual endpoint. Break ties by
        # shorter wording; this is a triage heuristic, never a quality verdict.
        eligible.sort(key=lambda r: (
            r["id"] in previous_ids,
            len(r.get("expected_narrative_order", [])) > 3,
            len(r["prompt_text"]), r["id"],
        ))
        needed = 5 - sum(r["discipline"] == discipline for r in old_selected)
        if len(eligible) < needed:
            raise SystemExit(f"Insufficient provisional candidates: {discipline}: {len(eligible)}/{needed}")
        selected.extend(eligible[:needed])
    selected.extend(old_selected)
    assert len(selected) == len({r["id"] for r in selected}) == 60
    grade_missing = [r["id"] for r in selected
                     if r.get("source", {}).get("dataset") == "GRADE"
                     and not (ROOT / "data/sources/grade/selected_assets/before" /
                              (r["id"] + ".png")).is_file()]
    out = ROOT / "data/prompts/round2_candidate_60.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected),
                   encoding="utf-8")
    report = {
        "status": "provisional_do_not_generate",
        "source": str(source.relative_to(ROOT)),
        "count": len(selected),
        "by_discipline": dict(Counter(r["discipline"] for r in selected)),
        "by_task_type": dict(Counter(r["task_type"] for r in selected)),
        "source_dataset": dict(Counter(r.get("source", {}).get("dataset", "authored")
                                       for r in selected)),
        "previous_pilot_overlap": sum(r["id"] in previous_ids for r in selected),
        "retained_old_ids": [r["id"] for r in old_selected],
        "existing_pilot_first_frames": sum(
            (ROOT / "data/first_frames_repaired_v1" / (r["id"] + ".png")).is_file()
            for r in selected),
        "grade_source_images_missing": grade_missing,
        "first_frames_to_create": [r["id"] for r in selected
                                   if not (ROOT / "data/first_frames_repaired_v1" /
                                           (r["id"] + ".png")).is_file()],
        "unresolved_gates": [
            "independent source and answer review",
            "one observable five-second action per case",
            "source/target image inspection where applicable",
            "answer-free first frame for every case",
            "protected exact text and equations",
            "five-case paired generation and visual acceptance before full run",
        ],
        "items": [{"id": r["id"], "discipline": r["discipline"],
                   "task_type": r["task_type"],
                   "source_dataset": r.get("source", {}).get("dataset", "authored"),
                   "curation_status": r.get("curation", {}).get("status", "unreviewed"),
                   "quality_flags": r.get("curation", {}).get("quality_flags", [])}
                  for r in selected],
    }
    report_path = ROOT / "results/round2_selection/report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"selected={len(selected)} report={report_path}")


if __name__ == "__main__":
    main()
