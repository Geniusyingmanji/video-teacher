"""Match each rise-teacher case to top-K MMMU candidate images.

Scoring: keyword overlap between the case's (expected_concepts + visual_elements +
prompt_text) and the MMMU row's (question + subfield + img_type), restricted to
discipline-mapped subjects and with a soft difficulty preference. Outputs a
candidates JSONL: each case gets its top-K candidate image rows.

Usage:
    python scripts/match_mmmu_candidates.py \\
        --prompts data/prompts/pilot_v0_1.jsonl \\
        --mmmu-index /data/zyf/datasets/mmmu/index.jsonl \\
        --out data/first_frames_mmmu/candidates.jsonl \\
        --top-k 5
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


DISCIPLINE_TO_SUBJECTS = {
    # MMMU subjects + AI2D pseudo-subjects (from tag_subject in download_ai2d.py)
    "mathematics": ["Math"],
    "physics": ["Physics", "Materials", "Mechanical_Engineering"],
    "chemistry": ["Chemistry"],
    "biology": ["Biology", "Agriculture",
                "Anatomy", "Ecology", "Life Cycles", "Botany", "Zoology"],
    "medicine": ["Basic_Medical_Science", "Clinical_Medicine",
                 "Diagnostics_and_Laboratory_Medicine", "Pharmacy", "Public_Health",
                 "Anatomy"],
    "computer_science": ["Computer_Science", "Electronics",
                         "Architecture_and_Engineering"],
    "economics": ["Economics", "Finance", "Accounting", "Manage", "Marketing"],
    "civics": ["Sociology", "Psychology"],
    "language_literature": ["Literature"],
    "history": ["History"],
    "geography": ["Geography", "Energy_and_Power",
                  "Earth Science", "Geology", "Astronomy"],
    "art_music": ["Art", "Music", "Art_Theory", "Design"],
}

# Soft difficulty preference (rise-teacher -> MMMU topic_difficulty score)
DIFFICULTY_BONUS = {
    "k12": {"Easy": 2.0, "Medium": 1.0, "Hard": 0.3},
    "undergrad": {"Easy": 0.8, "Medium": 2.0, "Hard": 1.2},
    "professional": {"Easy": 0.3, "Medium": 1.2, "Hard": 2.0},
}

STOPWORDS = set("""
a an the of and or to in on for from by with as at is are was were be been
this that these those it its their your our you we they he she his her them
about into over under between through during before after up down out off
on for of by to with as in at""".split())


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9_]+", " ", text)
    return [t for t in text.split() if len(t) > 2 and t not in STOPWORDS]


def score_candidate(case: dict, mmmu_row: dict) -> float:
    # Tokens we want to match
    case_tokens: list[str] = []
    case_tokens += tokenize(" ".join(case.get("expected_concepts", [])))
    case_tokens += tokenize(" ".join(case.get("expected_visual_elements", [])))
    case_tokens += tokenize(case.get("prompt_text", ""))[:30]  # cap prompt length
    case_tok_count = Counter(case_tokens)

    mmmu_tokens = (tokenize(mmmu_row.get("question", "")) +
                   tokenize(mmmu_row.get("subfield", "")) +
                   tokenize(str(mmmu_row.get("img_type", ""))))
    mmmu_tok_count = Counter(mmmu_tokens)

    # Weighted overlap: each shared token contributes min(case_count, mmmu_count)
    overlap = sum(min(case_tok_count[t], mmmu_tok_count[t])
                  for t in case_tok_count if t in mmmu_tok_count)
    score = float(overlap)

    # Difficulty bonus
    case_diff = case.get("difficulty", "k12")
    mmmu_diff = mmmu_row.get("topic_difficulty", "Medium") or "Medium"
    score += DIFFICULTY_BONUS.get(case_diff, {}).get(mmmu_diff, 1.0)

    # Slight bonus if MMMU image type is a diagram/chart vs raw table
    img_type = str(mmmu_row.get("img_type", "")).lower()
    if "diagram" in img_type or "chart" in img_type or "plot" in img_type:
        score += 0.5

    return score


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--mmmu-index", required=True)
    ap.add_argument("--ai2d-index", default=None,
                    help="Optional AI2D index to merge into the candidate pool.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(args.prompts) if l.strip()]
    # Load MMMU; rewrite image_path to be absolute so cross-source rows are unambiguous
    mmmu_root = Path(args.mmmu_index).parent
    mmmu = []
    for l in open(args.mmmu_index):
        if l.strip():
            r = json.loads(l)
            r["image_path"] = str(mmmu_root / r["image_path"])
            r["source"] = "mmmu"
            mmmu.append(r)
    if args.ai2d_index:
        ai2d_root = Path(args.ai2d_index).parent
        for l in open(args.ai2d_index):
            if l.strip():
                r = json.loads(l)
                r["image_path"] = str(ai2d_root / r["image_path"])
                r["source"] = "ai2d"
                mmmu.append(r)
        print(f"[match] merged AI2D, total pool: {len(mmmu)} images")
    # Group MMMU rows by subject
    by_subject: dict[str, list[dict]] = {}
    for r in mmmu:
        by_subject.setdefault(r["subject"], []).append(r)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_no_cand = 0
    with out_path.open("w") as out_f:
        for case in cases:
            disc = case["discipline"]
            subjects = DISCIPLINE_TO_SUBJECTS.get(disc, [])
            pool: list[dict] = []
            for s in subjects:
                pool.extend(by_subject.get(s, []))
            scored = [(score_candidate(case, r), r) for r in pool]
            scored.sort(key=lambda x: -x[0])
            top = scored[: args.top_k]
            if not top:
                n_no_cand += 1
            out_f.write(json.dumps({
                "case_id": case["id"],
                "discipline": disc,
                "difficulty": case.get("difficulty"),
                "concepts": case.get("expected_concepts", []),
                "candidates": [
                    {
                        "score": round(score, 2),
                        "source": r.get("source", "mmmu"),
                        "subject": r["subject"],
                        "image_path": r["image_path"],
                        "subfield": r.get("subfield"),
                        "img_type": r.get("img_type"),
                        "topic_difficulty": r.get("topic_difficulty"),
                        "question": r.get("question", "")[:200],
                    }
                    for score, r in top
                ],
            }, ensure_ascii=False) + "\n")
            print(f"{case['id']} ({disc}, {case.get('difficulty')}): "
                  f"{len(pool)} pool, top score={top[0][0] if top else 0:.1f}")
    print(f"\n[match] DONE: wrote {args.out}, {n_no_cand} cases with no candidates")


if __name__ == "__main__":
    main()
