"""Frozen two-level scoring policy for teaching video benchmark v2.

All public scores are 0..100. Missing required evidence invalidates a case;
there is no score floor and no renormalisation after a failed axis.
"""
from __future__ import annotations

import math

VERSION = "video-teacher-2x8-v4"
VIDEO_AXES = ("visual_quality", "temporal_consistency", "signal_quality")
TEACHING_AXES = (
    "conceptual_correctness", "narrative_structure", "pedagogical_clarity",
    "didactic_affordances", "audience_appropriateness",
)
GROUPS = {"video_quality": VIDEO_AXES, "teaching_quality": TEACHING_AXES}
AXIS_THRESHOLD = 60.0
GROUP_THRESHOLD = 70.0
CRITICAL_TEACHING = ("conceptual_correctness", "pedagogical_clarity")


def valid_score(value: object) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and 0 <= value <= 100)


def score_case(axes: dict, *, narration_required: bool = False,
               narration_detected: bool | None = None,
               defects: list[dict] | None = None) -> dict:
    """Compute fixed equal-group score and non-compensatory failure gates."""
    errors = [name for names in GROUPS.values() for name in names
              if not valid_score(axes.get(name))]
    if narration_required and narration_detected is None:
        errors.append("required_audio_probe_unverified")
    if errors:
        return {"valid": False, "score": None, "groups": None,
                "strict_pass": False, "errors": errors}
    defects = defects or []
    capped = {name: axes[name] for names in GROUPS.values() for name in names}
    for defect in defects:
        axis = defect["axis"]
        capped[axis] = min(float(capped[axis]), float(defect["axis_cap"]))
    groups = {group: round(sum(float(capped[a]) for a in names) / len(names), 4)
              for group, names in GROUPS.items()}
    overall = round((groups["video_quality"] + groups["teaching_quality"]) / 2, 4)
    strict = (all(float(capped[a]) >= AXIS_THRESHOLD for a in VIDEO_AXES + TEACHING_AXES)
              and all(v >= GROUP_THRESHOLD for v in groups.values())
              and all(float(capped[a]) >= GROUP_THRESHOLD for a in CRITICAL_TEACHING))
    gates = []
    if defects:
        overall = min(overall, min(float(d["overall_cap"]) for d in defects))
        strict = False
        gates.extend(d["reason"] for d in defects)
    if narration_required and narration_detected is False:
        overall = min(overall, 40.0)
        strict = False
        gates.append("required_audio_signal_absent_score_cap_40")
    return {"valid": True, "score": overall, "groups": groups,
            "axis_scores_after_caps": capped, "strict_pass": strict,
            "errors": [], "gates": gates}


CRITICAL_CRITERIA = {
    "visual_quality": {"artifact_control", "text_stability"},
    "conceptual_correctness": {"core_fact", "symbols", "no_contradiction"},
    "narrative_structure": {"transition", "completion"},
    "temporal_consistency": {"action_completion", "identity"},
    "signal_quality": {"text_rendering", "frame_integrity"},
}


def evidence_defects(axis_results: dict, *, expected_steps: int = 0,
                     freeze_seconds: float = 0.0) -> list[dict]:
    """Turn documented failures into non-compensatory caps.

    A low criterion requires a judge finding; cited frame indices are retained
    when present. The CV freeze trigger is task-aware and separately reported.
    """
    out = []
    for axis, keys in CRITICAL_CRITERIA.items():
        for row in axis_results.get(axis, {}).get("criteria", []):
            if (row.get("id") in keys and row.get("applicable") is True
                    and isinstance(row.get("score"), (int, float))
                    and not isinstance(row["score"], bool) and row["score"] <= 2):
                out.append({"axis": axis, "axis_cap": 40.0, "overall_cap": 50.0,
                            "reason": f"critical_{axis}_{row['id']}",
                            "evidence_frames": row.get("evidence_frames", []),
                            "finding": row.get("finding", "")})
    if expected_steps > 1 and freeze_seconds >= 1.5:
        out.append({"axis": "temporal_consistency", "axis_cap": 50.0,
                    "overall_cap": 60.0, "reason": "requested_multistep_action_frozen",
                    "freeze_seconds": freeze_seconds})
    return out


def aggregate(rows: list[dict]) -> dict:
    """Macro average cases; incomplete cases cannot silently disappear."""
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case IDs")
    valid = [r for r in rows if r.get("scoring", {}).get("valid") is True]
    complete = len(valid) == len(rows) and bool(rows)
    axes = VIDEO_AXES + TEACHING_AXES
    mean = lambda values: round(sum(values) / len(values), 4) if values else None
    return {
        "version": VERSION, "n_total": len(rows), "n_valid": len(valid),
        "n_failed": len(rows) - len(valid), "ranking_publishable": complete,
        "ranking_score": mean([r["scoring"]["score"] for r in valid]) if complete else None,
        "diagnostic_mean_valid_only": mean([r["scoring"]["score"] for r in valid]),
        "strict_pass_rate": mean([float(r["scoring"]["strict_pass"]) for r in valid]) if complete else None,
        "group_means": {g: mean([r["scoring"]["groups"][g] for r in valid]) for g in GROUPS},
        "axis_means": {a: mean([r["scoring"]["axis_scores_after_caps"][a] for r in valid]) for a in axes},
        "failed_ids": [r.get("id") for r in rows if r.get("scoring", {}).get("valid") is not True],
    }
