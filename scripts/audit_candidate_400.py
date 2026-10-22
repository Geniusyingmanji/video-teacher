"""Produce a review queue for the 400-item draft; no automatic expert approval."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data/prompts/candidate_400.jsonl"
REPORT = ROOT / "data/curated/candidate_400_quality_audit.json"
QUEUE = ROOT / "data/curated/candidate_400_review_queue.jsonl"


def source_text(row: dict) -> str:
    source = row.get("source", {})
    return source.get("original_instruction") or source.get("original_annotation") or row["prompt_text"]


def main() -> None:
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 400:
        raise ValueError(f"Expected 400 rows, got {len(rows)}")
    texts = [source_text(row) for row in rows]
    matrix = TfidfVectorizer(analyzer="char", ngram_range=(3, 5)).fit_transform(texts)
    scores = cosine_similarity(matrix)
    pairs = []
    links: dict[str, list[dict]] = {row["id"]: [] for row in rows}
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            score = float(scores[i, j])
            if score < 0.70:
                continue
            pair = {"id_a": rows[i]["id"], "id_b": rows[j]["id"], "similarity": round(score, 3),
                    "same_discipline": rows[i]["discipline"] == rows[j]["discipline"]}
            pairs.append(pair)
            links[rows[i]["id"]].append({"id": rows[j]["id"], "similarity": pair["similarity"]})
            links[rows[j]["id"]].append({"id": rows[i]["id"], "similarity": pair["similarity"]})
    pairs.sort(key=lambda item: item["similarity"], reverse=True)

    queue = []
    for row, original in zip(rows, texts):
        flags = list(row.get("curation", {}).get("quality_flags", []))
        if len(original) > 300 and "source_instruction_over_300_chars" not in flags:
            flags.append("source_text_over_300_chars")
        if len(row["expected_narrative_order"]) > 4:
            flags.append("too_many_story_beats_for_short_clip")
        if row["discipline"] in {"medicine", "civics"}:
            flags.append("domain_expert_review_required")
        if links[row["id"]]:
            flags.append("near_duplicate_topic_review")
        if row.get("source", {}).get("dataset") == "GRADE":
            flags.append("source_license_unverified")
        if row.get("curation", {}).get("status") != "reviewed_release_ready":
            flags.append("manual_content_review_required")
        queue.append({
            "id": row["id"], "discipline": row["discipline"], "task_type": row["task_type"],
            "source_text_chars": len(original), "prompt_chars": len(row["prompt_text"]),
            "quality_flags": sorted(set(flags)),
            "near_duplicate_candidates": sorted(links[row["id"]], key=lambda x: -x["similarity"]),
        })

    report = {
        "count": len(rows), "method": "character 3-5 gram TF-IDF cosine on original source instructions; review signal, not semantic equivalence",
        "threshold": 0.70, "near_duplicate_pairs": pairs,
        "near_duplicate_pair_count": len(pairs),
        "quality_flag_counts": dict(sorted(Counter(flag for item in queue for flag in item["quality_flags"]).items())),
        "release_ready": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    QUEUE.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in queue), encoding="utf-8")
    print(f"audited={len(rows)} near_duplicate_pairs_for_review={len(pairs)}")


if __name__ == "__main__":
    main()
