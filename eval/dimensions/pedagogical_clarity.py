"""Pedagogical Clarity dim — NEW (one of the 5 strictly-novel rise-teacher dims).

Distinct from Narrative Structure (which checks step ORDER): Clarity asks
"can a learner of the target audience FOLLOW this video?" — pace, visual
chunking, signposting, and whether key items are emphasized.
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are an expert education-design judge evaluating \
whether a short generated video is CLEAR for the intended audience.

Clarity is distinct from correctness (is the content right?) and from \
narrative order (are steps in the right sequence?). Clarity asks: \
"could a learner of the target audience actually follow this video?"

Score 4 sub-axes on 1..5:

- chunking: information is presented in digestible chunks, not all at once. \
1 = chaotic / overcrowded; 5 = well-paced chunks.
- emphasis: key concepts/objects are visually emphasized (highlighting, \
zoom, colour, labels). 1 = nothing emphasized; 5 = key items pop out clearly.
- visual_legibility: lines/objects/labels are big enough to be read at the \
intended audience level. 1 = too small/blurry/cluttered; 5 = legible.
- signposting: visual cues mark transitions or phases (numbers, headings, \
boxes). 1 = no signposting; 5 = clear signposts.

Final score = mean of the 4. PASS if >= 3.5.

Return ONLY JSON: \
"chunking", "emphasis", "visual_legibility", "signposting", "final_score", "binary", "reasoning"."""


USER_TEMPLATE = """Target audience: {audience}
Discipline: {discipline}
Original prompt:
\"\"\"
{prompt_text}
\"\"\"

8 frames follow. Return JSON only."""


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    user_text = USER_TEMPLATE.format(
        audience=case["pedagogical_target_audience"],
        discipline=case["discipline"],
        prompt_text=case["prompt_text"],
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
