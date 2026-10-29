"""Import a downloaded GRADE dataset directory or zip into candidate-named images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="extracted GRADE directory or zip archive")
    parser.add_argument("--prompts", type=Path, default=ROOT / "data/prompts/candidate_400.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "data/sources/grade/selected_assets")
    args = parser.parse_args()
    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    rows = [json.loads(line) for line in args.prompts.read_text(encoding="utf-8").splitlines() if line.strip()]
    archive = zipfile.ZipFile(args.source) if args.source.is_file() else None
    members = archive.namelist() if archive else []
    copied = 0
    missing = []
    try:
        for row in rows:
            source = row.get("source", {})
            if source.get("dataset") != "GRADE":
                continue
            for role, key in (("before", "source_image_path"), ("gt", "target_image_path")):
                relative = source.get(key)
                if not relative:
                    missing.append(f"{row['id']}:{role}:no source path")
                    continue
                destination = args.out / role / f"{row['id']}.png"
                if destination.is_file() and destination.stat().st_size > 0:
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                if archive:
                    matches = [name for name in members if name.endswith(relative)]
                    if len(matches) != 1:
                        missing.append(f"{row['id']}:{role}:archive match count {len(matches)}")
                        continue
                    with archive.open(matches[0]) as reader, destination.open("wb") as writer:
                        shutil.copyfileobj(reader, writer)
                else:
                    candidates = (args.source / relative, args.source / relative.removeprefix("image/"))
                    original = next((path for path in candidates if path.is_file()), None)
                    if original is None:
                        missing.append(f"{row['id']}:{role}:missing {relative}")
                        continue
                    shutil.copyfile(original, destination)
                try:
                    with Image.open(destination) as image:
                        image.verify()
                except Exception as exc:
                    destination.unlink(missing_ok=True)
                    missing.append(f"{row['id']}:{role}:invalid image {type(exc).__name__}")
                else:
                    copied += 1
    finally:
        if archive:
            archive.close()
    print(json.dumps({"candidate_grade_items": sum(r.get("source", {}).get("dataset") == "GRADE" for r in rows),
                      "copied": copied, "missing": missing}, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
