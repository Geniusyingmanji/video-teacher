"""Non-compensatory acceptance, separate from the unchanged General weights."""
from __future__ import annotations

from .rubric import DIMENSIONS
from .score_validity import invalid_reasons, valid_score

VERSION = 'teaching-quality-acceptance-v1'


def assess(result):
    failed = []; unknown = []
    invalid=invalid_reasons(result)
    for name in DIMENSIONS:
        score = valid_score(result, name)
        threshold = 70 if name in {'conceptual_correctness', 'task_completeness', 'pedagogical_clarity'} else 60
        if score is None:
            unknown.append(name)
        elif score < threshold:
            failed.append('dimension:' + name)
        dimension = result.get('dimensions', {}).get(name, {})
        for key, item in dimension.get('criteria', {}).items():
            if name not in invalid and item.get('status') == 'observed' and item.get('severity') in {'major', 'critical'}:
                failed.append('critical_criterion:' + name + '.' + key)
        for chunk in dimension.get('chunk_reviews', []):
            for key, item in chunk.get('criteria', {}).items():
                if chunk.get('status') == 'reviewed' and item.get('severity') in {'major', 'critical'}:
                    failed.append('critical_audio:' + chunk['id'] + ':' + key)
    for group in ('video', 'teaching'):
        value = result.get('scoring', {}).get('groups', {}).get(group)
        if value is None:
            unknown.append('group:' + group)
        elif value < 70:
            failed.append('group:' + group)
    if result.get('timeline_review',{}).get('status')!='reviewed':
        unknown.append('timeline_review_incomplete')
    checks = result.get('output_checks')
    if checks is None:
        unknown.append('output_checks_missing')
    else:
        failed.extend('requirement:' + x for x in checks.get('failed', []))
        unknown.extend('requirement:' + x for x in checks.get('review', []) + checks.get('unverified', []))
    for check in result.get('critical_verification', {}).get('checks', []) + result.get('timeline_review', {}).get('checks', []):
        if check.get('verdict') == 'fail' and check.get('severity', 'major') in {'major', 'critical'}:
            failed.append('observed_defect:' + check.get('id', 'unknown'))
    if invalid_reasons(result) or valid_score(result, 'overall') is None:
        unknown.append('incomplete_or_conflicting_evidence')
    status = 'failed' if failed else 'unverified' if unknown else 'passed'
    return {'version': VERSION, 'status': status, 'passed': status == 'passed',
            'failures': sorted(set(failed)), 'unverified': sorted(set(unknown)),
            'policy': {'ordinary_dimension_min': 60, 'critical_teaching_min': 70, 'group_min': 70,
                       'major_or_critical_defect_blocks': True, 'changes_general_score': False},
            'scope': 'Declared development acceptance; not calibrated human teaching effectiveness.'}
