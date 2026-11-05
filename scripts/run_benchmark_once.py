"""Preflight and run the complete 2x8 benchmark with an OpenAI-compatible API."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Generation manifest with locally accessible video_path values")
    parser.add_argument("--prompts", help="Prompt JSONL; defaults to the 60-case pilot or 400-case draft")
    parser.add_argument("--out", help="Output directory")
    parser.add_argument("--full-400", action="store_true", help="Evaluate exactly 400 unique prompt IDs")
    parser.add_argument("--check-only", action="store_true", help="Run local preflight without API calls")
    args = parser.parse_args()
    missing = [name for name in ("VIDEO_TEACHER_API_KEY", "VIDEO_TEACHER_BASE_URL", "VIDEO_TEACHER_MODEL")
               if not os.environ.get(name, "").strip()]
    if missing:
        parser.error("set these environment variables first: " + ", ".join(missing))
    root = Path(__file__).resolve().parents[1]
    prompt_path = Path(args.prompts or (root / "data/prompts/candidate_400_lessons_v3.jsonl" if args.full_400
                                        else root / "data/prompts/pilot_v0_1.jsonl")).resolve()
    output_path = Path(args.out or (root / "results/benchmark_400_lessons_v2" if args.full_400
                                    else root / "results/benchmark_v2")).resolve()
    if args.full_400:
        try:
            cases = [json.loads(line) for line in prompt_path.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
        except (OSError, ValueError) as exc:
            parser.error(f"cannot read 400-case prompts: {exc}")
        ids = [case.get("id") for case in cases if isinstance(case, dict)]
        if len(ids) != 400 or len(set(ids)) != 400:
            parser.error("--full-400 requires exactly 400 unique prompt IDs")
    command = [sys.executable, "-m", "eval.run_benchmark_v2",
               "--prompts", str(prompt_path),
               "--manifest", str(Path(args.manifest).resolve()),
               "--out", str(output_path)]
    preflight = subprocess.run([*command, "--preflight"], cwd=root, check=False)
    if preflight.returncode or args.check_only:
        return preflight.returncode
    return subprocess.run(command, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
