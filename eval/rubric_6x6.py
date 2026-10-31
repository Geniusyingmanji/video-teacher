"""Evidence-based six-by-six teaching-video rubric.

Each of the six existing dimensions has six observable criteria. The judge
returns criterion evidence before a dimension score is computed in code.
"""

from __future__ import annotations

import json
import math

from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat


RUBRIC: dict[str, tuple[tuple[str, str], ...]] = {
    "conceptual_correctness": (
        ("core_fact", "The central scientific or factual claim is correct."),
        ("relationships", "Causal, spatial, or logical relationships are correct."),
        ("symbols", "Numbers, labels, equations, and units are correct and stable."),
        ("steps", "Shown operations or intermediate states follow valid rules."),
        ("final_state", "The visible result or answer matches the task."),
        ("no_contradiction", "No frame contradicts the intended lesson."),
    ),
    "narrative_structure": (
        ("setup", "The starting state is identifiable."),
        ("target", "The intended change or question is identifiable."),
        ("sequence", "Visible events occur in a comprehensible order."),
        ("transition", "The key transition is actually shown rather than implied."),
        ("completion", "The resulting state is visible long enough to inspect."),
        ("pace", "The number and speed of events fit the clip duration."),
    ),
    "visual_quality": (
        ("legibility", "Essential text and marks are legible at source resolution."),
        ("text_stability", "Existing text does not mutate or become gibberish."),
        ("shape_stability", "Important objects and diagrams keep their identity."),
        ("artifact_control", "No intrusive hands, objects, melting, or glitches."),
        ("composition", "The subject stays framed with usable contrast."),
        ("motion", "Motion is smooth and serves the requested change."),
    ),
    "pedagogical_clarity": (
        ("single_focus", "The clip has one clear learning focus."),
        ("attention", "Visual emphasis directs attention to the important part."),
        ("explanation", "The visual change helps explain the target concept."),
        ("readability", "The viewer has enough time to read essential content."),
        ("ambiguity", "The viewer can distinguish the intended answer from distractors."),
        ("takeaway", "The end state makes the lesson's takeaway clear."),
    ),
    "didactic_affordances": (
        ("observable_change", "A meaningful before-and-after change is visible."),
        ("step_evidence", "A viewer can locate the crucial step or event."),
        ("reference_anchor", "Stable visual anchors support comparison across time."),
        ("alignment", "Highlights or annotations point to the correct objects."),
        ("inspectability", "The result can be paused and checked visually."),
        ("diagnosability", "A wrong answer or step would be observable from the clip."),
    ),
    "audience_appropriateness": (
        ("prerequisites", "The clip fits the stated audience's prior knowledge."),
        ("vocabulary", "Terminology and symbols suit that audience."),
        ("complexity", "The visual load is manageable for that audience."),
        ("speed", "The audience has enough time to follow the change."),
        ("accessibility", "Color, contrast, and scale support reading."),
        ("task_fit", "The chosen representation helps this audience learn the task."),
    ),
}

SYSTEM = """Judge a short educational video from sampled frames. Score each of the six
listed criteria on 1..5 (1 severe failure, 3 partial/uncertain, 5 clear success).
For each criterion return id, applicable (boolean), score (1..5 or null when
inapplicable), evidence_frames (indices 1..N), and one concrete finding. Treat
missing visual evidence as a low score, not as proof of success. Use inapplicable
only when the task genuinely has no such element. Do not invent audio evidence.
Return JSON only: {"criteria": [...], "summary": "..."}."""


def validate_result(dimension: str, raw: dict, frame_count: int) -> dict:
    expected = [criterion_id for criterion_id, _ in RUBRIC[dimension]]
    criteria = raw.get("criteria")
    if not isinstance(criteria, list) or len(criteria) != 6:
        raise ValueError("judge must return exactly six criteria")
    by_id = {row.get("id"): row for row in criteria if isinstance(row, dict)}
    if set(by_id) != set(expected) or len(by_id) != 6:
        raise ValueError("judge criterion IDs do not match rubric")
    scores = []
    ordered = []
    for criterion_id in expected:
        row = by_id[criterion_id]
        applicable = row.get("applicable")
        if not isinstance(applicable, bool):
            raise ValueError(f"{criterion_id}: applicable must be boolean")
        score = row.get("score")
        if applicable:
            if (not isinstance(score, (int, float)) or isinstance(score, bool)
                    or not math.isfinite(score) or not 1 <= score <= 5):
                raise ValueError(f"{criterion_id}: invalid score")
            scores.append(float(score))
        elif score is not None:
            raise ValueError(f"{criterion_id}: inapplicable score must be null")
        evidence = row.get("evidence_frames")
        if not isinstance(evidence, list) or any(
            not isinstance(i, int) or isinstance(i, bool) or not 1 <= i <= frame_count
            for i in evidence
        ):
            raise ValueError(f"{criterion_id}: invalid frame evidence")
        if applicable and score >= 3 and not evidence:
            raise ValueError(f"{criterion_id}: positive score needs frame evidence")
        if not isinstance(row.get("finding"), str) or not row["finding"].strip():
            raise ValueError(f"{criterion_id}: missing finding")
        ordered.append(row)
    if len(scores) < 4:
        raise ValueError("fewer than four applicable criteria")
    score = round(sum(scores) / len(scores), 3)
    return {
        "score": score,
        "binary": "PASS" if score >= 4 and min(scores) >= 3 else "FAIL",
        "criteria": ordered,
        "summary": str(raw.get("summary", "")),
        "rubric_version": "6x6-v1",
    }


def score_dimension(dimension: str, case: dict, frames: list) -> dict:
    criteria = "\n".join(f"- {i}: {description}" for i, description in RUBRIC[dimension])
    task = json.dumps({key: case.get(key) for key in (
        "discipline", "subdomain", "task_type", "pedagogical_target_audience",
        "prompt_text", "expected_concepts", "expected_visual_elements",
        "expected_narrative_order", "discipline_specific_rubric",
    )}, ensure_ascii=False)
    content = frames_as_multimodal_content(
        frames, f"Dimension: {dimension}\nTask: {task}\nCriteria:\n{criteria}\n"
                f"Frames are indexed 1..{len(frames)}. Return JSON only.")
    raw = chat([{"role": "system", "content": SYSTEM},
                {"role": "user", "content": content}],
               max_tokens=3500, response_format={"type": "json_object"})
    return validate_result(dimension, json.loads(raw), len(frames))


class RubricDimension:
    def __init__(self, name: str):
        self.name = name

    def score(self, case: dict, frames: list) -> dict:
        return score_dimension(self.name, case, frames)


DIMENSIONS = {name: RubricDimension(name) for name in RUBRIC}
