"""Evidence-backed video-specific axes for benchmark 2x8-v3."""
from __future__ import annotations

import json
from eval.evidence_prompt import prompt_json
import math

from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat
from eval.judges.structured_rubric import judge

RUBRIC = {
    "temporal_consistency": (
        ("identity", "Objects and diagrams preserve identity across frames unless intentionally transformed."),
        ("motion_continuity", "Motion has coherent trajectories without unexplained jumps or reversals."),
        ("state_continuity", "Labels, quantities, and visual states remain consistent between steps."),
        ("transition_integrity", "Scene transitions or cuts do not erase or contradict necessary context."),
        ("action_completion", "The requested visible action progresses and completes rather than freezing prematurely."),
        ("temporal_readability", "Changes and holds give enough time to perceive the intended event."),
    ),
    "signal_quality": (
        ("focus", "Task-relevant content is sharp enough to inspect at native resolution."),
        ("exposure", "Task-relevant content is visible without destructive clipping or darkness; plain backgrounds are acceptable."),
        ("compression", "Compression or generation noise does not obscure essential content."),
        ("text_rendering", "Essential letters, numbers, and symbols are rendered cleanly and stably."),
        ("contrast", "Essential foreground content is distinguishable from its background."),
        ("frame_integrity", "Frames are complete and free from blank, corrupted, or severely degraded intervals."),
    ),
}

SYSTEM = """Use the shared literal grounded_observations to keep values, positions and completion facts consistent across axes. Recheck uncertain facts against frames; do not guess unsupported domain identities. If a consistency_correction is provided, correct the cited factual observation while keeping the original rubric and actual evidence.
Evaluate only the named video-quality axis using the ordered sampled frames.
For each of its six criteria return id, applicable (boolean), score (integer 1..5
or null when inapplicable), evidence_frames (1-based indices), and a concrete
finding. 1=severe failure, 2=clear defect, 3=adequate/uncertain, 4=strong,
5=exceptional with concrete evidence. Mere presence or stable still frames does not
prove completed motion. Inspect identities and intermediate states. Missing requested evidence scores 1 or 2. Do not assume audio.
Avoid penalising intentional static holds, flat diagrams, cuts, or white
backgrounds merely because they are present. Return JSON only with criteria
and summary. Every score >=3 needs at least one cited frame."""


def validate_result(axis: str, raw: dict, frame_count: int) -> dict:
    expected = [key for key, _ in RUBRIC[axis]]
    rows = raw.get("criteria")
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("six criteria required")
    by_id = {r.get("id"): r for r in rows if isinstance(r, dict)}
    if len(by_id) != 6 or set(by_id) != set(expected):
        raise ValueError("incorrect or duplicate criterion IDs")
    ordered, scores = [], []
    for key in expected:
        row = by_id[key]
        applicable = row.get("applicable")
        score = row.get("score")
        evidence = row.get("evidence_frames")
        if not isinstance(applicable, bool):
            raise ValueError(f"{key}: invalid applicability")
        if applicable:
            if (isinstance(score, bool) or not isinstance(score, (int, float)) or not 1 <= score <= 5 or score * 2 != round(score * 2)):
                raise ValueError(f"{key}: invalid score")
            scores.append(score)
        elif score is not None:
            raise ValueError(f"{key}: inapplicable score must be null")
        if (not isinstance(evidence, list) or any(isinstance(i, bool) or not isinstance(i, int)
                or not 1 <= i <= frame_count for i in evidence)):
            raise ValueError(f"{key}: invalid evidence")
        if applicable and score >= 3 and not evidence:
            raise ValueError(f"{key}: positive score needs evidence")
        if not isinstance(row.get("finding"), str) or not row["finding"].strip():
            raise ValueError(f"{key}: missing finding")
        ordered.append(row)
    if len(scores) < 4:
        raise ValueError("too few applicable criteria")
    mean = sum(scores) / len(scores)
    return {"score": round((mean - 1) * 25, 4), "rubric_score_1_to_5": round(mean, 4),
            "criteria": ordered, "summary": str(raw.get("summary", "")),
            "method": "evidence_backed_video_rubric_v2"}


class VideoDimension:
    def __init__(self, name: str):
        self.name = name

    def score(self, case: dict, frames: list) -> dict:
        axis = self.name
        spec = "\n".join(f"- {k}: {description}" for k, description in RUBRIC[axis])
        task = {key: case.get(key) for key in ("prompt_text", "expected_visual_elements",
                                                "expected_narrative_order", "task_type", "grounded_observations", "consistency_correction", "segment_evidence", "actual_duration_s", "target_duration_s")}
        content = frames_as_multimodal_content(
            frames, f"Axis: {axis}\nTask: {prompt_json(task)}\n"
                    f"Criteria:\n{spec}\nFrames: 1..{len(frames)}")
        return judge(chat, [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': content}],
                     [key for key, _ in RUBRIC[axis]], len(frames),
                     lambda raw: validate_result(axis, raw, len(frames)))


DIMENSIONS = {name: VideoDimension(name) for name in RUBRIC}

SYSTEM += """ Use half-point increments (1, 1.5, ..., 5) only.
Anchors: 1 unusable/absent; 2 major defect; 3 adequate with visible limitations;
4 strong with minor defects; 5 exceptional and fully demonstrated. A half point
requires evidence between adjacent anchors, not numerical precision by intuition.
Inspect the supplied segment_evidence and delivery_pacing_evidence before grading.
A clean static final diagram does not establish a successful transition.
Find and describe failures before assigning a rating. Reconcile contrary evidence
from segmented review; do not select only favorable overview frames.
"""
