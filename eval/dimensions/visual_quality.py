"""Visual Quality dim.

Inherits from RISE-Video's Visual Quality and VBench primitives.
LMM-judge only here (no DOVER/MANIQA in pilot — add later).
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are a video quality judge. Given 8 frames from a \
generated video, rate four sub-axes on 1..5:

- aesthetic: composition / color balance / overall appeal
- artifacts: 5 = none. 1 = severe AIGC artifacts (warping, melting, \
text gibberish, body distortion, broken geometry).
- temporal_coherence: 5 = subjects and background stay consistent across \
frames. 1 = identity/scene changes randomly.
- resolution_adequacy: 5 = sharp enough to read on-screen text/labels. \
1 = blurry, illegible.

Final score = arithmetic mean of the four sub-axes (1..5).
PASS if final >= 3.5.

Return ONLY a JSON object with keys: \
"aesthetic", "artifacts", "temporal_coherence", "resolution_adequacy", \
"final_score", "binary", "reasoning"."""


USER_TEMPLATE = """Discipline: {discipline} / {subdomain}
8 frames follow (indices 1..8). Return JSON only."""


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    user_text = USER_TEMPLATE.format(
        discipline=case["discipline"], subdomain=case["subdomain"]
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
    # Also normalize 'score' alias for aggregation
    out["score"] = out.get("final_score", 0)
    return out
