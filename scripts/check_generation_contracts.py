"""Validate and compile reviewed teaching contracts without generating video."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generation.teaching_contract import ContractError, load_contracts, prepare_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--num-frames", type=int, default=121)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--require-all", action="store_true",
                        help="Fail if any prompt lacks a contract")
    args = parser.parse_args()

    prompts = [json.loads(line) for line in args.prompts.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    contracts = load_contracts(args.contracts)
    missing = [case["id"] for case in prompts if case["id"] not in contracts]
    if args.require_all and missing:
        parser.error(f"{len(missing)} prompts have no contract; first: {missing[:5]}")
    selected = [case for case in prompts if case["id"] in contracts]
    if not selected:
        parser.error("no prompt has a matching contract")
    try:
        compiled = prepare_cases(selected, contracts, args.width, args.height,
                                 args.num_frames, args.fps)
    except ContractError as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in compiled),
                        encoding="utf-8")
    print(f"validated={len(compiled)} missing_contract={len(missing)} output={args.out}")


if __name__ == "__main__":
    main()
