"""Narrative Structure dim.

Inherits from PhyEduVideo's Logic Flow but adds explicit step-ordering
verification. Especially important for problem-solving videos where the
worked-example progression is the pedagogy.
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are an expert pedagogy judge evaluating whether \
a short generated video presents its content in a teachable narrative order.

A "teachable" order means: (a) setup/hook first, (b) worked steps in correct \
logical sequence, (c) result/summary at the end. For problem-solving videos, \
each step must visibly follow from the previous.

You will be shown:
- the original prompt,
- the expected narrative order (an ordered list of beats),
- 8 evenly-spaced frames (indices 1..8).

Procedure:
1. For each expected beat, identify the earliest frame that depicts it.
2. Verify the beats appear in the same order as expected (no reversals or skips).
3. Score 1..5 where 1=no narrative structure or reversed order, \
3=partial order with some gaps, 5=full correct order with smooth progression.
4. PASS if score>=4.

Return ONLY a single JSON object with keys: \
"beat_to_frame" (list of {beat, earliest_frame, found}), \
"order_correct", "score", "binary", "reasoning"."""


USER_TEMPLATE = """Discipline: {discipline}
Task type: {task_type}

Original prompt:
\"\"\"
{prompt_text}
\"\"\"

Expected narrative order (the video should hit these beats in this order):
{expected_order}

8 frames follow. Indices 1..8.
Return JSON only."""


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    # v0.2 uses richer narrative_beats [{beat, expected_frame_range}]; fall back to plain list
    beats = case.get("narrative_beats")
    if beats:
        order_str = "\n".join(
            f"  {i+1}. {b['beat']} (expected around frames {b['expected_frame_range'][0]}-{b['expected_frame_range'][1]})"
            for i, b in enumerate(beats)
        )
    else:
        order_str = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(case["expected_narrative_order"]))
    user_text = USER_TEMPLATE.format(
        discipline=case["discipline"],
        task_type=case["task_type"],
        prompt_text=case["prompt_text"],
        expected_order=order_str,
    )
    content = frames_as_multimodal_content(frames, user_text)
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=1536,
        response_format={"type": "json_object"},
    )
    try:
        out = json.loads(raw)
    except Exception:
        out = {"error": "json_parse_failed", "raw": raw[:500]}
    out.setdefault("score", 0)
    out.setdefault("binary", "FAIL")
    return out
