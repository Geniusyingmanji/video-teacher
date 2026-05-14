"""Common student-model interface for TeachQuiz-T."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass
class StudentAnswer:
    choice: str
    raw: str
    confidence: float | None = None


class StudentModel(Protocol):
    name: str

    def answer(
        self,
        *,
        question: str,
        choices: list[str],
        frames: list[Image.Image] | None = None,
        transcript: str | None = None,
    ) -> StudentAnswer:
        """Return the selected option label A-D."""
