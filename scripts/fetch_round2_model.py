"""Fetch the official Diffusers checkpoint used by the round-two probe."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--revision", default=None)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id="Wan-AI/Wan2.2-TI2V-5B-Diffusers",
                      revision=args.revision, local_dir=args.out)
    if not (args.out / "model_index.json").is_file():
        raise SystemExit("Model download is incomplete: model_index.json missing")
    print(args.out.resolve())


if __name__ == "__main__":
    main()
