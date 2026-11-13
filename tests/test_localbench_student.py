import copy
import json
from pathlib import Path

from PIL import Image
import pytest

from localbench import student
from localbench import student_perception as perception
from localbench.common import write_json
from localbench.delivery import build_report
from localbench.provenance import file_hash
from localbench.services import Service
from localbench.student_run import settings_from, public_settings, run_stage


@pytest.fixture
def profile():
    return {'id': 'beginner', 'description': 'English-reading learner',
            'known': {'K0': 'integer arithmetic'}, 'not_assumed': ['algebraic conventions']}


@pytest.fixture
def evidence(tmp_path):
    path = tmp_path/'frame.jpg'
    Image.new('RGB', (10, 10)).save(path)
    return {'duration_s': 30, 'video_sha256': 'video',
            'frames': [{'id': f'F{i}', 'time_s': t, 'path': str(path)} for i, t in enumerate([0, 10, 20, 29])],
            'transcripts': [
                {'id': 'T0', 'start_s': 1, 'end_s': 9, 'source_chunk_end_s': 10, 'text': 'VISIBLE'},
                {'id': 'T1', 'start_s': 11, 'end_s': 12, 'source_chunk_end_s': 20, 'text': 'FUTURE_ASR_CONTEXT'},
                {'id': 'T2', 'start_s': 25, 'end_s': 29, 'source_chunk_end_s': 30, 'text': 'FUTURE_SOLUTION'}],
            'audio_chunk_ends': [10, 20, 30], 'valid_audio_intervals': [
                {'start_s': 0, 'end_s': 10}, {'start_s': 10, 'end_s': 20}, {'start_s': 20, 'end_s': 30}],
            'evidence_errors': []}


def answer():
    return {'understandings': [{'claim': 'An equation appears.', 'evidence_ids': ['F0']}],
            'questions': [{'question': 'What does x stand for?', 'evidence_ids': ['F0']}],
            'prerequisite_used': ['K0'], 'state_update': 'I noticed the unknown.'}


def review():
    return {'understandings': [{'index': 0, 'status': 'supported', 'evidence_ids': ['F0'], 'reason': 'Visible equation'}],
            'questions': [{'index': 0, 'status': 'video_gap', 'evidence_ids': ['F0'],
                           'rubric_targets': ['pedagogical_clarity.grounding'], 'reason': 'Symbol not grounded in the cited state'}],
            'profile_consistency': {'status': 'consistent', 'reason': 'Uses arithmetic only'}}


def test_prefix_filters_future_frames_and_complete_asr_chunks(profile, evidence):
    p = student.prefix(evidence, 15)
    assert p['evidence_ids'] == ['F0', 'F1', 'T0']
    case = {'id': 'a', 'prompt_text': 'Explain equality', 'expected_answer': 'HIDDEN_ANSWER',
            'rubric': 'HIDDEN_RUBRIC', 'generation_code': 'HIDDEN_CODE'}
    encoded = json.dumps(student.messages(case, profile, p, None))
    assert 'VISIBLE' in encoded
    for forbidden in ['FUTURE_ASR_CONTEXT', 'FUTURE_SOLUTION', 'HIDDEN_ANSWER', 'HIDDEN_RUBRIC', 'HIDDEN_CODE']:
        assert forbidden not in encoded
    assert p['audio_transcript_intervals'] == [{'start_s': 0, 'end_s': 10}]
    assert 'artificial' in p['transcript_boundary_notice']
    assert student.checkpoint_times(evidence) == [10, 20, 30]


def test_invalid_evidence_prerequisites_and_review_rejected(profile, evidence):
    p = student.prefix(evidence, 10)
    raw = answer()
    student.validate_response(raw, profile, p)
    raw['understandings'][0]['evidence_ids'] = ['T2']
    with pytest.raises(ValueError, match='future evidence'): student.validate_response(raw, profile, p)
    raw = answer(); raw['prerequisite_used'] = ['expert_solution']
    with pytest.raises(ValueError, match='prerequisite'): student.validate_response(raw, profile, p)
    r = review(); r['understandings'] = []
    with pytest.raises(ValueError, match='expected 1 entries.*received 0'): student.validate_review(r, answer(), p)
    r = review(); r['questions'][0]['rubric_targets'] = []
    with pytest.raises(ValueError, match='requires'): student.validate_review(r, answer(), p)
    r = review(); r['questions'][0]['status'] = 'pending_instruction'
    with pytest.raises(ValueError, match='final video'): student.validate_review(r, answer(), student.prefix(evidence, 30))
    r = review(); r['questions'][0]['status'] = 'simulator_error'; del r['questions'][0]['rubric_targets']
    assert student.validate_review(r, answer(), p)['questions'][0]['rubric_targets'] == []


