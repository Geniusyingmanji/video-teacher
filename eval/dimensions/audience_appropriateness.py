"""Audience Appropriateness dim — NEW rise-teacher dimension.

Asks: "Is the video pitched at the right level for its stated audience?"
Distinct from Clarity (can they follow it?) — this asks whether the *content
depth, vocabulary, and assumed prior knowledge* match the target.
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are an expert educational-design judge evaluating \
whether a short generated video is appropriate for its STATED TARGET AUDIENCE.

This is NOT about whether the content is correct (that's Conceptual Correctness) \
or whether it's clear (that's Pedagogical Clarity). You assess whether the \
complexity, vocabulary, assumed prior knowledge, and depth of treatment match \
the stated audience.

Score 4 sub-axes on 1..5:

- depth_match: content depth aligns with audience level. \
  1 = wildly mismatched (graduate content for K-8, or trivially simple for advanced); \
  5 = perfectly calibrated depth.
- vocabulary_match: terminology and language suit the audience. \
  1 = jargon-laden (for beginners) or condescending (for experts); \
  5 = appropriate language register.
- prior_knowledge_assumed: scaffolding is right for the audience's background. \
  1 = assumes far too much or too little; 5 = exactly right.
- engagement_style: visual style, pacing, and tone fit the audience. \
  1 = tone and style completely wrong for audience; 5 = engaging and appropriate.

Final score = mean of the 4. PASS if >= 3.5.

Return ONLY JSON with keys: \
"depth_match", "vocabulary_match", "prior_knowledge_assumed", "engagement_style", \
"final_score", "binary", "reasoning"."""


USER_TEMPLATE = """Target audience: {audience}
Discipline: {discipline}
Subdomain: {subdomain}
Difficulty level: {difficulty}
Original prompt:
\"\"\"
{prompt_text}
\"\"\"

8 frames follow. Assess whether the video content is appropriately pitched \
for the stated audience. Return JSON only."""


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    user_text = USER_TEMPLATE.format(
        audience=case.get("pedagogical_target_audience", "general"),
        discipline=case.get("discipline", ""),
        subdomain=case.get("subdomain", ""),
        difficulty=case.get("difficulty", "medium"),
        prompt_text=case.get("prompt_text", ""),
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
    if "final_score" not in out:
        axes = ["depth_match", "vocabulary_match", "prior_knowledge_assumed", "engagement_style"]
        vals = [float(out[a]) for a in axes if a in out and out[a]]
        out["final_score"] = round(sum(vals) / len(vals), 2) if vals else 0
    out.setdefault("binary", "PASS" if float(out.get("final_score", 0)) >= 3.5 else "FAIL")
    out["score"] = out.get("final_score", 0)
    return out
