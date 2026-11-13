"""Three independent visual/teaching judges with a shared, separately labelled listener."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

from .common import digest, write_json
from .rubric import DIMENSIONS, aggregate_dimensions
from .strict_anchors import OPTIONAL_CRITERIA

VERSION = 'three-judge-integer-median-v1'
DISAGREEMENT_RANGE = 2


def combine_votes(votes, *, allow_na=False):
    """All three must be valid. Large disagreement is pending, never averaged away."""
    rows = copy.deepcopy(votes)
    valid = [v for v in rows if v.get('status') == 'observed'
             and type(v.get('score')) in (int, float) and 1 <= v['score'] <= 5
             and v['score'] == round(v['score'])]
    candidate = int(median(v['score'] for v in valid)) if len(valid) == 3 else None
    spread = max(v['score'] for v in valid)-min(v['score'] for v in valid) if len(valid) == 3 else None
    na = allow_na and len(rows) == 3 and all(v.get('status') == 'not_applicable' and v.get('score') is None for v in rows)
    if na:
        status, reason = 'not_applicable', 'All three judges mark this optional criterion not applicable.'
    elif len(rows) != 3 or len(valid) != 3:
        status, reason = 'unverified', 'Three valid integer ratings are required; missing or applicability disagreement remains unresolved.'
    elif spread >= DISAGREEMENT_RANGE:
        status, reason = 'unverified', 'Judge rating range is at least two levels; inspect the independent evidence before adjudication.'
    else:
        status, reason = 'observed', 'Median of three independent integer ratings; individual reasons and evidence are retained.'
    return {'status': status, 'score': candidate if status == 'observed' else None,
            'candidate_median': candidate, 'range': spread, 'valid_votes': len(valid),
            'reason': reason, 'votes': rows,
            'evidence_ids': sorted({e for v in rows for e in v.get('evidence_ids', [])})}


def criterion_vote(member, name, key):
    result = member['result']
    dimension = result.get('dimensions', {}).get(name, {})
    item = copy.deepcopy(dimension.get('criteria', {}).get(key, {}))
    blocked = dimension.get('evidence_status')
    if dimension.get('score') is None and item.get('status') == 'observed':
        # A null dimension can arise from a sibling unknown criterion. Only
        # invalidate every item when its evidence gate or unexplained null blocks it.
        unknown_sibling = any(c.get('status') == 'unverified' for c in dimension.get('criteria', {}).values())
        if not unknown_sibling:
            blocked = blocked or 'dimension_score_unavailable'
    if blocked or not item or (item.get('status') == 'observed' and
                              (not item.get('evidence_ids') or not item.get('reason'))):
        item = {**item, 'status': 'unverified', 'score': None,
                'reason': blocked or 'Judge failed or returned no validated criterion evidence.'}
    return {'judge_id': member['id'], **item}


def aggregate_panel(case, prepared, members, out, effective_version):
    """Aggregate validated single-judge outputs, preserving every evidence gate."""
    from .judge import audio_dimension
    from .requirements import output_checks
    from .transcript_validity import apply_validity

    if len(members) != 3 or len({m['id'] for m in members}) != 3:
        raise ValueError('aggregation requires three distinct configured judges')
    packet, audio = prepared['packet'], prepared['audio']
    dimensions, pending = {}, []
    for name, definition in DIMENSIONS.items():
        if name == 'audio_quality':
            continue
        criteria = {}
        for key in definition['criteria']:
            combined = combine_votes([criterion_vote(m, name, key) for m in members],
                                     allow_na=name+'.'+key in OPTIONAL_CRITERIA)
            criteria[key] = combined
            if combined['status'] == 'unverified':
                pending.append({'dimension': name, 'criterion': key, **combined})
        applicable = [r for r in criteria.values() if r['status'] != 'not_applicable']
        complete = bool(applicable) and all(r['status'] == 'observed' for r in applicable)
        dimensions[name] = {'criteria': criteria, 'applicable_criteria_count': len(applicable),
                            'score': round((sum(r['score'] for r in applicable)/len(applicable)-1)*25, 3) if complete else None}
    # Three copies of the same listener output must never become three votes.
    dimensions['audio_quality'] = {**audio_dimension(audio),
        'aggregation': 'shared_audio_listener_single_assessment', 'independent_judge_votes': None}
    scoring = aggregate_dimensions(dimensions)
    scoring['version'] = effective_version+'+'+VERSION
    conflicts, errors, verification_checks, member_checks = [], [], [], []
    overall_blockers = []
    for member in members:
        result, id_ = member['result'], member['id']
        conflicts.extend({'judge_id': id_, **c} for c in result.get('verification_conflicts', []))
        errors.extend({**e, 'stage': id_+':'+e['stage']} for e in result.get('stage_errors', []))
        if result.get('error'):
            errors.append({'stage': id_, 'error': result['error'], 'error_type': result.get('error_type', 'JudgeFailure')})
        if result.get('scoring', {}).get('overall') is None:
            overall_blockers.append(id_)
        for check in result.get('critical_verification', {}).get('checks', []):
            verification_checks.append({**check, 'id': id_+':'+check['id'], 'judge_id': id_})
        for check in result.get('output_checks', {}).get('checks', []):
            member_checks.append({**check, 'id': id_+':'+check['id'], 'judge_id': id_})
    if overall_blockers or conflicts:
        scoring['candidate_overall'] = scoring['overall']
        scoring['overall'] = None
        scoring['status'] = 'unresolved_member_evidence'
    result = {'case_id': case['id'], 'case_hash': digest(case), 'video_sha256': packet['video_sha256'],
              'rubric_version': scoring['version'], 'judge_model': 'three-judge-panel',
              'dimensions': dimensions, 'scoring': scoring,
              'evaluation_status': 'panel_scored' if scoring['overall'] is not None else 'panel_incomplete',
              'stage_errors': errors, 'verification_conflicts': conflicts,
              'critical_verification': {'status': 'independent_judge_reviews', 'checks': verification_checks},
              'reference_concerns': [{'judge_id': m['id'], 'concerns': m['result'].get('reference_concerns', [])} for m in members],
              'major_findings': [{'judge_id': m['id'], 'findings': m['result'].get('major_findings', [])} for m in members],
              'evidence_path': str((Path(out)/'evidence/packet.json').resolve()),
              'human_calibration': 'pending',
              'judge_panel': {'version': VERSION, 'expected_judges': 3,
                  'complete_judges': sum(m['result'].get('scoring', {}).get('overall') is not None for m in members),
                  'aggregation': 'criterion_integer_median', 'required_votes': 3,
                  'disagreement_range': DISAGREEMENT_RANGE,
                  'audio_policy': 'one_shared_listener_not_three_independent_votes',
                  'shared_evidence_hash': digest(prepared), 'pending_criteria': len(pending),
                  'blocked_members': overall_blockers,
                  'members': [{k: v for k, v in m.items() if k != 'result'} | {
                      'overall': m['result'].get('scoring', {}).get('overall'),
                      'evaluation_status': m['result'].get('evaluation_status', m['result'].get('status'))} for m in members]}}
    checks = output_checks(result, audio, packet, case)['checks']+member_checks
    failed = [r['id'] for r in checks if r['status'] == 'fail']
    review = [r['id'] for r in checks if r['status'] == 'review']
    unknown = [r['id'] for r in checks if r['status'] == 'unverified']
    if pending:
        review.append('judge_panel_pending_criteria')
        checks.append({'id': 'judge_panel_pending_criteria', 'status': 'review',
                       'reason': f'{len(pending)} criteria require missing-evidence or disagreement review.', 'evidence_ids': []})
    result['output_checks'] = {'checks': checks, 'failed': failed, 'review': review, 'unverified': unknown,
        'status': 'observed_requirement_failure' if failed else 'review_required' if review else 'unverified' if unknown else 'no_failure_detected'}
    result = apply_validity(result, audio)
    write_json(Path(out)/'review_queue.json', {'criteria': pending, 'verification_conflicts': conflicts,
                                            'blocked_members': overall_blockers, 'stage_errors': errors})
    write_json(Path(out)/'scores.json', result)
    return result


def evaluate_panel(video, case, out, members, audio_client, *, transcript_guard=False, applicability=None):
    """members: (JudgeSpec, JudgeClient); no raw scores are fed into another judge."""
    from . import judge
    members = list(members)
    if len(members) != 3 or any(len(set(values)) != 3 for values in (
        [spec.id.casefold() for spec, _ in members],
        [spec.family.casefold() for spec, _ in members],
        [spec.service.model.casefold() for spec, _ in members],
    )):
        raise ValueError('evaluation requires three distinct configured judges')
    out = Path(out)
    version = judge.evaluation_version(transcript_guard=transcript_guard, applicability=applicability)
    prepared = judge.prepare_evidence(video, out, audio_client, transcript_guard=transcript_guard)
    bindings = {'case_id': case['id'], 'case_hash': digest(case),
                'video_sha256': prepared['packet']['video_sha256'], 'rubric_version': version}
    write_json(out/'panel.json', {'version': VERSION, 'members': [spec.public() for spec, _ in members],
                               'shared_evidence_hash': digest(prepared), 'audio_policy': 'shared_single_listener'})
    def one(pair):
        spec, client = pair
        directory = out/'judges'/spec.id
        try:
            result = judge.evaluate(video, case, directory, client, transcript_guard=transcript_guard,
                                    applicability=applicability, prepared_evidence=copy.deepcopy(prepared))
            if any(result.get(k) != v for k, v in bindings.items()):
                raise ValueError('judge result does not match frozen task, media or rubric')
        except Exception as exc:
            error = str(exc).replace(spec.service.api_key, '[redacted]')[:600]
            result = {**bindings, 'evaluation_status': 'judge_error', 'error_type': type(exc).__name__,
                      'error': error, 'dimensions': {}, 'scoring': {'overall': None}}
            write_json(directory/'scores.json', result)
        return {**spec.public(), 'scores_path': str((directory/'scores.json').resolve()), 'result': result}
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = list(workers.map(one, members))
    return aggregate_panel(case, prepared, results, out, version)