def test_empty_pending_review_citation_reports_exact_field_without_relaxation(evidence):
    raw = review()
    raw['questions'][0].update(status='pending_instruction', evidence_ids=[])
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match=r'review questions\[0\].evidence_ids: missing evidence.*nonempty'):
        student.validate_review(raw, answer(), student.prefix(evidence, 10))
    assert raw == before


def test_future_citation_feedback_names_item_and_invalid_id(profile, evidence):
    raw = answer(); raw['questions'][0]['evidence_ids'] = ['T2']
    with pytest.raises(ValueError, match=r'student questions\[0\].evidence_ids: unknown or future.*T2'):
        student.validate_response(raw, profile, student.prefix(evidence, 10))


@pytest.mark.parametrize('key', ['understandings', 'questions'])
def test_review_coverage_feedback_preserves_original_items_and_reports_excess(key, evidence):
    response = answer()
    response[key] *= 4
    before = copy.deepcopy(response)
    raw = review()
    raw[key] = [{**raw[key][0], 'index': i} for i in range(6)]
    with pytest.raises(ValueError, match=r'expected 4 entries with indices \[0, 1, 2, 3\], received 6'):
        student.validate_review(raw, response, student.prefix(evidence, 10))
    assert response == before
    assert len(raw[key]) == 6  # A bad review must not be silently trimmed to pass.


@pytest.mark.parametrize('indices', [[0, 0], [0, True], [0, '1'], [0, 2]])
def test_review_feedback_identifies_invalid_indices_without_accepting_them(indices, evidence):
    response = answer()
    response['understandings'] *= 2
    raw = review()
    raw['understandings'] = [{**raw['understandings'][0], 'index': i} for i in indices]
    with pytest.raises(ValueError, match=r'expected each integer index in \[0, 1\] exactly once, received'):
        student.validate_review(raw, response, student.prefix(evidence, 10))


def test_reviewer_feedback_does_not_enter_learner_state(profile, evidence, tmp_path):
    calls = []
    class Learner:
        def chat(self, messages, **kwargs):
            calls.append(json.dumps(messages)); return answer()
    class Reviewer:
        def chat(self, messages, **kwargs):
            r = review(); r['profile_consistency']['reason'] = 'REVIEWER_ONLY_SECRET'; return r
    session = student.run_session({'id': 'a'}, profile, evidence, tmp_path, Learner(), Reviewer())
    assert session['status'] == 'complete'
    assert len(calls) == 3 and all('REVIEWER_ONLY_SECRET' not in x for x in calls)
    assert 'I noticed the unknown.' in calls[-1]
    assert 'FUTURE_SOLUTION' not in calls[0] and 'FUTURE_SOLUTION' in calls[-1]
    # Independent profile sessions restart with no prior student state.
    student.run_session({'id': 'a'}, {**profile, 'id': 'other'}, evidence, tmp_path/'other', Learner(), Reviewer())
    payload = json.loads(json.loads(calls[3])[1]['content'][0]['text'])
    assert payload['prior_student_state'] is None


def test_incomplete_session_is_not_zero_or_success(profile, evidence, tmp_path):
    class Broken:
        def chat(self, *args, **kwargs): raise ValueError('transport failed')
    s = student.run_session({'id': 'a'}, profile, evidence, tmp_path, Broken(), Broken())
    assert s['status'] == 'incomplete' and len(s['checkpoints']) == 1 and s['planned_checkpoints'] == 3
    m = student.metrics([s], 2)
    assert m['profile_coverage'] == 0 and m['final_video_gap_reports'] is None
    assert m['supported_claim_rate_among_assessed'] is None and m['score'] is None


