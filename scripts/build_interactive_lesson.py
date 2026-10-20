"""Build a standalone interactive lesson without running a video generator."""

from __future__ import annotations

import argparse

from generation.interactive_lesson import build_from_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default="data/interactive/convex_lens.json")
    parser.add_argument("--contracts", default="data/teaching_contracts/examples.jsonl")
    parser.add_argument("--out", default="results/interactive/convex_lens.html")
    args = parser.parse_args()
    lesson = build_from_files(args.spec, args.contracts, args.out)
    print(f"Built {args.out}: {len(lesson['variants'])} validated states")


if __name__ == "__main__":
    main()
