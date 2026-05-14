"""Conceptual Correctness dim.

Inspired by RISE-Video's Reasoning Alignment prompt: judge must
(a) restate the discipline-specific concept the video should depict,
(b) cite frames as evidence,
(c) emit a binary verdict + 1-5 score + reasoning.

Output JSON:
    {"binary": "PASS"|"FAIL", "score": int(1..5), "reasoning": str, "evidence": list[str]}
"""

from __future__ import annotations

import json
from typing import Any

from eval.judges.gpt55 import chat
from eval.frame_extractor import frames_as_multimodal_content


SYSTEM_PROMPT = """You are an expert subject-matter judge evaluating whether \
a short generated educational video correctly depicts a target concept.

You will be shown:
- the original text prompt that was given to the video generator,
- a list of "expected concepts" the video must convey,
- a list of "expected visual elements" that should appear,
- a discipline-specific rubric of yes/no checks,
- 8 evenly-spaced frames sampled from the generated video.

Procedure (think step-by-step but only write the final JSON):
1. Restate the central concept the video is supposed to teach.
2. For each rubric check, decide whether the frames provide visual evidence \
that satisfies it. Cite the frame index(es) (1..8) that support your verdict.
3. Score 1..5 where 1=concept entirely wrong/absent, 3=partial/ambiguous, 5=fully correct \
and unambiguous.
4. Mark binary verdict: PASS if score>=4 AND every rubric check passes; otherwise FAIL.

Return ONLY a single JSON object on one line with keys: \
"restated_concept", "rubric_results" (list of {check, verdict, evidence_frames}), \
"score", "binary", "reasoning"."""


USER_TEMPLATE = """Discipline: {discipline} / {subdomain}
Task type: {task_type}
Target audience: {audience}

Original prompt given to video generator:
\"\"\"
{prompt_text}
\"\"\"

Expected concepts (must be conveyed):
{expected_concepts}

Expected visual elements (should appear):
{expected_visual_elements}

Discipline-specific rubric checks:
{rubric_checks}

8 frames from the generated video follow. Indices 1..8.
Return JSON only."""


def format_rubric(checks: list[str]) -> str:
    return "\n".join(f"  - [{i+1}] {c}" for i, c in enumerate(checks))


def score(case: dict[str, Any], frames: list) -> dict[str, Any]:
    rubric_str = format_rubric(case["discipline_specific_rubric"])
    concepts_str = "\n".join(f"  - {c}" for c in case["expected_concepts"])
    visuals_str = "\n".join(f"  - {v}" for v in case["expected_visual_elements"])
    user_text = USER_TEMPLATE.format(
        discipline=case["discipline"],
        subdomain=case["subdomain"],
        task_type=case["task_type"],
        audience=case["pedagogical_target_audience"],
        prompt_text=case["prompt_text"],
        expected_concepts=concepts_str,
        expected_visual_elements=visuals_str,
        rubric_checks=rubric_str,
    )

    content = frames_as_multimodal_content(frames, user_text)
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    try:
        out = json.loads(raw)
    except Exception:
        out = {"error": "json_parse_failed", "raw": raw[:500]}
    out.setdefault("score", 0)
    out.setdefault("binary", "FAIL")
    return out
