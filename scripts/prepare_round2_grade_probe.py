"""Prepare the readable GRADE-image subset for the first round-two video probe."""

from __future__ import annotations

import json
import hashlib
import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/round2_grade_probe11"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="Use already imported GRADE images only")
    args = ap.parse_args()
    rows = [json.loads(s) for s in (ROOT / "data/prompts/round2_candidate_60.jsonl")
            .read_text(encoding="utf-8").splitlines() if s.strip()]
    selected = [r for r in rows if r.get("source", {}).get("dataset") == "GRADE"
                and r["discipline"] != "history"]
    assert len(selected) == 11
    frames = OUT / "first_frames"
    frames.mkdir(parents=True, exist_ok=True)
    evidence = []
    for row in selected:
        case_id = row["id"]
        source = ROOT / "data/sources/grade/selected_assets/before" / (case_id + ".png")
        if not source.is_file():
            if args.offline:
                raise SystemExit(f"Missing source image in offline mode: {case_id}")
            from huggingface_hub import hf_hub_download
            source = Path(hf_hub_download(
                repo_id="VisionXLab/GRADE", repo_type="dataset",
                filename=row["source"]["source_image_path"],
            ))
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image.convert("RGB").save(frames / (case_id + ".png"))
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        frame_hash = hashlib.sha256((frames / (case_id + ".png")).read_bytes()).hexdigest()
        evidence.append({"id": case_id, "source_path": row["source"]["source_image_path"],
                         "source_sha256": source_hash, "first_frame_sha256": frame_hash})
    (OUT / "prompts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected),
        encoding="utf-8")
    manifest = OUT / "image_manifest.jsonl"
    if manifest.is_file():
        prior = [json.loads(s) for s in manifest.read_text(encoding="utf-8").splitlines() if s.strip()]
        fingerprint = lambda items: [(r["id"], r["source_path"], r["source_sha256"])
                                     for r in items]
        if fingerprint(prior) != fingerprint(evidence):
            raise SystemExit("Downloaded GRADE source differs from the pinned image manifest")
    else:
        manifest.write_text("".join(json.dumps(r) + "\n" for r in evidence),
                            encoding="utf-8")
    print(f"prepared {len(selected)} GRADE cases in {OUT}")


if __name__ == "__main__":
    main()
