import copy

import pytest

from localbench.compare import paired_summary
from localbench.judge import assess_teaching
from localbench.rubric import DIMENSIONS


@pytest.mark.parametrize('repaired', [True, False])
def test_checklist_retries_without_replacing_valid_dimension_scores(tmp_path, repaired):
    name = 'task_completeness'
    rating = {'criteria': {key: {
        'status': 'observed', 'score': 3, 'severity': 'moderate',
        'reason': 'F00 shows a limited demonstration.',
        'limitation': 'An intermediate step is unclear.',
        'high_score_evidence': '', 'evidence_ids': ['F00'],
    } for key in DIMENSIONS[name]['criteria']}}
    original = copy.deepcopy(rating)
    finding = {'requirement_id': 'R01', 'verdict': 'met',
               'evidence_ids': ['F00'], 'reason': 'The requested objects are visible.'}

    class Client:
        calls = 0

        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {'dimensions': {name: rating}}
            assert kwargs['purpose'].startswith('public_requirement_findings_repair:')
            assert 'Do not return or change dimension ratings' in messages[-1]['content']
            return {'requirement_findings': [finding]} if repaired else {}

    client = Client()
    errors = []
    dimensions, _, findings = assess_teaching(
        client, [], [name], {'F00'}, {'F00'}, 'fixture', tmp_path, errors,
        contract={'requirements': [{'id': 'R01'}]},
    )
    assert client.calls == 2
    assert rating == original
    assert dimensions[name]['criteria'] == original['criteria']
    assert dimensions[name]['score'] == (50 if repaired else None)
    assert findings == ([finding] if repaired else [])
    assert len(errors) == (0 if repaired else 1)
    assert (tmp_path / 'raw_requirement_findings_repaired.json').exists()


def pair():
    return [{
        'case_id': 'a', 'mode': mode, 'case_hash': 'same-task',
        'rubric_version': 'same-protocol', 'judge_model': 'same-model',
        'scoring': {'overall': value},
        'dimensions': {name: {'score': value} for name in DIMENSIONS},
    } for mode, value in [('code', 75), ('slides', 50)]]


@pytest.mark.parametrize('field', ['case_hash', 'rubric_version', 'judge_model'])
@pytest.mark.parametrize('value', ['different', None])
def test_pairing_rejects_changed_or_one_sided_identity(field, value):
    rows = pair()
    rows[1][field] = value
    with pytest.raises(ValueError, match=field + ' mismatch'):
        paired_summary(rows)


def test_pairing_reports_legacy_identity_gap_and_keeps_failed_tasks():
    rows = pair()
    result = paired_summary(rows, expected_ids=['a', 'failed'])
    assert result['task_identity_verified_ids'] == ['a']
    assert result['dimensions']['overall']['n_tasks'] == 2
    assert result['dimensions']['overall']['mean_delta'] == 25
    for row in rows:
        del row['case_hash']
    result = paired_summary(rows)
    assert result['task_identity_unverified_ids'] == ['a']
