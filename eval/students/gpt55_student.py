"""GPT-5.5 student adapter for TeachQuiz-T.

Uses our existing keyless Azure OpenAI client. Both the pre-quiz
(no frames) and post-quiz (with frames) use the same GPT-5.5 model,
which eliminates model-mismatch confounds.

Example:
    from eval.students.gpt55_student import GPT55Student
    student = GPT55Student()
    ans = student.answer(question="...", choices=["A opt","B opt","C opt","D opt"])
"""

from __future__ import annotations

import re
from typing import Any

from PIL import Image

from eval.students.base import StudentAnswer
from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


CHOICE_RE = re.compile(r"\b([ABCD])\b", re.IGNORECASE)

SYSTEM_NO_VIDEO = (
    "You are a student answering a multiple-choice question. "
    "Reply with ONLY the letter of the correct answer (A, B, C, or D) — nothing else."
)

SYSTEM_WITH_VIDEO = (
    "You are a student who has just watched an educational video (8 frames shown). "
    "Answer the multiple-choice question using both what you see in the frames and your knowledge. "
    "Reply with ONLY the letter of the correct answer (A, B, C, or D) — nothing else."
)


def _format_question(question: str, choices: list[str]) -> str:
    lines = [question]
    for i, c in enumerate(choices):
        lines.append(f"{chr(65+i)}. {c}")
    return "\n".join(lines)


def _parse_choice(text: str) -> str:
    text = text.strip()
    m = CHOICE_RE.search(text)
    if m:
        return m.group(1).upper()
    for ch in "ABCD":
        if text.upper().startswith(ch):
            return ch
    return "A"


class GPT55Student:
    name = "gpt55"

    def __init__(self, max_tokens: int = 64) -> None:
        self.max_tokens = max_tokens

    def answer(
        self,
        *,
        question: str,
        choices: list[str],
        frames: list[Image.Image] | None = None,
        transcript: str | None = None,
    ) -> StudentAnswer:
        q_text = _format_question(question, choices)
        if frames:
            system = SYSTEM_WITH_VIDEO
            content = frames_as_multimodal_content(frames, q_text)
        else:
            system = SYSTEM_NO_VIDEO
            content = q_text

        raw = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            max_tokens=self.max_tokens,
        )
        choice = _parse_choice(raw)
        return StudentAnswer(choice=choice, raw=raw)