def test_schema_repair_keeps_raw_and_does_not_add_future_evidence(profile, evidence, tmp_path):
    observation = student.prefix(evidence,10)
    case = {'id':'a','prompt_text':'Explain equality','expected_answer':'HIDDEN_REFERENCE'}
    original = answer(); original['understandings'] *= 5
    class Learner:
        calls = 0
        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:return original
            encoded = json.dumps(messages)
            assert 'invalid student response count' in encoded
            assert 'FUTURE_SOLUTION' not in encoded and 'HIDDEN_REFERENCE' not in encoded
            return answer()
    client = Learner()
    response = student.request_validated(client, student.messages(case,profile,observation,None),
        lambda r:student.validate_response(r,profile,observation),tmp_path,'student','fixture',1800)
    assert client.calls == 2 and response == answer()
    assert len(json.loads((tmp_path/'student_raw.json').read_text())['understandings']) == 5
    assert json.loads((tmp_path/'student_repaired_raw.json').read_text()) == answer()


def test_schema_repair_is_bounded_and_cannot_validate_future_citations(profile, evidence, tmp_path):
    observation = student.prefix(evidence,10)
    raw = answer(); raw['understandings'][0]['evidence_ids']=['T2']
    class Broken:
        calls = 0
        def chat(self,*args,**kwargs):self.calls+=1;return copy.deepcopy(raw)
    client=Broken()
    with pytest.raises(ValueError,match='future evidence'):
        student.request_validated(client,[],lambda r:student.validate_response(r,profile,observation),
                                  tmp_path,'student','fixture',1800)
    assert client.calls==2
    assert [r['status'] for r in json.loads((tmp_path/'student_schema_reviews.json').read_text())]==['invalid','invalid']


def test_transcript_provenance_and_relative_chunk_offsets(tmp_path, monkeypatch):
    source = tmp_path/'old'; (source/'evidence').mkdir(parents=True)
    audio = source/'evidence/audio.wav'; audio.write_bytes(b'wave')
    record = {'id': 'A1', 'path': '/linux/old/audio.wav', 'sha256': file_hash(audio), 'start_s': 10, 'end_s': 20}
    packet = {'video_sha256': 'v', 'metadata': {'duration': 30}, 'frames': [], 'audio': [record]}
    monkeypatch.setattr(student, 'extract', lambda *args: packet)
    write_json(source/'evidence/packet.json', packet)
    transcript = {**record, 'transcript_valid': True, 'timing_valid': True,
                  'utterances': [{'start_s': 2, 'end_s': 5, 'text': 'actual words'}],
                  'criteria': {'do_not_leak': 'EXPERT_SCORE_SECRET'}}
    write_json(source/'actual_audio.json', [transcript])
    result = student.prepare_evidence('unused', source, tmp_path/'new')
    assert result['transcripts'][0]['start_s'] == 12 and result['transcripts'][0]['end_s'] == 15
    assert result['transcripts'][0]['source_chunk_start_s'] == 10
    assert result['transcripts'][0]['near_artificial_end'] is False
    assert 'EXPERT_SCORE_SECRET' not in json.dumps(result)
    audio.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='audio hash'): student.prepare_evidence('unused', source, tmp_path/'new2')
    packet['video_sha256'] = 'different'
    with pytest.raises(ValueError, match='video hash'): student.prepare_evidence('unused', source, tmp_path/'new2')


def test_report_adds_third_block_without_changing_expert_scores(tmp_path):
    cases = [{'id': 'a'}, {'id': 'b'}]
    scores = [{'case_id': 'a', 'scoring': {'overall': 80, 'groups': {'video': 90, 'teaching': 70}}}]
    learners = [{'case_id': 'a', 'status': 'complete', 'metrics': {'planned_profiles': 2, 'complete_profiles': 2,
                 'profile_coverage': 1, 'final_video_gap_reports': 3, 'supported_claim_rate_among_assessed': .5,
                 'understanding_verdicts': {'supported': 2, 'contradicted': 2, 'unverified': 5}}},
                {'case_id': 'b', 'status': 'no_video', 'metrics': {'planned_profiles': 2, 'complete_profiles': 0}}]
    summary = build_report(tmp_path, cases, [], scores, students=learners)
    assert summary['mean_overall_among_valid'] == 80 and summary['all_cases_mean'] is None
    assert summary['student_evaluation']['planned_profiles'] == 4
    assert summary['student_evaluation']['profile_coverage'] == .5
    assert summary['student_evaluation']['score'] is None
    assert summary['cases'][1]['student_final_gap_reports'] is None
    assert summary['cases'][0]['student_unverified_claims'] == 5
    assert summary['cases'][1]['student_supported_claims'] is None
    report = (tmp_path/'REPORT.md').read_text()
    assert '2/2/5 | 50%' in report and '100%不等于满分' in report


