"""Inspect every candidate for concrete content and task-design defects."""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/prompts/candidate_400.jsonl"
OUT = ROOT / "results/paper_item_curation/content_400_triage.csv"

EASY_HIGH = {
    "med_prob_01": "15 mg/kg × 70 kg is one multiplication; relabel introductory",
    "med_prob_02": "70 mL × 75/min with one unit conversion; relabel introductory/intermediate",
    "chem_high_02": "direct substitution into ΔG=ΔH−TΔS; relabel intermediate",
    "bio_high_02": "direct Hardy–Weinberg substitution; relabel intermediate",
    "econ_high_02": "MV=PQ with fixed V,Q is one proportional step; relabel introductory",
}
REPEATED_YEAR = {f"grade_his_task_{n}" for n in range(16, 23)}
KNOWN_CONTENT_ISSUES = {
    "grade_biology_task_10": (
        "source_target_scientifically_questionable",
        "target image makes fox→bear a food-chain link; exclude until corrected with evidence",
    ),
    "disciplinegen_biology_26fdde9159c8433d": (
        "meiosis_allele_claim_ambiguous",
        "verify the A/a sister-chromatid mutation claim and rewrite to one checkable step",
    ),
}


def inspect(row: dict) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    fixes: list[str] = []
    cid = row["id"]
    source = row.get("source") or {}
    dataset = source.get("dataset")
    prompt = row["prompt_text"]
    if dataset == "GRADE":
        image = ROOT / "data/sources/grade/selected_assets/before" / f"{cid}.png"
        if not image.is_file() and "supplied source image" in prompt.lower():
            flags.append("required_source_image_absent_locally")
            fixes.append("acquire the exact source image or remove from image-conditioned run")
        if row.get("curation", {}).get("visual_pair_screening", {}).get("status") == "target_rejected":
            flags.append("source_target_image_rejected")
            fixes.append("do not score against the source target image; use the corrected written answer or create a verified replacement")
    elif dataset == "DisciplineGen-1M" and "supplied source image" in prompt.lower():
        local = source.get("local_before_path")
        if not local or not (ROOT / local).is_file():
            flags.append("claims_supplied_image_without_local_asset")
            fixes.append("build and verify an initial image, or rewrite as pure T2V")
    if "<image>" in prompt:
        flags.append("literal_image_placeholder")
        fixes.append("replace placeholder with an actual input reference")
    if cid in EASY_HIGH:
        flags.append("difficulty_recalibrated_from_high" if row["difficulty"] != "high"
                     else "high_difficulty_overstated")
        fixes.append(EASY_HIGH[cid])
    if cid in REPEATED_YEAR and "historical year" in prompt.lower():
        flags.append("repeated_single_year_fill_template")
        fixes.append("keep at most one; replace others with causal or temporal reasoning")
    if cid in KNOWN_CONTENT_ISSUES and not (
            (cid == "grade_biology_task_10" and "bear unconnected" in prompt.lower()) or
            (cid == "disciplinegen_biology_26fdde9159c8433d" and "do not infer a mutation" in prompt.lower())):
        flag, fix = KNOWN_CONTENT_ISSUES[cid]
        flags.append(flag)
        fixes.append(fix)
    if len(row.get("expected_narrative_order") or []) > 4 or \
            "manual_atomic_scope_required" in row.get("curation", {}).get("quality_flags", []):
        flags.append("short_clip_scope_too_broad")
        fixes.append("reduce to one checkable state change or move to longer-video track")
    rubric = row.get("discipline_specific_rubric") or []
    generic_rules = {
        "the transformation follows the source instruction exactly",
        "unrelated content is preserved",
        "the final change is visible and independently checkable",
        "labels reproduce the source terminology",
        "every label points to exactly one intended target",
        "labels remain readable without covering evidence",
    }
    if rubric and all(item.strip().lower() in generic_rules for item in rubric):
        flags.append("rubric_lacks_subject_truth_check")
        fixes.append("add a case-specific correct answer and failure condition")
    return sorted(set(flags)), sorted(set(fixes))


def main() -> None:
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 400 or len({r["id"] for r in rows}) != 400:
        raise ValueError("expected 400 unique candidates")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("id", "discipline", "task_type", "difficulty", "original_difficulty",
                         "content_flags", "specific_fix", "prompt_text"))
        for row in rows:
            flags, fixes = inspect(row)
            counts.update(flags)
            writer.writerow((row["id"], row["discipline"], row["task_type"],
                             row["difficulty"], row.get("original_difficulty", row["difficulty"]),
                             ";".join(flags), ";".join(fixes),
                             row["prompt_text"]))
    print(json.dumps({"rows": len(rows), "flags": dict(counts), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
