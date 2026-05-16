"""Download AI2D (lmms-lab/ai2d, 3088 K-12 science diagrams) and index it
in the same schema as the MMMU index so they can be unified.

Usage:
    python scripts/download_ai2d.py
"""
from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset


OUT_DIR = Path("/home/azureuser/workspace-gzy/zyf/datasets/ai2d")
INDEX_PATH = OUT_DIR / "index.jsonl"


# Heuristic subject tagging based on diagram subject keywords in the question
KW_TO_SUBJECT = [
    (["cell", "tissue", "organ", "human body", "anatomy", "skeleton",
      "muscle", "blood", "heart", "lung", "brain", "nervous", "digestive",
      "respiratory", "circulatory"], "Anatomy"),
    (["food chain", "food web", "predator", "prey", "ecosystem", "habitat",
      "biome", "producer", "consumer", "decomposer"], "Ecology"),
    (["life cycle", "metamorphosis", "larva", "pupa", "egg", "embryo",
      "reproduction", "germination", "seedling"], "Life Cycles"),
    (["plant", "flower", "leaf", "root", "stem", "photosynthesis",
      "chlorophyll"], "Botany"),
    (["animal", "vertebrate", "invertebrate", "mammal", "bird", "reptile",
      "amphibian", "fish", "insect"], "Zoology"),
    (["water cycle", "rock cycle", "weather", "atmosphere", "climate",
      "precipitation", "evaporation", "condensation"], "Earth Science"),
    (["volcano", "earthquake", "plate tectonics", "fault", "magma",
      "geology", "mineral", "fossil"], "Geology"),
    (["sun", "moon", "earth", "planet", "solar system", "orbit", "eclipse",
      "phases", "galaxy", "constellation"], "Astronomy"),
    (["atom", "molecule", "element", "compound", "chemical", "reaction",
      "acid", "base"], "Chemistry"),
    (["force", "motion", "energy", "gravity", "magnet", "electric",
      "circuit", "wave", "light", "sound"], "Physics"),
]


def tag_subject(question: str) -> str:
    q = question.lower()
    for kws, subj in KW_TO_SUBJECT:
        if any(kw in q for kw in kws):
            return subj
    return "Science_General"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img_dir = OUT_DIR / "images"
    img_dir.mkdir(exist_ok=True)

    print("[ai2d] loading lmms-lab/ai2d ...")
    ds = load_dataset("lmms-lab/ai2d", split="test")
    print(f"[ai2d] {len(ds)} samples loaded")

    n_done = 0
    with INDEX_PATH.open("w") as f:
        for i, ex in enumerate(ds):
            img = ex.get("image")
            if img is None:
                continue
            sample_id = f"ai2d_{i:05d}"
            fname = f"{sample_id}.png"
            fpath = img_dir / fname
            try:
                if not fpath.exists():
                    img.save(str(fpath))
            except Exception as e:
                print(f"[ai2d]   skip {sample_id}: {e}")
                continue
            subject = tag_subject(ex.get("question") or "")
            row = {
                "subject": subject,
                "split": "test",
                "id": sample_id,
                "image_idx": 1,
                "image_path": str(fpath.relative_to(OUT_DIR)),
                "question": (ex.get("question") or "")[:400],
                "img_type": "diagram",
                "topic_difficulty": "Easy",  # AI2D is K-12 / grade school
                "subfield": subject,
                "options": ex.get("options") or [],
                "answer": ex.get("answer"),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_done += 1
            if (i + 1) % 500 == 0:
                print(f"[ai2d]   {i+1}/{len(ds)} done")
    print(f"\n[ai2d] DONE: {n_done} indexed, index at {INDEX_PATH}")


if __name__ == "__main__":
    main()