def test_profiles_are_explicit_and_separate_reviewer_required(tmp_path, profile, monkeypatch):
    monkeypatch.delenv('VIDEO_TEACHER_API_KEY', raising=False)
    write_json(tmp_path/'profiles.json', {'a': [profile]})
    base = Service('judge', 'https://example.test/v1', 'secret')
    cfg = {'student_evaluation': {'student': {'model': 'small'}, 'profiles': 'profiles.json'}}
    settings = settings_from(cfg, base, tmp_path)
    assert 'secret' not in json.dumps(public_settings(settings, [{'id': 'a'}]))
    with pytest.raises(ValueError, match='missing frozen'): public_settings(settings, [{'id': 'b'}])
    cfg['student_evaluation']['student']['model'] = 'judge'
    with pytest.raises(ValueError, match='separate reviewer'): settings_from(cfg, base, tmp_path)


def test_stage_resume_and_tamper_preserve_prior(tmp_path, profile, monkeypatch):
    import localbench.student_run as runner
    video = tmp_path/'v.mp4'; video.write_bytes(b'video')
    artifact = {'complete': True, 'video_path': str(video), 'sha256': file_hash(video)}
    settings = {'student': Service('small', 'https://a.test/v1', 'x'),
                'reviewer': Service('judge', 'https://a.test/v1', 'x'), 'profiles': {'a': [profile]}}
    class Pool:
        def client(self, service): return service
    calls = []
    def fake(video, case, out, learner, reviewer, profiles, **kwargs):
        from localbench.common import digest, public_case
        calls.append(case['id'])
        return {'case_id': 'a', 'version': student.VERSION, 'video_sha256': file_hash(video),
                'public_case_hash': digest(public_case(case)), 'profiles_hash': digest(profiles),
                'student_model': learner.model, 'reviewer_model': reviewer.model,
                'status': 'complete', 'sessions': [], 'metrics': {'planned_profiles': 1}}
    monkeypatch.setattr(runner, 'evaluate', fake)
    args = (tmp_path/'out', [{'id': 'a'}], [{'id': 'a', 'artifacts': [artifact]}], Pool(), settings)
    first = run_stage(*args)
    saved = tmp_path/'out/student/a/student.json'; before = saved.read_bytes()
    assert run_stage(*args, resume=True) == first and calls == ['a']
    video.write_bytes(b'changed')
    assert run_stage(*args, resume=True)[0]['status'] == 'student_evaluation_error'
    assert saved.read_bytes() == before


def notebook_row(frame_id):
    return {'frame_id': frame_id, 'visible_facts': ['Two separate circles.'],
            'text_claims': ['A straight angle'], 'uncertainty': 'Angles are not measurable here.'}


def make_notebook(evidence):
    seen = set(); batches = []
    for cutoff in student.checkpoint_times(evidence):
        frames = [f for f in evidence['frames'] if f['time_s'] <= cutoff and f['id'] not in seen]
        seen.update(f['id'] for f in frames)
        batches.append({'cutoff_s': cutoff, 'status': 'complete',
                        'observations': [notebook_row(f['id']) for f in frames]})
    return {'version': perception.VERSION, 'batches': batches}


