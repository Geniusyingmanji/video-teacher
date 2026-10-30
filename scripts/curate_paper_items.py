"""Audit candidate diversity and export only independently reviewed paper items.

Review JSONL has two independent entries per case plus one adjudication entry.
No review is inferred from existing draft status or generated text.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("source_valid", "answer_correct", "atomic_clip", "visible_endpoint",
              "unambiguous_rubric", "license_verified")
COGNITIVE_SKILLS = {"recall", "application", "multi_step_reasoning", "transfer"}
DIFFICULTIES = {"introductory", "intermediate", "advanced"}
CORE_DISCIPLINES = ("mathematics", "physics", "chemistry", "biology", "medicine",
                    "computer_science", "economics", "civics", "language_literature",
                    "history", "geography", "art_music")
TASK_TYPES = ("explanation", "problem_solving")
TEACHING_TASKS = {"concept_mechanism", "worked_step", "evidence_interpretation",
                  "procedure_strategy"}


def normalized_discipline(label: str) -> str:
    """Keep source labels intact while using one frozen reporting vocabulary."""
    return "art_music" if label == "music" else label


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def item_hash(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def review_errors(row: dict, reviews: list[dict]) -> list[str]:
    case_id = row["id"]
    digest = item_hash(row)
    independent = [r for r in reviews if r.get("case_id") == case_id
                   and r.get("role") == "reviewer" and r.get("item_sha256") == digest]
    adjudications = [r for r in reviews if r.get("case_id") == case_id
                     and r.get("role") == "adjudicator" and r.get("item_sha256") == digest]
    errors = []
    if row.get("curation", {}).get("status") in {"exclude_content_quality", "draft_needs_content_repair"}:
        errors.append("content_repair_required")
    reviewers = {r.get("reviewer_id") for r in independent if r.get("reviewer_id")}
    if len(independent) != 2 or len(reviewers) != 2:
        errors.append("two_independent_reviews_required")
    for review in independent:
        if any(review.get(field) is not True for field in DIMENSIONS):
            errors.append("review_gate_failed")
        if review.get("difficulty") not in DIFFICULTIES or review.get("cognitive_skill") not in COGNITIVE_SKILLS:
            errors.append("review_scale_missing")
        if review.get("teaching_task") not in TEACHING_TASKS:
            errors.append("review_teaching_task_missing")
    if len(adjudications) != 1:
        errors.append("one_adjudication_required")
    else:
        final = adjudications[0]
        if not final.get("reviewer_id") or final.get("reviewer_id") in reviewers:
            errors.append("adjudicator_must_be_independent")
        if final.get("decision") != "accept":
            errors.append("not_accepted")
        for field in ("source_url", "license", "reference_answer", "atomic_target",
                      "expected_final_state", "failure_criteria", "difficulty_rationale"):
            if not isinstance(final.get(field), str) or not final[field].strip():
                errors.append(f"missing_{field}")
        if str(final.get("license", "")).strip().lower() in {
            "unknown", "not_verified", "unverified", "pending", "none", "n/a"
        }:
            errors.append("license_unverified")
        if final.get("difficulty") not in DIFFICULTIES or final.get("cognitive_skill") not in COGNITIVE_SKILLS:
            errors.append("final_scale_missing")
        if final.get("teaching_task") not in TEACHING_TASKS:
            errors.append("final_teaching_task_missing")
        for field in ("target_audience", "observable_evidence"):
            if not isinstance(final.get(field), str) or not final[field].strip():
                errors.append(f"missing_{field}")
        if len(independent) == 2 and any(
            r.get("difficulty") != final.get("difficulty") or
            r.get("cognitive_skill") != final.get("cognitive_skill") or
            r.get("teaching_task") != final.get("teaching_task") for r in independent
        ) and not str(final.get("disagreement_resolution", "")).strip():
            errors.append("disagreement_resolution_required")
    return sorted(set(errors))


def audit(rows: list[dict], reviews: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate candidate IDs")
    unknown = sorted({r.get("case_id") for r in reviews} - set(by_id))
    if unknown:
        raise ValueError(f"review IDs absent from candidates: {unknown[:5]}")
    by_case = defaultdict(list)
    for review in reviews:
        by_case[review["case_id"]].append(review)
    queue = []
    accepted = []
    for row in rows:
        errors = review_errors(row, by_case[row["id"]])
        queue.append({"id": row["id"], "item_sha256": item_hash(row),
                      "discipline": row["discipline"], "task_type": row["task_type"],
                      "normalized_discipline": normalized_discipline(row["discipline"]),
                      "original_difficulty": row["difficulty"], "gates": errors})
        if not errors:
            final = next(r for r in by_case[row["id"]] if r["role"] == "adjudicator")
            accepted.append({**row, "reviewed_difficulty": final["difficulty"],
                             "cognitive_skill": final["cognitive_skill"],
                             "normalized_discipline": normalized_discipline(row["discipline"]),
                             "teaching_task": final["teaching_task"],
                             "target_audience": final["target_audience"],
                             "observable_evidence": final["observable_evidence"],
                             "atomic_target": final["atomic_target"],
                             "expected_final_state": final["expected_final_state"],
                             "reference_answer": final["reference_answer"],
                             "failure_criteria": final["failure_criteria"],
                             "reviewed_source_sha256": item_hash(row)})
    report = {
        "candidate_count": len(rows), "accepted_count": len(accepted),
        "original_difficulty": dict(Counter(r["difficulty"] for r in rows)),
        "normalized_disciplines": dict(sorted(Counter(
            normalized_discipline(r["discipline"]) for r in rows).items())),
        "discipline_task_cells": {f"{d}/{t}": n for (d, t), n in sorted(
            Counter((r["discipline"], r["task_type"]) for r in rows).items())},
        "accepted_difficulty": dict(Counter(r["reviewed_difficulty"] for r in accepted)),
        "accepted_cognitive_skill": dict(Counter(r["cognitive_skill"] for r in accepted)),
        "accepted_teaching_task": dict(Counter(r["teaching_task"] for r in accepted)),
        "core_cell_minimum": 5,
        "candidate_core_cell_gaps": {f"{d}/{t}": max(0, 5 - sum(
            r["discipline"] == d and r["task_type"] == t for r in rows))
            for d in CORE_DISCIPLINES for t in TASK_TYPES},
        "core_cell_gaps": {f"{d}/{t}": max(0, 5 - sum(
            r["discipline"] == d and r["task_type"] == t for r in accepted))
            for d in CORE_DISCIPLINES for t in TASK_TYPES},
        "outside_core_taxonomy": dict(Counter(r["discipline"] for r in rows
                                               if r["discipline"] not in CORE_DISCIPLINES)),
        "gate_counts": dict(Counter(gate for item in queue for gate in item["gates"])),
    }
    return report, queue, accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=ROOT / "data/prompts/candidate_400.jsonl")
    parser.add_argument("--reviews", type=Path, default=ROOT / "data/curated/paper_item_reviews.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "results/paper_item_curation")
    args = parser.parse_args()
    rows = read_jsonl(args.candidates)
    if not rows:
        parser.error("candidate file is empty or missing")
    report, queue, accepted = audit(rows, read_jsonl(args.reviews))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "review_queue.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in queue), encoding="utf-8")
    (args.out / "accepted.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in accepted), encoding="utf-8")
    print(f"candidates={len(rows)} accepted={len(accepted)} out={args.out}")


if __name__ == "__main__":
    main()
