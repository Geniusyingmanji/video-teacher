"""Download MMMU validation split and index by subject/subfield/difficulty.

Saves images to /data/zyf/datasets/mmmu/images/{subject}/ and writes an index
JSONL: /data/zyf/datasets/mmmu/index.jsonl with one row per (sample, image_n).

Usage:
    python scripts/download_mmmu.py [--splits validation,dev] [--subjects Math,Physics,...]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# MMMU's 30 subjects organized by rise-teacher discipline
DISCIPLINE_TO_SUBJECTS = {
    "mathematics": ["Math"],
    "physics": ["Physics", "Materials", "Mechanical_Engineering"],
    "chemistry": ["Chemistry"],
    "biology": ["Biology", "Agriculture"],
    "medicine": ["Basic_Medical_Science", "Clinical_Medicine",
                 "Diagnostics_and_Laboratory_Medicine", "Pharmacy", "Public_Health"],
    "computer_science": ["Computer_Science", "Electronics", "Architecture_and_Engineering"],
    "economics": ["Economics", "Finance", "Accounting", "Manage", "Marketing"],
    "civics": ["Sociology", "Psychology"],  # closest matches
    "language_literature": ["Literature"],
    "history": ["History"],
    "geography": ["Geography", "Energy_and_Power"],
    "art_music": ["Art", "Music", "Art_Theory", "Design"],
}

ALL_SUBJECTS = sorted({s for subs in DISCIPLINE_TO_SUBJECTS.values() for s in subs})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/home/azureuser/workspace-gzy/zyf/datasets/mmmu")
    ap.add_argument("--splits", default="validation,dev",
                    help="Comma-separated splits (validation=900, dev=150, test=10500).")
    ap.add_argument("--subjects", default="",
                    help="Comma-separated subjects, or empty for all 30.")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    img_root = out_dir / "images"
    img_root.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.jsonl"

    subjects = args.subjects.split(",") if args.subjects else ALL_SUBJECTS
    subjects = [s.strip() for s in subjects if s.strip()]
    splits = [s.strip() for s in args.splits.split(",") if s.strip()]

    from datasets import load_dataset

    n_total = 0
    n_images = 0
    with index_path.open("w") as idx_f:
        for subject in subjects:
            subj_dir = img_root / subject
            subj_dir.mkdir(exist_ok=True)
            for split in splits:
                try:
                    print(f"[mmmu] loading {subject}/{split} ...")
                    ds = load_dataset("MMMU/MMMU", subject, split=split)
                except Exception as e:
                    print(f"[mmmu] skip {subject}/{split}: {e}")
                    continue
                for i, ex in enumerate(ds):
                    sample_id = ex.get("id") or f"{subject}_{split}_{i}"
                    # MMMU has image_1..image_7 columns
                    for j in range(1, 8):
                        key = f"image_{j}"
                        img = ex.get(key)
                        if img is None:
                            continue
                        try:
                            fname = f"{sample_id}_img{j}.png"
                            fpath = subj_dir / fname
                            if not fpath.exists():
                                img.save(str(fpath))
                            row = {
                                "subject": subject,
                                "split": split,
                                "id": sample_id,
                                "image_idx": j,
                                "image_path": str(fpath.relative_to(out_dir)),
                                "question": (ex.get("question") or "")[:400],
                                "img_type": ex.get("img_type", ""),
                                "topic_difficulty": ex.get("topic_difficulty", ""),
                                "subfield": ex.get("subfield", ""),
                                "options": ex.get("options", []),
                                "answer": ex.get("answer", ""),
                            }
                            idx_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                            n_images += 1
                        except Exception as e:
                            print(f"[mmmu]   skip {sample_id}/{key}: {e}")
                    n_total += 1
                print(f"[mmmu]   {subject}/{split}: {len(ds)} samples processed")
    print(f"\n[mmmu] DONE: {n_total} samples, {n_images} images, index at {index_path}")


if __name__ == "__main__":
    main()
