"""Non-compensatory task, timing, presentation and required speech acceptance."""


def assess(generation, evaluation):
    diagnostics = generation.get('strict_diagnostics', {})
    contract_source = diagnostics.get('source_preservation')
    def supported(axis, keys):
        rows = {row['id']: row for row in evaluation.get('axes', {}).get(axis, {}).get('criteria', [])}
        return all(key in rows and rows[key].get('applicable') is True
                   and type(rows[key].get('score')) in (int, float)
                   and rows[key]['score'] >= 4 and bool(rows[key].get('evidence_frames')) for key in keys)
    checks = {
        'generation': generation.get('complete') is True,
        'strict_duration': generation.get('timing', {}).get('valid') is True,
        'source_preservation': (contract_source is None and not generation.get('source_required')) or (
            contract_source is not None and
            contract_source.get('valid') is True
            and contract_source.get('pre_encoding', {}).get('valid') is True),
        'rubric_valid': evaluation.get('scoring', {}).get('valid') is True,
        ('benchmark_strict_pass' if generation.get('contract_version') in ('strict-five-seconds-v4', 'strict-five-seconds-v5', 'instructional-lesson-contract-v1','instructional-lesson-contract-v2','instructional-lesson-contract-v3') else 'v4_strict_pass'): evaluation.get('scoring', {}).get('strict_pass') is True,
        'task_coverage': supported('conceptual_correctness', ['steps', 'final_state']),
        'correctness': supported('conceptual_correctness', ['core_fact', 'no_contradiction']),
        'readability': supported('pedagogical_clarity', ['readability', 'takeaway']),
        'engagement_report_valid': evaluation.get('supplementary', {}).get(
            'teaching_engagement', {}).get('valid') is True,
    }
    if generation.get('contract_version') in ('strict-five-seconds-v4', 'strict-five-seconds-v5', 'instructional-lesson-contract-v1','instructional-lesson-contract-v2','instructional-lesson-contract-v3'):
        checks['layout'] = diagnostics.get('layout', {}).get('valid') is True
        checks['source_plan'] = not generation.get('source_required') or generation.get('source_plan_validation', {}).get('valid') is True
        checks['consistent_evidence'] = evaluation.get('consistency_review', {}).get('valid') is True
    if generation.get('contract_version') in ('instructional-lesson-contract-v1','instructional-lesson-contract-v2','instructional-lesson-contract-v3'):
        checks['teaching_timeline'] = diagnostics.get('teaching_timeline',{}).get('valid') is True
    version = evaluation.get('version', '')
    if version in tuple(f'video-teacher-2x8-v{number}' for number in range(6, 12)):
        checks['task_completion'] = evaluation.get('task_completion', {}).get('valid') is True and evaluation.get('task_completion', {}).get('passed') is True
    if version in tuple(f'video-teacher-2x8-v{number}' for number in range(7, 12)):
        checks['instructional_presentation'] = evaluation.get('instructional_presentation',{}).get('valid') is True and evaluation.get('instructional_presentation',{}).get('passed') is True
    if generation.get('contract_version') in ('instructional-lesson-contract-v1','instructional-lesson-contract-v2','instructional-lesson-contract-v3'):
        checks['segment_coverage'] = evaluation.get('instructional_presentation',{}).get('all_windows_reviewed') is True
        checks['evaluated_duration'] = evaluation.get('duration_validation',{}).get('valid') is True
    if generation.get('audio_narration_required') is True:
        checks['narration_generated']=(generation.get('narration') or {}).get('valid') is True
        checks['actual_speech']=evaluation.get('speech_transcript',{}).get('valid') is True
        checks['spoken_teaching']=evaluation.get('narration_review',{}).get('valid') is True and evaluation.get('narration_review',{}).get('passed') is True
    # Engagement is reported separately; its numeric score never affects acceptance.
    failures = [name for name, passed in checks.items() if not passed]
    return {'passed': not failures, 'checks': checks, 'failures': failures,
            'quality_evidence': {'axes': evaluation.get('axes', {}),
                                 'defects': evaluation.get('defects', []),
                                 'scoring': evaluation.get('scoring', {})}}
