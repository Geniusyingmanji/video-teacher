"""Assemble a traceable 400-item research pool from existing prompt files.

This is a candidate pool, not a reviewed or redistributable benchmark release.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "data" / "prompts"
OUT = PROMPTS / "candidate_400.jsonl"
REPORT = ROOT / "data" / "curated" / "candidate_400_report.json"
SOURCE_MANIFEST = ROOT / "data" / "curated" / "candidate_400_sources.jsonl"

# The source pool contains twelve near-identical "Generate sheet music on ...
# Measure 1" topics. Keep three with different clef/metre and replace the
# other nine with older drafts in underrepresented pilot disciplines.
DROP_IDS = {
    "disciplinegen_music_2ad2d505e0d64643",
    "disciplinegen_music_88c21d03e4201ffa",
    "disciplinegen_music_90251e36efa679df",
    "disciplinegen_music_c80ec38538b2694a",
    "disciplinegen_music_dc4a9194e2dafb28",
    "disciplinegen_music_e53863cafe1d34ff",
    "disciplinegen_music_e659c41c922d909c",
    "disciplinegen_music_ebc11b723e10ec2a",
    "disciplinegen_music_ec2f444553647eeb",
}
ARCHETYPE_REPAIRS = {
    "disciplinegen_biology_637de7c74ec514f2": (
        "spatial_reasoning", ["five labeled species at distinct trophic levels",
                              "directed energy-flow arrows attached to the correct species"]),
    "disciplinegen_biology_79da49549e98a464": (
        "labeling", ["one animal cell diagram", "unambiguous leader lines for each named structure"]),
    "disciplinegen_biology_ce413ce67a202d21": (
        "labeling", ["one neuron diagram", "distinct labels for cell body, axon, dendrites, and terminals"]),
}
EXTRA_IDS = (
    *(f"cand_med_cs_gap_{i:02d}" for i in range(1, 10)),
    *(f"cand_hs_civ_{i:02d}" for i in range(1, 7)),
    *(f"cand_hs_lang_{i:02d}" for i in range(1, 7)),
    *(f"cand_hs_art_{i:02d}" for i in range(1, 7)),
)


def read_rows(name: str) -> list[dict]:
    path = PROMPTS / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def focus_multisource(row: dict) -> dict:
    """Remove generic template text only when the complete source fits.

    Long source records keep their full original prompt and are held for manual
    scoping; truncating them could silently change the correct answer.
    """
    row = deepcopy(row)
    source = row["source"]
    instruction = source.get("original_instruction") or source.get("original_annotation") or ""
    flags = []
    if len(instruction) <= 300 and instruction.strip():
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = (
            "Create a five-second teaching clip using the supplied source image. "
            f"Show one checkable visual change: {instruction.strip()} "
            "Keep unrelated content fixed and hold the result for inspection."
        )
        row["expected_concepts"] = [f"Source-defined target: {instruction.strip()}"]
        row["expected_narrative_order"] = [
            "Show the unchanged source state",
            "Make the requested visual change",
            "Hold the resulting state for inspection",
        ]
        row["curation"]["prompt_focus"] = "source_instruction_complete"
    else:
        flags.append("manual_atomic_scope_required")
        row["curation"]["prompt_focus"] = "original_full_instruction_preserved"
    if len(instruction) > 300:
        flags.append("source_instruction_over_300_chars")
    if len(row["prompt_text"]) > 500:
        flags.append("prompt_over_500_chars")
    if row["curation"].get("pedagogical_archetype") == "comparison" and not re.search(
        r"compar|versus|\bvs\b|differ|two cases", instruction, re.I
    ):
        flags.append("comparison_template_needs_review")
    if row["id"] in ARCHETYPE_REPAIRS:
        archetype, visual_elements = ARCHETYPE_REPAIRS[row["id"]]
        row.setdefault("original_prompt_text", row["prompt_text"])
        row["prompt_text"] = (
            "Create a five-second teaching clip using the supplied source image. "
            f"Show one checkable change: {instruction.strip()} "
            "Keep unrelated content fixed and hold the result."
        )
        row["expected_visual_elements"] = visual_elements
        row["expected_narrative_order"] = [
            "Show the source diagram", "Add the requested arrows or labels",
            "Hold the completed diagram for inspection",
        ]
        row["curation"]["archetype_corrected_from"] = "comparison"
        row["curation"]["pedagogical_archetype"] = archetype
        flags = [flag for flag in flags if flag != "comparison_template_needs_review"]
        if len(row["prompt_text"]) > 500 and "prompt_over_500_chars" not in flags:
            flags.append("prompt_over_500_chars")
    row["curation"]["quality_flags"] = flags
    return row


def focus_pilot(row: dict) -> dict:
    row = deepcopy(row)
    flags = []
    if "10-second" in row["prompt_text"] and row.get("target_duration_s") == 5:
        row["original_prompt_text"] = row["prompt_text"]
        row["prompt_text"] = row["prompt_text"].replace("10-second", "5-second")
        flags.append("duration_wording_corrected_from_10_to_5")
    if len(row.get("expected_narrative_order", [])) > 4:
        flags.append("manual_atomic_scope_required")
    if flags:
        row.setdefault("curation", {})["quality_flags"] = flags
    return row


def main() -> None:
    groups = [
        ("pilot_v0_2.jsonl", [focus_pilot(row) for row in read_rows("pilot_v0_2.jsonl")]),
        ("multisource_pilot_300.jsonl", [focus_multisource(row) for row in
            read_rows("multisource_pilot_300.jsonl") if row["id"] not in DROP_IDS]),
    ]
    extras = {}
    extra_sources = {}
    for name in ("candidates_subagent_medicine_cs_gaps.jsonl", "candidates_subagent_humanities_social.jsonl"):
        for row in read_rows(name):
            if row["id"] in EXTRA_IDS:
                if row["id"] in extras:
                    raise ValueError(f"Duplicate extra ID: {row['id']}")
                extras[row["id"]] = row
                extra_sources[row["id"]] = name
    if set(extras) != set(EXTRA_IDS):
        raise ValueError(f"Missing extras: {sorted(set(EXTRA_IDS) - set(extras))}")

    rows = []
    manifest = []
    ids = set()
    texts = set()
    for name, batch in groups + [("selected_draft_extras", [extras[key] for key in EXTRA_IDS])]:
        for row in batch:
            case_id = row["id"]
            normalized = re.sub(r"\s+", " ", row["prompt_text"].strip().casefold())
            if case_id in ids or normalized in texts:
                raise ValueError(f"Duplicate ID or exact prompt: {case_id}")
            ids.add(case_id)
            texts.add(normalized)
            rows.append(row)
            source_file = extra_sources[case_id] if name == "selected_draft_extras" else name
            curation = row.get("curation", {})
            manifest.append({
                "id": case_id,
                "source_file": f"data/prompts/{source_file}",
                "source_dataset": row.get("source", {}).get("dataset", "project_draft"),
                "curation_status": curation.get("status", "draft_needs_subject_review"),
                "redistribution_license": row.get("source", {}).get("license", "not_verified"),
            })

    if len(rows) != 400:
        raise ValueError(f"Expected 400 cases, found {len(rows)}")
    if len(DROP_IDS) != 9 or set(DROP_IDS) & ids:
        raise ValueError("The intended near-duplicate exclusions were not applied")
    required = {"id", "discipline", "task_type", "prompt_text", "expected_concepts", "expected_visual_elements", "expected_narrative_order"}
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"{row['id']}: missing {sorted(missing)}")

    report = {
        "candidate_count": len(rows),
        "release_ready": False,
        "by_source_file": dict(Counter(item["source_file"] for item in manifest)),
        "by_discipline": dict(sorted(Counter(row["discipline"] for row in rows).items())),
        "by_task_type": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "by_curation_status": dict(sorted(Counter(item["curation_status"] for item in manifest).items())),
        "quality_flags": dict(sorted(Counter(flag for row in rows for flag in
            row.get("curation", {}).get("quality_flags", [])).items())),
        "excluded_source_ids": sorted(DROP_IDS),
        "known_limitations": [
            "Only the existing four reviewed multisource rows have completed visual and subject review.",
            "GRADE redistribution rights remain unverified; keep upstream IDs and assets separate.",
            "The 27 supplemental rows are earlier generated drafts, not new expert-authored items.",
            "Sports and music remain separate taxonomy labels from the original 12-discipline pilot.",
            "No videos, first frames, or frozen learner quizzes are provided for every item.",
            "A 3-5 second task-feasibility and near-duplicate semantic review is still required.",
        ],
    }
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    SOURCE_MANIFEST.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} candidates to {OUT.relative_to(ROOT)}")
    print(f"source counts: {report['by_source_file']}")


if __name__ == "__main__":
    main()
