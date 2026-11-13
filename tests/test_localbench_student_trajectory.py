import copy
import json

import pytest
from PIL import Image

from localbench.student import prefix
from localbench.student_questions import trajectory as t, pipeline


@pytest.fixture
def context(tmp_path):
    frame = tmp_path/'frame.jpg'
    Image.new('RGB', (24, 24), 'white').save(frame)
    evidence = {'duration_s': 40, 'video_sha256': 'hash',
        'frames': [{'id': 'F0', 'path': str(frame), 'time_s': 0}, {'id': 'F1', 'path': str(frame), 'time_s': 35}],
        'transcripts': [{'id': 'T1', 'source_chunk_end_s': 40, 'end_s': 40, 'text': 'FUTURE_SENTINEL'}],
        'valid_audio_intervals': [], 'evidence_errors': []}
    profile = {'id': 'p', 'description': 'learner', 'known': {'K0': 'arrows'}, 'not_assumed': ['convergence']}
    return profile, evidence


def question():
    return {'question': 'How are the arrows related?', 'category': 'grounding',
            'trigger_reason': 'Two paths are visible.', 'evidence_ids': ['F0']}


def answer():
    return {'resolution': 'resolved', 'explanation': 'The arrows converge.',
            'visual_observation': 'Both arrowheads end at the same point.',
            'narration_claim': 'They converge.', 'uncertainty': '', 'evidence_ids': ['F0']}


def group():
    return {'members': ['Q1'], 'reference_status': 'draft',
            'targets': [{'criterion': 'Describe arrow endpoints.', 'visual_required': True, 'source_ids': ['TASK']}]}


def scored():
    return {'groups': {'S1': {'status': 'scored', 'score': 5, 'reason': 'Endpoints stated.',
            'targets': [{'status': 'met', 'evidence_ids': ['F0'], 'reason': 'Endpoints visible.',
                         'student_quote': answer()['visual_observation']}]}}}


def test_student_projection_and_prefix_isolation(context):
    profile, evidence = context
    msg = t.messages(profile, prefix(evidence, 10),
        {'Q1': {**question(), 'eligibility': 'TEACHER_SECRET', 'targets': ['REFERENCE_SECRET']}},
        {'Q1': {**answer(), 'review': 'REVIEW_SECRET'}})
    text = json.dumps(msg)
    assert all(secret not in text for secret in ('TEACHER_SECRET', 'REFERENCE_SECRET', 'REVIEW_SECRET', 'FUTURE_SENTINEL'))
    raw = {'answers': {'Q1': answer()}}
    assert t.validate(raw, {'Q1': question()}, prefix(evidence, 10)) == raw
    raw['answers']['Q1']['evidence_ids'] = ['F1']
    with pytest.raises(ValueError):
        t.validate(raw, {'Q1': question()}, prefix(evidence, 10))


@pytest.mark.parametrize('fault', ['invented_quote', 'wrong_field', 'missing_final', 'half_score', 'unmet_full'])
def test_review_cannot_substitute_reference_for_student(context, fault):
    raw, responses = scored(), {'Q1': answer()}
    row = raw['groups']['S1']
    if fault == 'invented_quote':
        row['targets'][0]['student_quote'] = 'The northwest component is clear.'
    elif fault == 'wrong_field':
        row['targets'][0]['student_quote'] = answer()['narration_claim']
    elif fault == 'missing_final':
        responses = {}
    elif fault == 'half_score':
        row['score'] = 4.5
    else:
        row['targets'][0]['status'] = 'partial'
    with pytest.raises(ValueError):
        t.validate_review(raw, {'S1': group()}, prefix(context[1], 40), responses)


def test_no_fallback_from_missing_final_to_earlier_answer(context):
    sessions = [{'trajectory': [
        {'cutoff_s': 20, 'is_final': False, 'answers': {'Q1': answer()}},
        {'cutoff_s': 40, 'is_final': True, 'answers': {}}]}]
    final, history = t.final_responses(sessions)
    assert final == {} and len(history['Q1']) == 1
    raw = scored()
    row = raw['groups']['S1']
    row.update(status='unverified', score=None)
    row['targets'][0].update(status='unverified', evidence_ids=[], student_quote='')
    assert t.validate_review(raw, {'S1': group()}, prefix(context[1], 40), final) == raw


def test_failed_answer_batch_preserved_without_skipping_later_batch(context, tmp_path):
    class Student:
        calls = 0
        def chat(self, messages, **kwargs):
            self.calls += 1
            keys = json.loads(messages[1]['content'][0]['text'])['own_questions']
            return {'answers': {}} if 'Q0' in keys else {'answers': {k: answer() for k in keys}}
    student = Student()
    out = t.answer_at(student, context[0], prefix(context[1], 40),
                      {f'Q{i}': question() for i in range(5)}, {}, tmp_path)
    assert student.calls == 2 and out['status'] == 'incomplete'
    assert set(out['answers']) == {'Q4'} and len(out['errors']) == 1


