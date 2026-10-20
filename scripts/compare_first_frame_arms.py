"""Make fair-aspect side-by-side sheets for first-frame method review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for candidate in sorted(args.candidate.glob("*.png")):
        baseline = args.baseline / candidate.name
        if not baseline.is_file():
            continue
        with Image.open(baseline) as old, Image.open(candidate) as new:
            old_size, new_size = old.size, new.size
            left = ImageOps.pad(old.convert("RGB"), (args.width, args.height),
                                method=Image.Resampling.LANCZOS, color="white")
            right = ImageOps.pad(new.convert("RGB"), (args.width, args.height),
                                 method=Image.Resampling.LANCZOS, color="white")
        sheet = Image.new("RGB", (args.width * 2, args.height + 38), "#e8edf0")
        draw = ImageDraw.Draw(sheet)
        draw.text((10, 10), f"ordinary first frame  {old_size}", fill="black")
        draw.text((args.width + 10, 10), f"contract first frame  {new_size}", fill="black")
        sheet.paste(left, (0, 38))
        sheet.paste(right, (args.width, 38))
        output = args.out / candidate.name
        sheet.save(output)
        rows.append({"id": candidate.stem, "baseline": str(baseline),
                     "candidate": str(candidate), "comparison": str(output),
                     "baseline_size": old_size, "candidate_size": new_size})
        print(output)
    (args.out / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
