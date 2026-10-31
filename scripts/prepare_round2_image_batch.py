"""Prepare the 24 selected cases with existing first-frame/source images."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/round2_image_batch24"


def main() -> None:
    rows = [json.loads(s) for s in (ROOT / "data/prompts/round2_candidate_60.jsonl")
            .read_text(encoding="utf-8").splitlines() if s.strip()]
    selected = [r for r in rows if r.get("source", {}).get("dataset") == "GRADE"
                or (ROOT / "data/first_frames_repaired_v1" / (r["id"] + ".png")).is_file()]
    if len(selected) != 24:
        raise SystemExit(f"Expected 24 image-backed cases, found {len(selected)}")
    frames = OUT / "first_frames"
    frames.mkdir(parents=True, exist_ok=True)
    evidence = []
    for row in selected:
        case_id = row["id"]
        if row.get("source", {}).get("dataset") == "GRADE":
            status = row.get("curation", {}).get("visual_pair_screening", {}).get("status")
            if status not in {"manually_checked", "passed"}:
                raise SystemExit(f"GRADE image pair not checked: {case_id}: {status}")
            source = ROOT / "data/sources/grade/selected_assets/before" / (case_id + ".png")
        else:
            source = ROOT / "data/first_frames_repaired_v1" / (case_id + ".png")
        if not source.is_file():
            raise SystemExit(f"Missing first image: {source}")
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image.convert("RGB").save(frames / (case_id + ".png"))
        digest = hashlib.sha256((frames / (case_id + ".png")).read_bytes()).hexdigest()
        evidence.append({"id": case_id, "source": str(source.relative_to(ROOT)),
                         "first_frame_sha256": digest})
        row["target_duration_s"] = 5
    (OUT / "prompts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected), encoding="utf-8")
    (OUT / "image_manifest.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in evidence), encoding="utf-8")
    print(f"prepared {len(selected)} cases in {OUT}")


if __name__ == "__main__":
    main()
