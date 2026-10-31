"""Read-only prerequisites for a matched 60-case generation/evaluation run."""

from __future__ import annotations

import argparse
import hashlib
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


def quiz_defects(rows: list[dict], expected_ids: set[str]) -> list[str]:
    defects: list[str] = []
    seen_questions: set[str] = set()
    for row in rows:
        case_id = row.get("case_id")
        if case_id not in expected_ids:
            defects.append(f"unexpected quiz case_id: {case_id!r}")
        questions = row.get("quiz")
        if not isinstance(questions, list) or not questions:
            defects.append(f"quiz has no questions: {case_id!r}")
            continue
        for question in questions:
            if not isinstance(question, dict):
                defects.append(f"invalid quiz question in {case_id!r}")
                continue
            question_id = question.get("id")
            choices = question.get("choices")
            answer = question.get("answer")
            if not isinstance(question_id, str) or not question_id or question_id in seen_questions:
                defects.append(f"missing or duplicate question id: {question_id!r}")
            seen_questions.add(question_id)
            if (not isinstance(choices, list) or not 2 <= len(choices) <= 26 or
                    not isinstance(answer, str) or
                    answer not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:len(choices)]):
                defects.append(f"invalid choices/answer: {question_id!r}")
    return defects


def check(prompts: Path, first_frames: Path, quiz: Path, model: Path,
          student_model: Path, *, check_runtime: bool = True,
          require_quiz: bool = True,
          first_frame_review: Path | None = None) -> dict:
    blockers: list[str] = []
    cases = read_jsonl(prompts)
    ids = [row.get("id") for row in cases]
    if (not cases or any(not isinstance(cid, str) or not cid for cid in ids) or
            len(ids) != len(set(ids))):
        blockers.append("prompt file missing, empty, or contains duplicate IDs")
    valid_ids = {cid for cid in ids if isinstance(cid, str) and cid}
    missing_frames = [cid for cid in valid_ids if not (first_frames / f"{cid}.png").is_file()]
    if missing_frames:
        blockers.append(f"first frames missing: {len(missing_frames)}/{len(ids)}")
    if first_frame_review is not None:
        reviews = read_jsonl(first_frame_review)
        reviewed = {row.get("id"): row for row in reviews}
        not_approved = sorted(cid for cid in valid_ids
                              if reviewed.get(cid, {}).get("verdict") != "PASS")
        if not_approved:
            blockers.append(f"first-frame quality review not passed: "
                            f"{len(not_approved)}/{len(valid_ids)}; "
                            f"first: {not_approved[0]}")
        changed = []
        for cid in sorted(valid_ids - set(missing_frames) - set(not_approved)):
            expected_hash = reviewed[cid].get("sha256")
            if expected_hash:
                actual_hash = hashlib.sha256((first_frames / f"{cid}.png").read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    changed.append(cid)
        if changed:
            blockers.append(f"first-frame changed after review: {len(changed)}/{len(valid_ids)}; "
                            f"first: {changed[0]}")
    quiz_rows = read_jsonl(quiz) if require_quiz else []
    quiz_ids = [row.get("case_id") for row in quiz_rows]
    present_quiz_ids = {cid for cid in quiz_ids if isinstance(cid, str) and cid}
    missing_quiz = sorted(valid_ids - present_quiz_ids)
    if require_quiz and (not quiz_rows or len(quiz_ids) != len(present_quiz_ids) or missing_quiz):
        blockers.append(f"frozen shared quiz missing or incomplete: {len(valid_ids & present_quiz_ids)}/{len(ids)}")
    defects = quiz_defects(quiz_rows, valid_ids) if require_quiz else []
    if require_quiz and defects:
        blockers.append(f"frozen shared quiz invalid: {len(defects)} defect(s); first: {defects[0]}")
    if not model.is_dir():
        blockers.append(f"Wan model directory missing: {model}")
    if require_quiz and not student_model.is_dir():
        blockers.append(f"student model directory missing: {student_model}")
    if check_runtime:
        packages = ("torch", "diffusers", "transformers", "cv2")
        if require_quiz:
            packages += ("openai",)
        for package in packages:
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
        if require_quiz:
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            if not endpoint or "YOUR-ENDPOINT" in endpoint:
                blockers.append("AZURE_OPENAI_ENDPOINT not configured")
            if not shutil.which("az"):
                blockers.append("Azure CLI (az) unavailable for judge authentication")
    return {
        "ready": not blockers, "prompt_count": len(ids),
        "first_frame_count": len(valid_ids) - len(missing_frames),
        "shared_quiz_count": len(valid_ids & present_quiz_ids),
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
    parser.add_argument("--generation-only", action="store_true",
                        help="check 60-case generation without requiring the shared quiz or student model")
    parser.add_argument("--first-frame-review", type=Path,
                        help="require PASS in a reviewed per-case first-frame report")
    args = parser.parse_args()
    report = check(args.prompts, args.first_frames, args.quiz, args.model, args.student_model,
                   require_quiz=not args.generation_only,
                   first_frame_review=args.first_frame_review)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
