"""Didactic Affordances dim — PhyEduVideo Element Layout inheritance.

Are the teaching-specific visual affordances (labels, arrows, on-screen text,
diagrams, color-coding, callouts) present, correct, and informative?
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are an expert education-design judge evaluating the \
DIDACTIC AFFORDANCES present in a short generated educational video.

Didactic affordances are the visual elements that make a video TEACH rather \
than just depict: labels naming parts, arrows showing direction/causality, \
on-screen text/equations, color-coding distinguishing concepts, callouts \
emphasising key items, axis/scale annotations.

Score 4 sub-axes on 1..5:

- labels_legible: text labels are present where needed and readable
- arrows_meaningful: arrows (if present) indicate genuine direction/cause/flow
- equations_text_correctness: any on-screen formulas/text are correctly \
spelled / not garbled. 1 = gibberish; 5 = correct.
- color_coding: distinct concepts get distinct colors when helpful

Final score = mean. PASS if >= 3.0 (lower bar — many simple scenes lack \
affordances and that's not always wrong).

Return ONLY JSON: \
"labels_legible", "arrows_meaningful", "equations_text_correctness", \
"color_coding", "final_score", "binary", "reasoning", "observed_affordances" (list of strings)."""


USER_TEMPLATE = """Discipline: {discipline}
Expected visual elements:
{visuals}
Original prompt excerpt: {prompt_excerpt}

8 frames follow. Return JSON only."""


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    visuals = "\n".join(f"  - {v}" for v in case.get("expected_visual_elements", []))
    user_text = USER_TEMPLATE.format(
        discipline=case["discipline"],
        visuals=visuals,
        prompt_excerpt=case["prompt_text"][:300],
    )
    content = frames_as_multimodal_content(frames, user_text)
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    try:
        out = json.loads(raw)
    except Exception:
        out = {"error": "json_parse_failed", "raw": raw[:500]}
    out.setdefault("final_score", 0)
    out.setdefault("binary", "FAIL")
    out["score"] = out.get("final_score", 0)
    return out