def test_observer_has_only_frames_and_batches_preserve_prefix(evidence, tmp_path, monkeypatch):
    def image_parts(frame):
        return [{'type': 'text', 'text': frame['id']},
                {'type': 'image_url', 'image_url': {'url': 'data:image/mock;'+frame['id']}}]
    monkeypatch.setattr(perception, 'image_content', image_parts)
    evidence['task'] = 'HIDDEN_TASK'; evidence['profile'] = 'HIDDEN_PROFILE'
    calls = []
    class Observer:
        def chat(self, messages, **kwargs):
            encoded = json.dumps(messages)
            for forbidden in ['HIDDEN_TASK', 'HIDDEN_PROFILE', 'VISIBLE', 'FUTURE_ASR_CONTEXT', 'FUTURE_SOLUTION']:
                assert forbidden not in encoded
            ids = [r['text'] for r in messages[1]['content'] if r.get('text', '').startswith('F')]
            calls.append(ids)
            return {'observations': [notebook_row(id_) for id_ in ids]}
    notes = perception.build_notebook(evidence, Observer(), tmp_path)
    assert notes['status'] == 'complete'
    assert sorted(calls) == [['F0', 'F1'], ['F2'], ['F3']]
    for cutoff, expected in [(10, ['F0', 'F1']), (20, ['F0', 'F1', 'F2']), (30, ['F0', 'F1', 'F2', 'F3'])]:
        selected = perception.prefix_notes(notes, student.prefix(evidence, cutoff))
        assert [r['frame_id'] for r in selected] == expected


@pytest.mark.parametrize('ids', [['F0'], ['F0', 'F0'], ['F0', 'FUTURE'], ['F0', ['F1']]])
def test_observer_requires_exact_frame_coverage(evidence, ids):
    with pytest.raises(ValueError, match='exactly one'):
        perception.validate_notes({'observations': [notebook_row(x) for x in ids]}, evidence['frames'][:2])


def test_dev4_basis_required_and_legacy_schema_unchanged(profile, evidence):
    obs = student.prefix(evidence, 10); raw = answer()
    with pytest.raises(ValueError, match='learner observation'):
        student.validate_response(raw, profile, obs, protocol=perception.VERSION)
    raw['understandings'][0]['basis'] = 'visual_observation'
    assert student.validate_response(raw, profile, obs, protocol=perception.VERSION) == raw
    with pytest.raises(ValueError, match='learner observation'):
        student.validate_response(raw, profile, obs)
    raw['understandings'][0]['basis'] = 'expert_answer'
    with pytest.raises(ValueError, match='understanding basis'):
        student.validate_response(raw, profile, obs, protocol=perception.VERSION)


def test_missing_perception_stops_session_without_fallback(profile, evidence, tmp_path):
    class NeverCalled:
        def chat(self, *args, **kwargs): raise AssertionError('No API should be reached')
    for i, notebook in enumerate([None, make_notebook(evidence)]):
        if notebook:
            notebook['batches'][0]['status'] = 'error'
        result = student.run_session({'id': 'a'}, profile, evidence, tmp_path/str(i),
                                     NeverCalled(), NeverCalled(), protocol=perception.VERSION, notebook=notebook)
        assert result['status'] == 'incomplete'
        assert result['checkpoints'][0]['status'] == 'perception_error'
        assert student.metrics([result], 1)['final_video_gap_reports'] is None


def test_dev4_reviewer_feedback_and_future_notes_do_not_enter_student(profile, evidence, tmp_path):
    notebook = make_notebook(evidence)
    notebook['batches'][-1]['observations'][0]['visible_facts'] = ['FUTURE_NOTE']
    calls = []
    class Learner:
        def chat(self, messages, **kwargs):
            calls.append(json.dumps(messages))
            response = answer(); response['understandings'][0]['basis'] = 'visual_observation'
            return response
    class Reviewer:
        def chat(self, messages, **kwargs):
            assert 'FALLIBLE MODEL DESCRIPTION' in messages[0]['content']
            result = review(); result['profile_consistency']['reason'] = 'EXPERT_FEEDBACK'
            return result
    result = student.run_session({'id': 'a', 'expected_answer': 'HIDDEN_ANSWER'}, profile, evidence, tmp_path,
                                  Learner(), Reviewer(), protocol=perception.VERSION, notebook=notebook)
    assert result['status'] == 'complete' and len(calls) == 3
    assert all('EXPERT_FEEDBACK' not in r and 'HIDDEN_ANSWER' not in r for r in calls)
    assert 'FUTURE_NOTE' not in calls[0] and 'FUTURE_NOTE' in calls[-1]
    assert 'I noticed the unknown.' in calls[-1]


