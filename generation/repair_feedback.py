"""Bounded repair messages; full evidence stays on disk, task text stays intact."""
from copy import deepcopy
import json


def compact(value, *, depth=0):
    if depth > 7:
        return '[nested evidence retained on disk]'
    if isinstance(value, dict):
        return {k: (deepcopy(v) if k in ('frozen_source_edit_regions', 'gate_failures') else compact(v, depth=depth+1)) for k, v in value.items()
                if k not in {'axes', 'quality_evidence', 'mean_gray_differences',
                             'fraction_pixels_gray_difference_ge16'}}
    if isinstance(value, list):
        return [compact(v, depth=depth+1) for v in value[:8]]
    if isinstance(value, str):
        return value[:1600]
    return value


def bounded_feedback(value, max_chars=12000):
    """Bound supplemental evidence as a whole; full reports remain on disk."""
    value = compact(value)
    result = {}
    priority = ('frozen_source_edit_regions', 'gate_failures', 'generation_error',
                'instruction', 'findings', 'source_plan_validation', 'review_frames')
    for key in dict.fromkeys((*priority, *value)):
        if key not in value:
            continue
        candidate = {**result, key: value[key]}
        if len(json.dumps(candidate, ensure_ascii=False)) <= max_chars:
            result = candidate
        else:
            result[key] = '[full evidence retained on disk]'
    return result


def feedback_for(result, evaluation, frozen=None):
    findings = []
    for axis, data in evaluation.get('axes', {}).items():
        for criterion in data.get('criteria', []):
            if criterion.get('applicable') and (criterion.get('score') or 0) < 4:
                findings.append({'axis': axis, **criterion})
    feedback = {'gate_failures': result.get('quality_gate', {}).get('failures', []),
                'findings': findings[:16],
                'render_diagnostics': compact(result.get('strict_diagnostics', {})),
                'generation_error': result.get('error'),
                'render_failure_logs': compact(result.get('render_failure_logs', [])),
                'evaluation_errors': evaluation.get('errors', []),
                'consistency_review': evaluation.get('consistency_review'),
                'grounded_observations': compact(evaluation.get('grounded_observations', {})),
                'instructional_presentation': compact(evaluation.get('instructional_presentation',{})),
                'task_completion': evaluation.get('task_completion'),
                'spoken_teaching':compact(evaluation.get('narration_review',{})),
                'delivery_pacing':compact(evaluation.get('delivery_pacing',{})),
                'narration_diagnostics':compact(result.get('narration')),
                'source_plan_validation': result.get('source_plan_validation'),
                'instruction': 'Repair all evidenced failures. Preserve the full task and validated target boxes. Expose relevant operations or reasoning; decorative motion and answer-only reveals do not repair weak video value. If source restrictions make substantive demonstration impossible, report that blocker rather than adding unrelated animation.'}
    if frozen is not None:
        feedback['frozen_source_edit_regions'] = deepcopy(frozen)
    return feedback


def validated_frozen(result, previous=None):
    """Never freeze rejected geometry or an unreviewed interpretation of a target."""
    if previous is not None:
        return deepcopy(previous)
    validation = result.get('source_plan_validation', {})
    if validation.get('valid') is True:
        return deepcopy(result.get('source_edit_regions'))
    return None
