"""TeachQuiz-T / Learning Gain scoring helpers.

The dimension measures whether a student VLM answers case-specific quiz items
better after seeing the generated video than without the video.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from eval.students.base import StudentModel


ConditionFrames = list[Image.Image] | None


def score_quiz(
    *,
    student: StudentModel,
    quiz_items: list[dict[str, Any]],
    frames: ConditionFrames = None,
    transcript: str | None = None,
) -> dict[str, Any]:
    answers = []
    correct = 0
    for item in quiz_items:
        ans = student.answer(
            question=item["question"],
            choices=item["choices"],
            frames=frames,
            transcript=transcript,
        )
        is_correct = ans.choice == item["answer"]
        correct += int(is_correct)
        answers.append(
            {
                "id": item.get("id"),
                "question": item["question"],
                "gold": item["answer"],
                "pred": ans.choice,
                "correct": is_correct,
                "raw": ans.raw,
            }
        )
    total = max(1, len(quiz_items))
    return {
        "score": round(correct / total, 4),
        "n_correct": correct,
        "n_total": len(quiz_items),
        "answers": answers,
    }


def learning_gain(
    *,
    pre_score: float,
    post_score: float,
    random_score: float | None = None,
    max_baseline_score: float = 0.8,
) -> dict[str, float | bool]:
    baseline = max(pre_score, random_score if random_score is not None else pre_score)
    gain = post_score - baseline
    denom = max(1e-6, 1.0 - baseline)
    normalized = gain / denom
    return {
        "baseline_score": round(baseline, 4),
        "learning_gain": round(gain, 4),
        "normalized_gain": round(normalized, 4),
        "valid": baseline < max_baseline_score,
        "positive_gain": gain > 0,
    }