def test_protocol_resume_mismatch_preserves_prior(tmp_path, profile, monkeypatch):
    import localbench.student_run as runner
    video = tmp_path/'v.mp4'; video.write_bytes(b'video')
    settings = {'student': Service('small', 'https://a.test/v1', 'x'),
                'reviewer': Service('judge', 'https://a.test/v1', 'x'), 'profiles': {'a': [profile]}}
    class Pool:
        def client(self, service): return service
    def fake(video, case, out, learner, reviewer, profiles, **kwargs):
        from localbench.common import digest, public_case
        return {'case_id': 'a', 'version': kwargs['protocol'], 'video_sha256': file_hash(video),
                'public_case_hash': digest(public_case(case)), 'profiles_hash': digest(profiles),
                'student_model': learner.model, 'reviewer_model': reviewer.model, 'status': 'complete'}
    monkeypatch.setattr(runner, 'evaluate', fake)
    artifact = {'complete': True, 'video_path': str(video), 'sha256': file_hash(video)}
    args = (tmp_path/'out', [{'id': 'a'}], [{'id': 'a', 'artifacts': [artifact]}], Pool(), settings)
    run_stage(*args)
    saved = tmp_path/'out/student/a/student.json'; before = saved.read_bytes()
    settings['protocol'] = perception.VERSION
    assert public_settings(settings, [{'id': 'a'}])['version'] == perception.VERSION
    assert run_stage(*args, resume=True)[0]['status'] == 'student_evaluation_error'
    assert saved.read_bytes() == before


def test_dev5_has_one_valid_schema_and_matched_prompts(profile, evidence):
    from localbench.student_protocol import BASELINE,PERCEPTION,EXAMPLE,add_recent_ids
    observation=student.prefix(evidence,10);add_recent_ids(observation,None)
    a=student.messages({'id':'a'},profile,observation,None,protocol=BASELINE)
    b=student.messages({'id':'a'},profile,observation,None,protocol=PERCEPTION)
    assert a==b
    example=copy.deepcopy(EXAMPLE);example['understandings'][0]['evidence_ids']=['F0']
    student.validate_response(example,profile,observation,protocol=BASELINE)
    system=a[0]['content'];assert system.count('"understandings":')==1
    parsed=json.loads(system.split('complete schema example:\n')[1])
    assert parsed==EXAMPLE and parsed['understandings'][0]['basis']=='visual_observation'
    for protocol in (BASELINE,PERCEPTION):
        reviewed=student.messages({'id':'a'},profile,observation,None,response=example,protocol=protocol)
        assert reviewed[0]['content']==student.messages({'id':'a'},profile,observation,None,response=example,protocol=BASELINE)[0]['content']


def test_dev5_requires_recent_evidence_without_leaking_future(evidence,profile):
    from localbench.student_protocol import BASELINE,add_recent_ids
    observation=student.prefix(evidence,20);add_recent_ids(observation,10)
    assert observation['new_evidence_ids']==['F2','T1']
    raw=answer();raw['understandings'][0]['basis']='visual_observation'
    with pytest.raises(ValueError,match='newly available'):
        student.validate_response(raw,profile,observation,protocol=BASELINE)
    raw['understandings'][0]['evidence_ids']=['F2']
    student.validate_response(raw,profile,observation,protocol=BASELINE)
    assert 'FUTURE_SOLUTION' not in json.dumps(student.messages({'id':'a'},profile,observation,None,protocol=BASELINE))


def test_dev5_baseline_runs_without_observer_and_repair_keeps_basis(profile,evidence,tmp_path):
    from localbench.student_protocol import BASELINE
    class Learner:
        calls=0
        def chat(self,messages,**kwargs):
            self.calls+=1
            if self.calls==1:return {}
            if self.calls==2:assert 'basis on EVERY understanding' in messages[-1]['content']
            payload=json.loads(messages[1]['content'][0]['text'])
            assert 'visual_notebook' not in payload['prefix']
            raw=answer();raw['understandings'][0]['basis']='visual_observation'
            raw['understandings'][0]['evidence_ids']=[payload['prefix']['new_evidence_ids'][0]]
            return raw
    class Reviewer:
        def chat(self,*args,**kwargs):return review()
    result=student.run_session({'id':'a'},profile,evidence,tmp_path,Learner(),Reviewer(),protocol=BASELINE)
    assert result['status']=='complete'
