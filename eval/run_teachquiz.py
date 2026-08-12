"""Run TeachQuiz-T learning-gain evaluation.

This runner is separate from eval.run_eval while the metric is experimental.
It evaluates each case under three conditions:

- pre/no_video: student answers from the quiz text only.
- post/generated_video: student answers after seeing frames from the case video.
- random_video: student answers after seeing frames from a mismatched case.

The metric is post - max(pre, random), with a normalized-gain variant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
import traceback
from pathlib import Path
from typing import Any

from eval.dimensions.learning_gain import learning_gain, score_quiz
from eval.frame_extractor import extract_frames
from eval.students.dummy import DummyStudent, OracleStudent
from eval.students.smolvlm2 import SmolVLM2Student
from eval.students.qwen25vl import Qwen25VLStudent
from eval.students.qwen3vl import Qwen3VLStudent
from eval.students.gpt55_student import GPT55Student


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_quiz_rows(rows: list[dict[str, Any]]) -> None:
    """Fail early on probe defects that would silently invalidate comparisons."""
    case_ids: set[str] = set()
    question_ids: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id or case_id in case_ids:
            raise ValueError(f"missing or duplicate quiz case_id: {case_id!r}")
        case_ids.add(case_id)
        if not row.get("quiz"):
            raise ValueError(f"quiz case {case_id!r} has no questions")
        for item in row["quiz"]:
            question_id = str(item.get("id", "")).strip()
            if not question_id or question_id in question_ids:
                raise ValueError(f"missing or duplicate question id: {question_id!r}")
            question_ids.add(question_id)
            choices = item.get("choices", [])
            answer = item.get("answer")
            if len(choices) < 2 or answer not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:len(choices)]:
                raise ValueError(f"invalid choices/answer for question {question_id!r}")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_student(args: argparse.Namespace, quiz_rows: list[dict[str, Any]]):
    if args.student == "dummy":
        return DummyStudent()
    if args.student == "oracle":
        answers = {}
        for row in quiz_rows:
            for item in row["quiz"]:
                answers[item["question"]] = item["answer"]
        return OracleStudent(answers)
    if args.student == "qwen25vl":
        if not args.student_model_path:
            raise SystemExit("--student-model-path is required for --student qwen25vl")
        return Qwen25VLStudent(
            args.student_model_path,
            device_map=args.device_map,
            torch_dtype=args.torch_dtype,
            max_new_tokens=args.max_new_tokens,
        )
    if args.student == "smolvlm2":
        if not args.student_model_path:
            raise SystemExit("--student-model-path is required for --student smolvlm2")
        return SmolVLM2Student(
            args.student_model_path,
            device_map=args.device_map,
            torch_dtype=args.torch_dtype,
            max_new_tokens=args.max_new_tokens,
        )
    if args.student == "qwen3vl":
        if not args.student_model_path:
            raise SystemExit("--student-model-path is required for --student qwen3vl")
        return Qwen3VLStudent(
            args.student_model_path,
            device_map=args.device_map,
            torch_dtype=args.torch_dtype,
            max_new_tokens=args.max_new_tokens,
        )
    if args.student == "gpt55":
        return GPT55Student()
    raise SystemExit(f"unknown student: {args.student}")


def choose_random_manifest(
    manifest: list[dict[str, Any]],
    case_id: str,
    rng: random.Random,
    prompts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    candidates = [m for m in manifest if m.get("id") != case_id and m.get("status") == "ok"]
    if not candidates:
        return None
    # Prefer controls with the same discipline, task type, and difficulty. This
    # reduces the chance that a trivially unrelated clip becomes an artificially
    # weak baseline. Relax constraints only when the dataset is too small.
    if prompts and case_id in prompts:
        target = prompts[case_id]
        fields = ("discipline", "task_type", "difficulty")
        for n_fields in range(len(fields), 0, -1):
            matched = [
                m for m in candidates
                if all(
                    prompts.get(m.get("id"), {}).get(field) == target.get(field)
                    for field in fields[:n_fields]
                )
            ]
            if matched:
                candidates = matched
                break
    # Sorting makes the seeded choice independent of manifest row order.
    return rng.choice(sorted(candidates, key=lambda item: str(item.get("id", ""))))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--quiz", "--probe", dest="quiz", required=True,
                    help="Frozen shared quiz/probe JSONL. --probe is a backwards-compatible alias.")
    ap.add_argument("--probe-origin", choices=["frozen_shared", "output_adaptive"],
                    default="frozen_shared",
                    help="Declare whether questions were frozen before generation. "
                         "Output-adaptive probes are diagnostic and not comparable across models.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--student", default="dummy", choices=["dummy", "oracle", "qwen25vl", "qwen3vl", "smolvlm2", "gpt55"])
    ap.add_argument("--student-model-path", default="")
    ap.add_argument("--device-map", default="auto")
    ap.add_argument("--torch-dtype", default="bfloat16",
                    choices=["bfloat16", "float16", "float32", "auto"])
    ap.add_argument("--max-new-tokens", type=int, default=16)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--frame-max-px", type=int, default=384)
    ap.add_argument("--max-questions", type=int, default=0,
                    help="If >0, evaluate only the first N quiz items per case.")
    ap.add_argument("--skip-random", action="store_true",
                    help="Skip random-video control. Useful for slow CPU smoke tests.")
    ap.add_argument("--max-baseline-score", type=float, default=0.8,
                    help="Cases at or above this no-video/random baseline are not counted as valid learning-gain cases.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=123)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    per_case_path = out_dir / "per_case.jsonl"

    prompts = {row["id"]: row for row in load_jsonl(args.prompts)}
    quiz_rows = load_jsonl(args.quiz)
    validate_quiz_rows(quiz_rows)
    if args.probe_origin == "output_adaptive":
        print("[teachquiz] WARNING: output-adaptive probes are diagnostic only; "
              "do not use their scores for cross-model ranking")
    manifest = [row for row in load_jsonl(args.manifest) if row.get("status") == "ok"]
    videos = {row["id"]: row for row in manifest}
    if args.limit > 0:
        quiz_rows = quiz_rows[: args.limit]

    student = load_student(args, quiz_rows)
    rng = random.Random(args.seed)

    done_ids = set()
    if per_case_path.exists():
        for row in load_jsonl(per_case_path):
            done_ids.add(row.get("id"))

    todo = [row for row in quiz_rows if row["case_id"] not in done_ids]
    print(f"[teachquiz] student={student.name} cases={len(quiz_rows)} todo={len(todo)}")
    started = time.time()

    with per_case_path.open("a", encoding="utf-8") as out_f:
        for i, row in enumerate(todo, 1):
            cid = row["case_id"]
            try:
                quiz_items = row["quiz"]
                if args.max_questions > 0:
                    quiz_items = quiz_items[: args.max_questions]
                if cid not in videos:
                    raise RuntimeError(f"missing video in manifest for {cid}")
                case = prompts.get(cid, {})
                video_path = videos[cid]["video_path"]
                frames = extract_frames(video_path, n=args.n_frames, resize_max=args.frame_max_px)

                random_entry = None if args.skip_random else choose_random_manifest(
                    manifest, cid, rng, prompts
                )
                random_frames = None
                random_id = None
                if random_entry:
                    random_id = random_entry["id"]
                    random_frames = extract_frames(
                        random_entry["video_path"],
                        n=args.n_frames,
                        resize_max=args.frame_max_px,
                    )

                pre = score_quiz(student=student, quiz_items=quiz_items)
                post = score_quiz(student=student, quiz_items=quiz_items, frames=frames)
                rand = score_quiz(
                    student=student,
                    quiz_items=quiz_items,
                    frames=random_frames,
                ) if random_frames else None
                lg = learning_gain(
                    pre_score=float(pre["score"]),
                    post_score=float(post["score"]),
                    random_score=float(rand["score"]) if rand else None,
                    max_baseline_score=args.max_baseline_score,
                )
                res = {
                    "id": cid,
                    "discipline": case.get("discipline"),
                    "task_type": case.get("task_type"),
                    "student": student.name,
                    "video_path": video_path,
                    "random_video_id": random_id,
                    "pre": pre,
                    "post_video": post,
                    "random_video": rand,
                    **lg,
                }
            except Exception as exc:
                res = {
                    "id": cid,
                    "student": getattr(student, "name", args.student),
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()[:1000],
                }
            out_f.write(json.dumps(res, ensure_ascii=False) + "\n")
            out_f.flush()
            print(
                f"[teachquiz] [{i}/{len(todo)}] {cid}: "
                f"gain={res.get('learning_gain', '?')} post={res.get('post_video', {}).get('score', '?')} "
                f"wall={(time.time() - started) / 60:.1f}m"
            )

    all_rows = load_jsonl(per_case_path)
    aggregate = build_aggregate(all_rows)
    aggregate["protocol"] = {
        "student": student.name,
        "quiz_path": str(Path(args.quiz).resolve()),
        "quiz_sha256": file_sha256(args.quiz),
        "probe_origin": args.probe_origin,
        "cross_model_comparable": args.probe_origin == "frozen_shared",
        "random_control": "skipped" if args.skip_random else "seeded_matched",
        "random_seed": args.seed,
        "match_priority": ["discipline", "task_type", "difficulty"],
        "max_baseline_score": args.max_baseline_score,
        "n_frames": args.n_frames,
        "frame_max_px": args.frame_max_px,
    }
    with (out_dir / "aggregate.json").open("w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2, ensure_ascii=False)
    print(f"[teachquiz] wrote {out_dir / 'aggregate.json'}")


def mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [r for r in rows if "error" not in r and r.get("valid")]
    scored = [r for r in rows if "error" not in r]
    by_discipline: dict[str, list[dict[str, Any]]] = {}
    by_task: dict[str, list[dict[str, Any]]] = {}
    for r in valid:
        by_discipline.setdefault(r.get("discipline") or "unknown", []).append(r)
        by_task.setdefault(r.get("task_type") or "unknown", []).append(r)

    def summarize(rs: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "n": len(rs),
            "pre_score": mean([float(r["pre"]["score"]) for r in rs]),
            "post_video_score": mean([float(r["post_video"]["score"]) for r in rs]),
            "random_video_score": mean([
                float(r["random_video"]["score"]) for r in rs if r.get("random_video")
            ]),
            "learning_gain": mean([float(r["learning_gain"]) for r in rs]),
            "raw_gain": mean([float(r.get("raw_gain", r["post_video"]["score"] - r["pre"]["score"])) for r in rs]),
            "control_adjusted_gain": mean([
                float(r.get(
                    "control_adjusted_gain",
                    r["post_video"]["score"] - (
                        r["random_video"]["score"] if r.get("random_video") else r["pre"]["score"]
                    ),
                )) for r in rs
            ]),
            "normalized_gain": mean([float(r["normalized_gain"]) for r in rs]),
            "positive_gain_rate": mean([1.0 if r.get("positive_gain") else 0.0 for r in rs]),
        }

    return {
        "n_total": len(rows),
        "n_scored": len(scored),
        "n_valid": len(valid),
        "overall": summarize(valid),
        "per_discipline": {k: summarize(v) for k, v in sorted(by_discipline.items())},
        "per_task_type": {k: summarize(v) for k, v in sorted(by_task.items())},
    }


if __name__ == "__main__":
    main()
