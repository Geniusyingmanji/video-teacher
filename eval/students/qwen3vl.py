"""Qwen3-VL student adapter for TeachQuiz-T.

This adapter expects a local or Hugging Face model path. It is intentionally
lazy-loaded so importing the package does not allocate GPU memory.

Example:
    python -m eval.run_teachquiz \
      --student qwen3vl \
      --student-model-path /home/azureuser/workspace-gzy/models/Qwen3-VL-2B-Instruct ...
"""

from __future__ import annotations

import re
from typing import Any

import torch
from PIL import Image

from eval.students.base import StudentAnswer


CHOICE_RE = re.compile(r"\b([ABCD])\b", re.IGNORECASE)


def parse_choice(text: str) -> str:
    text = text.strip()
    m = CHOICE_RE.search(text)
    if m:
        return m.group(1).upper()
    for ch in "ABCD":
        if text.upper().startswith(ch):
            return ch
    return "A"


class Qwen3VLStudent:
    name = "qwen3vl"

    def __init__(
        self,
        model_path: str,
        *,
        device_map: str = "auto",
        torch_dtype: str = "bfloat16",
        max_new_tokens: int = 16,
    ) -> None:
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        dtype = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
            "auto": "auto",
        }[torch_dtype]
        self.model_path = model_path
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=dtype,
            device_map=device_map,
            trust_remote_code=True,
        )
        self.max_new_tokens = max_new_tokens

    def answer(
        self,
        *,
        question: str,
        choices: list[str],
        frames: list[Image.Image] | None = None,
        transcript: str | None = None,
    ) -> StudentAnswer:
        prompt = build_prompt(question, choices, transcript)
        content: list[dict[str, Any]] = []
        if frames:
            for img in frames:
                content.append({"type": "image", "image": img})
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        image_inputs = frames or None
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        generated_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated)
        ]
        raw = self.processor.batch_decode(
            generated_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return StudentAnswer(choice=parse_choice(raw), raw=raw)


def build_prompt(question: str, choices: list[str], transcript: str | None = None) -> str:
    lines = [
        "Answer this multiple-choice learning quiz.",
        "Choose exactly one option: A, B, C, or D.",
        "Return only the option letter.",
        "",
        f"Question: {question}",
    ]
    for label, choice in zip("ABCD", choices):
        lines.append(f"{label}. {choice}")
    if transcript:
        lines.extend(["", "Transcript from the video:", transcript[:3000]])
    return "\n".join(lines)
