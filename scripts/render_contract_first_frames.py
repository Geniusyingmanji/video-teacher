"""Render code-bound opening frames for reviewed cases, without video generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generation.contract_frame import render_first_frame
from generation.teaching_contract import load_contracts, prepare_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--num-frames", type=int, default=121)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    prompts = [json.loads(line) for line in args.prompts.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    contracts = load_contracts(args.contracts)
    selected = [case for case in prompts if case["id"] in contracts]
    prepared = prepare_cases(selected, contracts, args.width, args.height,
                             args.num_frames, args.fps)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in prepared:
        path = args.out / f"{case['id']}.png"
        render_first_frame(contracts[case["id"]], args.width, args.height).save(path)
        manifest.append({"id": case["id"], "first_frame": str(path),
                         "teaching_contract_sha256": case["teaching_contract_sha256"]})
        print(f"rendered {case['id']}: {path}")
    (args.out / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
