import copy

import pytest

from localbench.applicability import VERSION, validate_annotation
from localbench.common import digest, public_case
from localbench.judge import assess_teaching, evaluation_version
from localbench.rubric import DIMENSIONS, validate_scores


def annotation():
    case = {'id': 'fixture', 'prompt_text': 'Explain the concept, check the result. Do not add unrelated material.'}
    raw = {'version': VERSION, 'case_id': case['id'], 'public_input_hash': digest(public_case(case)),
           'public_source_sha256': None, 'review_status': 'editorial_reviewed', 'expert_verified': False,
           'criteria': {
               'task_completeness.verification': {'applicable': True, 'prompt_quotes': ['check the result'],
                                                  'reason': 'Public task explicitly asks for a check.'},
               'task_completeness.constraints': {'applicable': True, 'prompt_quotes': ['Do not add unrelated material.'],
                                                 'reason': 'Explicit prohibition.'}}}
    return case, raw


def ratings():
    return {'dimensions': {'task_completeness': {'criteria': {
        k: {'status': 'observed', 'score': 3, 'evidence_ids': ['F00'], 'reason': 'Check has an explanatory gap.',
            'severity': 'moderate', 'limitation': 'Check does not fully explain the comparison.', 'high_score_evidence': ''}
        for k in DIMENSIONS['task_completeness']['criteria']}}}}


@pytest.mark.parametrize('mutation', ['prompt', 'quote', 'missing', 'type'])
def test_annotation_rejects_stale_or_untraceable_decisions(mutation):
    case, a = annotation()
    assert validate_annotation(a, case) == a
    if mutation == 'prompt': case['prompt_text'] += ' Changed.'
    if mutation == 'quote': a['criteria']['task_completeness.verification']['prompt_quotes'] = ['fabricated quote']
    if mutation == 'missing': a['criteria'].pop('task_completeness.constraints')
    if mutation == 'type': a['criteria']['task_completeness.verification']['applicable'] = 1
    with pytest.raises(ValueError): validate_annotation(a, case)


def test_required_check_cannot_disappear_and_insufficient_evidence_remains_null():
    _, a = annotation(); raw = ratings()
    item = raw['dimensions']['task_completeness']['criteria']['verification']
    item.update(status='not_applicable', score=None)
    original = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='frozen public-task applicability'):
        validate_scores(raw, {'F00'}, ['task_completeness'], strict=True, applicability=a)
    assert raw == original
    item.update(status='unverified')
    result = validate_scores(raw, {'F00'}, ['task_completeness'], strict=True, applicability=a)['task_completeness']
    assert result['score'] is None and result['applicable_criteria_count'] == 6


def test_excluded_check_cannot_receive_free_credit():
    _, a = annotation(); raw = ratings()
    a['criteria']['task_completeness.verification']['applicable'] = False
    with pytest.raises(ValueError, match='frozen public-task applicability'):
        validate_scores(raw, {'F00'}, ['task_completeness'], strict=True, applicability=a)
    raw['dimensions']['task_completeness']['criteria']['verification'].update(status='not_applicable', score=None)
    result = validate_scores(raw, {'F00'}, ['task_completeness'], strict=True, applicability=a)['task_completeness']
    assert result['applicable_criteria_count'] == 5 and result['score'] == 50


def test_applicability_drift_triggers_bounded_repair_not_automatic_score_edit(tmp_path):
    _, a = annotation(); bad = ratings()
    bad['dimensions']['task_completeness']['criteria']['verification'].update(status='not_applicable', score=None)
    class Client:
        calls = 0
        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1: return bad
            assert 'frozen public-task applicability' in messages[-1]['content']
            return ratings()
    c = Client(); errors = []
    result, _, _ = assess_teaching(c, [], ['task_completeness'], {'F00'}, {'F00'}, 'fixture', tmp_path,
                                  errors, applicability=a)
    assert c.calls == 2 and not errors
    assert result['task_completeness']['applicable_criteria_count'] == 6
    assert bad['dimensions']['task_completeness']['criteria']['verification']['score'] is None
    assert evaluation_version().endswith('integer-r5')
    assert evaluation_version(applicability=a).endswith('integer-r5+applicability-v1')
