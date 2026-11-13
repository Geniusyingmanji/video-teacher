import copy
import json

import pytest
from PIL import Image

from localbench import student
from localbench.student_keyed import VERSION, item_table, validate

PROFILE = {'id': 'basic', 'description': 'Reads English and arrows.',
           'known': {'K0': 'Arrows can indicate direction.'}, 'not_assumed': ['Runoff paths.']}
OBS = {'evidence_ids': ['F0'], 'is_final': True}


def response(count=1):
    return {'understandings': [{'claim': 'Rain reaches land; water follows the river to the sea.',
                               'evidence_ids': ['F0']} for _ in range(count)],
            'questions': [], 'prerequisite_used': ['K0'], 'state_update': 'I can follow the route.'}


def review(source):
    return {'items': {key: {'status': 'unverified', 'evidence_ids': ['F0'],
                            'reason': 'The static fixture cannot establish the whole path.'}
                      for key in item_table(source)},
            'profile_consistency': {'status': 'consistent', 'reason': 'Uses declared arrow knowledge.'}}


def test_compound_claim_is_one_item_and_exact_duplicate_text_keeps_distinct_ids():
    source = response(5)
    assert list(item_table(source)) == ['U0', 'U1', 'U2', 'U3', 'U4']
    result = validate(review(source), source, OBS)
    assert [r['index'] for r in result['understandings']] == list(range(5))
    assert all(r['status'] == 'unverified' for r in result['understandings'])
    assert student.validate_response(source, PROFILE, OBS, protocol=VERSION) == source
    with pytest.raises(ValueError, match='count'):
        student.validate_response(source, PROFILE, OBS)


@pytest.mark.parametrize('kind', ['split', 'missing', 'rewritten'])
def test_reviewer_cannot_split_drop_or_rewrite_original_item(kind):
    source = response()
    raw = review(source)
    if kind == 'split':
        raw['items']['U1'] = copy.deepcopy(raw['items']['U0'])
    elif kind == 'missing':
        raw['items'] = {}
    else:
        raw['items']['U0']['claim'] = 'A replacement observation'
    with pytest.raises(ValueError):
        validate(raw, source, OBS)


def test_keyed_reviews_keep_future_evidence_and_final_question_guards():
    source = response()
    raw = review(source)
    raw['items']['U0']['evidence_ids'] = ['FUTURE']
    with pytest.raises(ValueError, match='future'):
        validate(raw, source, OBS)
    source['questions'] = [{'question': 'Where does the water go?', 'evidence_ids': ['F0']}]
    raw = review(source)
    raw['items']['Q0'].update(status='pending_instruction', rubric_targets=[])
    with pytest.raises(ValueError, match='final'):
        validate(raw, source, OBS)


def test_nondefect_optional_mapping_does_not_mask_missing_evidence_error():
    source = response()
    source['questions'] = [{'question': 'Will the next topic appear?', 'evidence_ids': ['F0']}]
    raw = review(source)
    raw['items']['Q0']['status'] = 'pending_instruction'
    partial = {**OBS, 'is_final': False}
    result = validate(raw, source, partial)
    assert result['questions'][0]['rubric_targets'] == []
    assert 'rubric_targets' not in raw['items']['Q0']
    raw['items']['Q0']['evidence_ids'] = []
    with pytest.raises(ValueError, match='missing evidence reference'):
        validate(raw, source, partial)
    raw['items']['Q0'].update(status='video_gap', evidence_ids=['F0'])
    with pytest.raises(ValueError, match='rubric'):
        validate(raw, source, partial)


def test_session_preserves_five_original_items_and_uses_fixed_review_ids(tmp_path):
    frame = tmp_path/'frame.jpg'
    Image.new('RGB', (16, 16)).save(frame)
    evidence = {'duration_s': 30, 'frames': [{'id': 'F0', 'time_s': 0, 'path': str(frame)}],
                'transcripts': [{'id': 'T0', 'source_chunk_end_s': 30, 'end_s': 30, 'text': 'FUTURE_ONLY'}],
                'valid_audio_intervals': [], 'audio_chunk_ends': [10, 20, 30], 'evidence_errors': []}
    first = student.prefix(evidence, 10)
    assert student.messages({'id': 'a'}, PROFILE, first, None, protocol=VERSION) == student.messages(
        {'id': 'a'}, PROFILE, first, None)
    class Learner:
        def chat(self, request, **kw):
            return response(5)
    class Reviewer:
        def chat(self, request, **kw):
            data = json.loads(request[1]['content'][0]['text'])
            assert data['required_review_ids'] == ['U0', 'U1', 'U2', 'U3', 'U4']
            assert data['review_items']['U4']['observation'] == response(5)['understandings'][4]
            if not data['prefix']['is_final']:
                assert 'FUTURE_ONLY' not in json.dumps(request)
            assert 'Return JSON:' not in request[0]['content']
            return review(data['student_response'])
    result = student.run_session({'id': 'a'}, PROFILE, evidence, tmp_path/'run', Learner(), Reviewer(), protocol=VERSION)
    assert result['status'] == 'complete'
    for row in result['checkpoints']:
        assert row['response'] == response(5)
        assert len(row['review']['understandings']) == 5
        assert row['response_preservation']['sections']['understandings']['dropped_original_indices'] == []


def test_keyed_session_rejects_lossy_student_format_repair(tmp_path):
    frame = tmp_path/'frame.jpg'
    Image.new('RGB', (16, 16)).save(frame)
    evidence = {'duration_s': 30, 'frames': [{'id': 'F0', 'time_s': 0, 'path': str(frame)}],
                'transcripts': [], 'valid_audio_intervals': [], 'audio_chunk_ends': [30], 'evidence_errors': []}
    class Learner:
        calls = 0
        def chat(self, request, **kw):
            self.calls += 1
            raw = response(5 if self.calls == 1 else 4)
            if self.calls == 1:
                raw['invalid_extra'] = True
            return raw
    class Reviewer:
        def chat(self, *args, **kw):
            raise AssertionError('Lossy response must not reach review')
    learner = Learner()
    result = student.run_session({'id': 'a'}, PROFILE, evidence, tmp_path/'run', learner, Reviewer(), protocol=VERSION)
    assert learner.calls == 2 and result['status'] == 'incomplete'
    assert result['checkpoints'][0]['status'] == 'student_error'
    assert 'dropped' in result['checkpoints'][0]['error']
