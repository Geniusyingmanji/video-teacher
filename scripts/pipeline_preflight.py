"""Read-only prerequisites for a matched 60-case generation/evaluation run."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def check(prompts: Path, first_frames: Path, quiz: Path, model: Path,
          student_model: Path, *, check_runtime: bool = True) -> dict:
    blockers: list[str] = []
    cases = read_jsonl(prompts)
    ids = [row.get("id") for row in cases]
    if not cases or len(ids) != len(set(ids)):
        blockers.append("prompt file missing, empty, or contains duplicate IDs")
    missing_frames = [cid for cid in ids if not (first_frames / f"{cid}.png").is_file()]
    if missing_frames:
        blockers.append(f"first frames missing: {len(missing_frames)}/{len(ids)}")
    quiz_rows = read_jsonl(quiz)
    quiz_ids = [row.get("case_id") for row in quiz_rows]
    missing_quiz = sorted(set(ids) - set(quiz_ids))
    if not quiz_rows or len(quiz_ids) != len(set(quiz_ids)) or missing_quiz:
        blockers.append(f"frozen shared quiz missing or incomplete: {len(set(ids) & set(quiz_ids))}/{len(ids)}")
    if not model.is_dir():
        blockers.append(f"Wan model directory missing: {model}")
    if not student_model.is_dir():
        blockers.append(f"student model directory missing: {student_model}")
    if check_runtime:
        for package in ("torch", "diffusers", "transformers", "cv2", "openai"):
            if importlib.util.find_spec(package) is None:
                blockers.append(f"Python package missing: {package}")
        if importlib.util.find_spec("torch") is not None:
            try:
                probe = subprocess.run([sys.executable, "-c",
                                        "import torch; print(int(torch.cuda.is_available()))"],
                                       capture_output=True, text=True, timeout=30, check=False)
                if probe.returncode != 0:
                    blockers.append("torch/CUDA runtime failed in isolated probe")
                elif probe.stdout.strip() != "1":
                    blockers.append("CUDA GPU unavailable")
            except subprocess.TimeoutExpired:
                blockers.append("torch/CUDA runtime probe timed out")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        if not endpoint or "YOUR-ENDPOINT" in endpoint:
            blockers.append("AZURE_OPENAI_ENDPOINT not configured")
        if not shutil.which("az"):
            blockers.append("Azure CLI (az) unavailable for judge authentication")
    return {
        "ready": not blockers, "prompt_count": len(ids),
        "first_frame_count": len(ids) - len(missing_frames),
        "shared_quiz_count": len(set(ids) & set(quiz_ids)),
        "blockers": blockers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, default=ROOT / "data/prompts/pilot_v0_1.jsonl")
    parser.add_argument("--first-frames", type=Path, default=ROOT / "data/first_frames")
    parser.add_argument("--quiz", type=Path, default=ROOT / "data/teachquiz/pilot_v0_1_quiz.jsonl")
    parser.add_argument("--model", type=Path, default=ROOT / "models/Wan2.2-TI2V-5B-Diffusers")
    parser.add_argument("--student-model", type=Path, default=ROOT / "models/Qwen3-VL-2B-Instruct")
    parser.add_argument("--strict", action="store_true", help="exit nonzero if any blocker remains")
    args = parser.parse_args()
    report = check(args.prompts, args.first_frames, args.quiz, args.model, args.student_model)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
