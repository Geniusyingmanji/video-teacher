"""Deterministic dummy students for TeachQuiz smoke tests.

These are not evaluation models. They let the data plumbing, scoring, resume
logic, and report generation run on machines without a local VLM checkpoint.
"""

from __future__ import annotations

import hashlib

from PIL import Image

from eval.students.base import StudentAnswer


class DummyStudent:
    name = "dummy"

    def answer(
        self,
        *,
        question: str,
        choices: list[str],
        frames: list[Image.Image] | None = None,
        transcript: str | None = None,
    ) -> StudentAnswer:
        key = question + "|" + "|".join(choices)
        idx = hashlib.sha256(key.encode("utf-8")).digest()[0] % len(choices)
        choice = "ABCD"[idx]
        return StudentAnswer(choice=choice, raw=f"dummy:{choice}")


class OracleStudent:
    """Answer-key backed student for debugging the upper-bound path only."""

    name = "oracle"

    def __init__(self, answers: dict[str, str] | None = None) -> None:
        self.answers = answers or {}

    def answer(
        self,
        *,
        question: str,
        choices: list[str],
        frames: list[Image.Image] | None = None,
        transcript: str | None = None,
    ) -> StudentAnswer:
        choice = self.answers.get(question, "A")
        return StudentAnswer(choice=choice, raw=f"oracle:{choice}", confidence=1.0)
