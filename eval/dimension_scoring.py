"""v13: quality decisions derive exclusively from reported dimensions.

Missing evidence is unverified, never a zero. v12 remains reproducible.
"""
import copy
from eval.quality_scoring import criterion_mean, numeric
from eval.benchmark_scoring import VIDEO_AXES, TEACHING_AXES

VERSION = 'video-teacher-quality-v13'


def apply(evaluation, generation=None):
    result = copy.deepcopy(evaluation)
    dimensions = {}
    def add(name, value, source, threshold=60):
        dimensions[name] = {'score': value if numeric(value) else None,
                            'status': 'scored' if numeric(value) else 'unverified',
                            'threshold': threshold, 'source': source}
    for name in VIDEO_AXES + TEACHING_AXES:
        axis = result.get('axes', {}).get(name, {})
        value = criterion_mean(axis) if axis.get('criteria') else axis.get('score')
        if axis.get('valid') is False or axis.get('error'):
            value = None
        add(name, value, 'axes.' + name,
            70 if name in ('conceptual_correctness', 'pedagogical_clarity') else 60)
    presentation = result.get('instructional_presentation', {})
    presentation_score = criterion_mean(presentation) if presentation.get('valid') is True else None
    presentation_evidence = copy.deepcopy(presentation.get('criteria', []))
    layout = (generation or {}).get('strict_diagnostics', {}).get('layout', result.get('render_geometry', {}))
    if type(layout.get('valid')) is bool:
        presentation_evidence.append({'id': 'render_layout', 'score': 5 if layout['valid'] else 1,
                                      'evidence': layout})
        if presentation_score is not None:
            presentation_score = criterion_mean({'criteria': presentation_evidence})
    add('instructional_presentation', presentation_score, 'instructional_presentation.criteria and measured layout')
    dimensions['instructional_presentation']['criteria'] = presentation_evidence
    task = result.get('task_completion', {})
    requirements = task.get('requirements', [])
    coverage = task.get('coverage')
    uncertain = any(r.get('status') == 'uncertain' for r in requirements)
    add('task_completeness', coverage * 100 if task.get('valid') is True and not uncertain
        and type(coverage) in (int, float) and 0 <= coverage <= 1 else None,
        'task_completion.coverage')
    # Duration is measured instruction following, not a hidden acceptance veto.
    duration = result.get('duration_validation', {})
    if generation is not None:
        duration = generation.get('timing', duration)
    adherence = []
    if type(duration.get('valid')) is bool:
        adherence.append({'id': 'duration', 'score': 100 if duration['valid'] else 0,
                          'evidence': duration})
    if generation is not None:
        diagnostics = generation.get('strict_diagnostics', {})
        for key in ('source_preservation', 'teaching_timeline'):
            observed = diagnostics.get(key, {})
            if type(observed.get('valid')) is bool:
                accepted = observed['valid'] and observed.get('pre_encoding', {}).get('valid', True)
                adherence.append({'id': key, 'score': 100 if accepted else 0,
                                  'evidence': observed})
    add('instruction_following', sum(r['score'] for r in adherence) / len(adherence) if adherence else None,
        'measured instruction-following criteria')
    dimensions['instruction_following']['criteria'] = adherence
    required = result.get('narration_required', False)
    if required:
        speech = result.get('narration_review', {})
        add('spoken_teaching', criterion_mean(speech) if speech.get('valid') is True else None,
            'narration_review.criteria')
    availability = []
    if 'generation_missing_or_failed' in result.get('errors', []) or (generation is not None and generation.get('complete') is not True):
        availability.append('video_unavailable')
    if result.get('consistency_review', {}).get('valid') is not True:
        availability.append('unresolved_evidence')
    long_video = result.get('duration_validation', {}).get('duration_seconds', 0) > 5
    if presentation.get('all_windows_reviewed') is False or (long_video and presentation.get('all_windows_reviewed') is not True):
        availability.append('incomplete_video_review')
    if required and result.get('speech_transcript', {}).get('valid') is not True:
        availability.append('speech_evidence_unverified')
    unknown = [name for name, d in dimensions.items() if d['status'] != 'scored']
    if 'video_unavailable' in availability:
        for d in dimensions.values():
            d.update(score=None, status='unavailable_video')
        unknown = list(dimensions)
    teaching = TEACHING_AXES + ('instructional_presentation', 'task_completeness', 'instruction_following')
    groups = {}
    for name, keys in [('video_quality', VIDEO_AXES), ('teaching_quality', teaching)]:
        groups[name] = round(sum(dimensions[k]['score'] for k in keys) / len(keys), 4) if all(dimensions[k]['score'] is not None for k in keys) else None
    weights = {'video_quality': .4, 'teaching_quality': .4, 'spoken_teaching': .2} if required else {'video_quality': .5, 'teaching_quality': .5}
    if required:
        groups['spoken_teaching'] = dimensions['spoken_teaching']['score']
    failures = [name for name, d in dimensions.items() if d['score'] is not None and d['score'] < d['threshold']]
    failures += [name for name in ('video_quality', 'teaching_quality') if groups[name] is not None and groups[name] < 70]
    valid = not unknown and not availability
    score = round(sum(groups[k] * w for k, w in weights.items()), 4) if valid else None
    result['dimensions'] = dimensions
    result['scoring'] = {'valid': valid, 'score': score, 'groups': groups, 'weights': weights,
        'strict_pass': valid and not failures, 'acceptance_failures': failures, 'gates': failures,
        'errors': availability + [name + '_unverified' for name in unknown],
        'evaluation_status': 'unavailable_video' if 'video_unavailable' in availability else 'evaluated' if valid else 'unverified',
        'dimension_failures': failures, 'axis_scores': {k: v['score'] for k, v in dimensions.items()},
        'axis_scores_after_caps': {k: v['score'] for k, v in dimensions.items()},
        'numeric_caps_applied': False, 'ranking_eligible': valid,
        'presentation_score': dimensions['instructional_presentation']['score'],
        'spoken_teaching_score': dimensions.get('spoken_teaching', {}).get('score')}
    result['version'] = VERSION
    result['quality_policy'] = {'version': VERSION, 'acceptance_source': 'reported dimension thresholds and group thresholds only',
        'weights': weights, 'group_threshold': 70, 'unknown_is_zero': False,
        'calibration_status': 'declared policy; human calibration pending'}
    from eval.run_benchmark_v2 import assessment_coverage
    result['assessment_coverage'] = assessment_coverage(result)
    return result


def aggregate(rows):
    from eval.benchmark_scoring import aggregate as legacy_aggregate
    result = legacy_aggregate(rows)
    result.update(version=VERSION, acceptance_source='dimensions', numeric_caps_applied=False)
    result['dimension_summary'] = {}
    for name in sorted({k for row in rows for k in row.get('dimensions', {})}):
        relevant = [row for row in rows if name in row.get('dimensions', {})]
        scored = [row['dimensions'][name] for row in relevant if numeric(row['dimensions'][name].get('score'))]
        result['dimension_summary'][name] = {
            'n_total': len(relevant), 'n_scored': len(scored), 'n_unverified': len(relevant) - len(scored),
            'n_passed': sum(d['score'] >= d['threshold'] for d in scored),
            'mean_scored_only': round(sum(d['score'] for d in scored) / len(scored), 4) if scored else None,
            'failed_ids': [row.get('id') for row in relevant if numeric(row['dimensions'][name].get('score'))
                           and row['dimensions'][name]['score'] < row['dimensions'][name]['threshold']],
            'unverified_ids': [row.get('id') for row in relevant if not numeric(row['dimensions'][name].get('score'))]}
    return result