def test_profile_revisits_own_questions_and_never_receives_judge_feedback(context, tmp_path):
    class Student:
        answer_inputs = []
        def chat(self, messages, **kwargs):
            text = json.dumps(messages)
            assert 'JUDGE_SECRET' not in text and 'REFERENCE_SECRET' not in text
            data = json.loads(messages[1]['content'][0]['text'])
            if 'own_questions' in data:
                self.answer_inputs.append(data)
                return {'answers': {k: answer() for k in data['own_questions']}}
            return {'questions': [question()]}
    class Reviewer:
        def chat(self, messages, **kwargs):
            data = json.loads(messages[1]['content'][0]['text'])
            return {'items': {k: {'status': 'eligible', 'reason': 'JUDGE_SECRET',
                        'evidence_ids': ['F0'], 'prerequisite_ids': []} for k in data['questions']}}
    student = Student()
    session = pipeline.run_profile(context[0], context[1], {'TASK': 'REFERENCE_SECRET'},
        tmp_path, student, Reviewer(), (.25, .5, .75), track_answers=True)
    assert session['trajectory_complete']
    assert [r['planned_questions'] for r in session['trajectory']] == [1, 2, 3]
    assert [r['cutoff_s'] for r in session['trajectory']] == [20, 30, 40]
    assert 'FUTURE_SENTINEL' not in json.dumps(student.answer_inputs[:2])
    assert 'FUTURE_SENTINEL' in json.dumps(student.answer_inputs[-1])
    assert student.answer_inputs[1]['own_previous_answers']


def test_incomplete_trajectory_keeps_full_score_null(context, tmp_path):
    class Reviewer:
        def chat(self, messages, **kwargs):
            return scored()
    sessions = [{'trajectory_complete': False, 'trajectory': [
        {'cutoff_s': 40, 'is_final': True, 'answers': {'Q1': answer()}}]}]
    result = t.assess({'S1': group()}, {'Q1': question()}, prefix(context[1], 40),
                      {'TASK': {}}, sessions, tmp_path, Reviewer())
    assert result['summary']['supported_answer_score'] is None
    assert result['summary']['mean_among_scored_groups'] == 100


def test_pool_recovery_keeps_valid_groups_and_marks_invalid_unknown():
    from localbench.student_questions.pool_recovery import recover_batch
    raw = {'groups': [
        {**group(), 'representative_id': 'Q1'},
        {**group(), 'members': ['Q2'], 'representative_id': 'Q2',
         'targets': [{'criterion': 'Unsupported reference.', 'visual_required': False, 'source_ids': ['T00']}]}]}
    before = copy.deepcopy(raw)
    groups, receipt = recover_batch(raw, {'Q1': question(), 'Q2': question()}, {'TASK': {}})
    assert raw == before
    assert groups['S01']['targets'] == raw['groups'][0]['targets']
    assert groups['S02']['reference_status'] == 'insufficient' and groups['S02']['targets'] == []
    assert receipt[1]['original_group']['targets'][0]['source_ids'] == ['T00']
    assert receipt[0]['status'] == 'structurally_retained'


def test_ambiguous_pool_membership_cannot_select_favorable_questions():
    from localbench.student_questions.pool_recovery import recover_batch
    raw = {'groups': [{**group(), 'representative_id': 'Q1'}]}
    groups, _ = recover_batch(raw, {'Q1': question(), 'Q2': question()}, {'TASK': {}})
    assert len(groups) == 2
    assert all(g['reference_status'] == 'insufficient' for g in groups.values())


def test_answer_omission_does_not_require_inventing_a_media_citation(context):
    from localbench.student_questions.protocol import validate_assessment
    raw = scored()
    row = raw['groups']['S1']
    row.update(score=1, reason='The final answer never states the required relation.')
    row['targets'][0].update(status='missing', evidence_ids=[], student_quote='', reason='Absent from the supplied final answer.')
    assert t.validate_review(raw, {'S1': group()}, prefix(context[1], 40), {'Q1': answer()}) == raw
    video_row = copy.deepcopy(raw)
    video_row['groups']['S1']['targets'][0].pop('student_quote')
    with pytest.raises(ValueError, match='nonempty'):
        validate_assessment(video_row, {'S1': group()}, prefix(context[1], 40))


def test_known_unknowns_need_no_model_call(context, tmp_path):
    class Reviewer:
        def chat(self, *args, **kwargs):
            raise AssertionError('Known missing final/reference must not call a model')
    result = t.assess({'S1': group()}, {'Q1': question()}, prefix(context[1], 40),
                      {'TASK': {}}, [{'trajectory_complete': False, 'trajectory': []}], tmp_path, Reviewer())
    assert result['summary']['supported_answer_score'] is None
    assert result['assessment']['groups']['S1']['score'] is None
    assert result['batch_errors'] == []
