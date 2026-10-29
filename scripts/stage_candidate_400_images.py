"""Stage only GRADE image pairs referenced by the current 400-question pool.

Usage:
    python scripts/stage_candidate_400_images.py
    git commit -m "Add selected GRADE question images"
    git push origin main

The source archive and unselected images stay outside the commit.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "data/prompts/candidate_400.jsonl"
ASSETS = ROOT / "data/sources/grade/selected_assets"


def main() -> None:
    rows = [json.loads(line) for line in PROMPTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 400 or len({row["id"] for row in rows}) != 400:
        raise ValueError("expected 400 unique candidate IDs")
    grade = [row for row in rows if row.get("source", {}).get("dataset") == "GRADE"]
    paths: list[Path] = []
    for row in grade:
        for role in ("before", "gt"):
            path = ASSETS / role / f"{row['id']}.png"
            if not path.is_file():
                raise FileNotFoundError(path)
            with Image.open(path) as image:
                image.verify()
            paths.append(path.relative_to(ROOT))
    for start in range(0, len(paths), 50):
        subprocess.run(
            ["git", "add", "-f", "--", *(str(path) for path in paths[start:start + 50])],
            cwd=ROOT,
            check=True,
        )
    total = sum((ROOT / path).stat().st_size for path in paths)
    print(f"Staged {len(paths)} images for {len(grade)} GRADE questions ({total:,} bytes).")


if __name__ == "__main__":
    main()
