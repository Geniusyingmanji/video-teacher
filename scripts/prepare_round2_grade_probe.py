"""Prepare the readable GRADE-image subset for the first round-two video probe."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/round2_grade_probe11"


def main() -> None:
    rows = [json.loads(s) for s in (ROOT / "data/prompts/round2_candidate_60.jsonl")
            .read_text(encoding="utf-8").splitlines() if s.strip()]
    selected = [r for r in rows if r.get("source", {}).get("dataset") == "GRADE"
                and r["discipline"] != "history"]
    assert len(selected) == 11
    frames = OUT / "first_frames"
    frames.mkdir(parents=True, exist_ok=True)
    for row in selected:
        case_id = row["id"]
        source = ROOT / "data/sources/grade/selected_assets/before" / (case_id + ".png")
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image.convert("RGB").save(frames / (case_id + ".png"))
    (OUT / "prompts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected),
        encoding="utf-8")
    print(f"prepared {len(selected)} GRADE cases in {OUT}")


if __name__ == "__main__":
    main()
