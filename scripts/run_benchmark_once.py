"""Preflight and run the complete 2x8 benchmark with an OpenAI-compatible API."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Generation manifest with locally accessible video_path values")
    parser.add_argument("--prompts", default="data/prompts/pilot_v0_1.jsonl")
    parser.add_argument("--out", default="results/benchmark_v2")
    parser.add_argument("--check-only", action="store_true", help="Run local preflight without API calls")
    args = parser.parse_args()
    missing = [name for name in ("VIDEO_TEACHER_API_KEY", "VIDEO_TEACHER_BASE_URL", "VIDEO_TEACHER_MODEL")
               if not os.environ.get(name, "").strip()]
    if missing:
        parser.error("set these environment variables first: " + ", ".join(missing))
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "eval.run_benchmark_v2",
               "--prompts", str(Path(args.prompts).resolve()),
               "--manifest", str(Path(args.manifest).resolve()),
               "--out", str(Path(args.out).resolve())]
    preflight = subprocess.run([*command, "--preflight"], cwd=root, check=False)
    if preflight.returncode or args.check_only:
        return preflight.returncode
    return subprocess.run(command, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
