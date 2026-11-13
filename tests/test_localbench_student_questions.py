import copy
import json

import pytest
from PIL import Image

from localbench.student_questions import protocol as p
from localbench.student_questions import pipeline
from localbench.student import prefix


@pytest.fixture
def context(tmp_path):
    frame = tmp_path/'frame.jpg'
    Image.new('RGB', (24, 24), 'white').save(frame)
    evidence = {'duration_s': 40, 'video_sha256': 'mediahash',
        'frames': [{'id': 'F0', 'path': str(frame), 'time_s': 0}, {'id': 'F1', 'path': str(frame), 'time_s': 35}],
        'transcripts': [{'id': 'T0', 'source_chunk_end_s': 40, 'end_s': 40, 'text': 'FUTURE_ANSWER_SENTINEL'}],
        'valid_audio_intervals': [], 'audio_chunk_ends': [20, 40], 'evidence_errors': []}
    profile = {'id': 'basic', 'description': 'Reads diagrams.', 'known': {'K0': 'Can identify arrows.'}, 'not_assumed': ['A mechanism.']}
    return profile, evidence, prefix(evidence, 10)


def question():
    return {'question': 'Why do the two objects move together?', 'category': 'mechanism',
            'trigger_reason': 'The diagram places the objects on the same path.', 'evidence_ids': ['F0']}


def group():
    return {'members': ['Q1'], 'representative_id': 'Q1', 'reference_status': 'draft',
        'targets': [{'criterion': 'Explain coupling.', 'source_ids': ['TASK'], 'visual_required': True},
                    {'criterion': 'Connect the path to the explanation.', 'source_ids': ['TASK'], 'visual_required': False}]}


def score():
    return {'groups': {'S01': {'status': 'scored', 'score': 5, 'targets': [
        {'status': 'met', 'evidence_ids': ['F0'], 'reason': 'Visible relation.'},
        {'status': 'met', 'evidence_ids': ['F0'], 'reason': 'Visible explanation.'}], 'reason': 'All targets answered.'}}}


def test_questioning_has_no_future_or_reference_input(context):
    profile, evidence, obs = context
    msg = p.question_messages(profile, obs, [])
    assert 'FUTURE_ANSWER_SENTINEL' not in json.dumps(msg)
    assert 'F1' not in json.loads(msg[1]['content'][0]['text'])['prefix']['evidence_ids']
    assert set(json.loads(msg[1]['content'][0]['text'])) == {'profile', 'prefix', 'previous_questions'}
    raw = {'questions': [question()]}
    assert p.validate_questions(raw, obs) == raw
    raw['questions'][0]['evidence_ids'] = ['F1']
    with pytest.raises(ValueError, match='future'):
        p.validate_questions(raw, obs)


def test_repair_cannot_invent_delete_or_rewrite_questions(context):
    raw = {'questions': [question()]}
    p.preserve_questions(raw, copy.deepcopy(raw))
    for changed in [{'questions': []}, {'questions': [{**question(), 'question': 'An easier question?'}]}]:
        with pytest.raises(ValueError, match='preserve'):
            p.preserve_questions(raw, changed)
    assert p.validate_questions({'questions': []}, context[2]) == {'questions': []}


def test_gate_must_cover_each_original_question_without_future_evidence(context):
    obs = context[2]
    qs = {'Q1': question()}
    raw = {'items': {'Q1': {'status': 'eligible', 'reason': 'In-scope why question.', 'evidence_ids': ['F0']}}}
    assert p.validate_gate(raw, qs, obs) == raw
    with pytest.raises(ValueError):
        p.validate_gate({'items': {}}, qs, obs)
    raw['items']['Q1']['evidence_ids'] = ['F1']
    with pytest.raises(ValueError):
        p.validate_gate(raw, qs, obs)


def test_pool_cannot_drop_hard_questions_or_duplicate_members():
    eligible = {'Q1': question(), 'Q2': {**question(), 'question': 'What condition connects them?'}}
    raw = {'groups': [group()]}
    with pytest.raises(ValueError):
        p.validate_pool(raw, eligible, {'TASK': {}})
    raw['groups'].append({**group(), 'members': ['Q2'], 'representative_id': 'Q2'})
    result = p.validate_pool(raw, eligible, {'TASK': {}})
    assert result['S02']['question'] == eligible['Q2']['question']
    raw['groups'][0]['members'].append('Q2')
    with pytest.raises(ValueError):
        p.validate_pool(raw, eligible, {'TASK': {}})


@pytest.mark.parametrize('kind', ['unjustified_low', 'unjustified_full', 'uncertain_low', 'half', 'visual_without_frame'])
def test_specific_scores_require_frozen_target_evidence(context, kind):
    obs = prefix(context[1], 40)
    pool = {'S01': group()}
    raw = score()
    r = raw['groups']['S01']
    if kind == 'unjustified_low':
        r['score'] = 2
    elif kind == 'unjustified_full':
        r['targets'][0]['status'] = 'partial'
    elif kind == 'uncertain_low':
        r['score'] = 1
        r['targets'][0]['status'] = 'unverified'
    elif kind == 'half':
        r['score'] = 3.5
    else:
        r['targets'][0]['evidence_ids'] = ['T0']
    with pytest.raises(ValueError):
        p.validate_assessment(raw, pool, obs)


def test_missing_or_failed_data_never_manufactures_a_low_score(context):
    pool = {'S01': group()}
    raw = score()
    r = raw['groups']['S01']
    r.update(status='unverified', score=None)
    r['targets'][0].update(status='unverified', evidence_ids=[], reason='Sampling cannot resolve it.')
    assert p.validate_assessment(raw, pool, context[2]) == raw
    sessions = [{'status': 'incomplete', 'planned_prefixes': 3, 'prefixes': []}]
    summary = pipeline.assessment_summary(score(), pool, sessions)
    assert summary['specific_score'] is None
    assert summary['mean_among_scored_groups'] == 100


def test_end_to_end_freeze_order_and_no_gate_feedback_to_student(context, tmp_path):
    profile, evidence, obs = context
    case = {'id': 'case', 'prompt_text': 'PRIVATE_GENERATION_INSTRUCTION'}
    pack = {'reference_status': 'draft_not_expert_verified', 'points': {}}
    out = tmp_path/'run'
    class Student:
        def chat(self, messages, **kwargs):
            text = json.dumps(messages)
            assert 'PRIVATE_GENERATION_INSTRUCTION' not in text
            assert 'GATE_FEEDBACK_SENTINEL' not in text
            assert 'FUTURE_ANSWER_SENTINEL' not in text
            return {'questions': [question()]}
    class Reviewer:
        def chat(self, messages, **kwargs):
            data = json.loads(messages[1]['content'][0]['text'])
            if 'prefix' in data:
                assert 'FUTURE_ANSWER_SENTINEL' not in json.dumps(messages)
                return {'items': {k: {'status': 'eligible', 'reason': 'GATE_FEEDBACK_SENTINEL', 'evidence_ids': ['F0']} for k in data['questions']}}
            if 'required_output_template' in data and 'question_groups' in data and 'media' not in data:
                return {'groups': {k: {'status': 'approved', 'reason': 'All question facets preserved.'} for k in data['question_groups']}}
            if 'eligible_questions' in data:
                assert 'media' not in data and 'FUTURE_ANSWER_SENTINEL' not in json.dumps(messages)
                ids = list(data['eligible_questions'])
                return {'groups': [{**group(), 'members': [k], 'representative_id': k} for k in ids]}
            assert (out/'question_pool_frozen.json').exists()
            assert (out/'eligibility_frozen.json').exists()
            return {'groups': {k: score()['groups']['S01'] for k in data['question_groups']}}
    result = pipeline.run(case, [profile], pack, evidence, out, Student(), Reviewer())
    assert result['summary']['specific_score'] == 100
    assert result['summary']['original_questions'] == 3
    assert result['summary']['question_groups'] == 3
    assert (out/'REPORT.md').exists()


def test_partial_perfect_scores_are_only_diagnostics(tmp_path):
    pool = {f'S{i:02d}': {**group(), 'question': f'Question {i}?'} for i in range(14)}
    assessment = {'groups': {k: score()['groups']['S01'] for k in list(pool)[:6]}}
    sessions = [{'status': 'complete', 'planned_prefixes': 3,
                 'prefixes': [{'status': 'complete'}] * 3}]
    summary = pipeline.assessment_summary(assessment, pool, sessions)
    summary.update(original_questions=14, eligible_questions=14)
    assert summary['specific_score'] is None
    assert summary['score_coverage'] == 6/14
    assert summary['unscored_groups'] == 8
    result = {'case_id': 'partial', 'summary': summary, 'question_pool': pool,
              'assessment': assessment, 'sessions': sessions,
              'student_answers': {'summary': {'supported_answer_score': None,
                  'scored_groups': 3, 'groups': 14, 'mean_among_scored_groups': 58.333333}}}
    pipeline.render_report(tmp_path, result, {}, {})
    main, diagnostics = (tmp_path/'REPORT.md').read_text().split('## 条件统计')
    assert '视频Specific完整分：未完成' in main
    assert '学生最终回答完整分：未完成' in main
    assert '100.00' not in main and '58.33' not in main
    assert '| 未完成 | 6/14 | 8 | 100.00 |' in diagnostics
    assert '| 未完成 | 3/14 | 11 | 58.33 |' in diagnostics


def test_provenance_freezes_nested_question_protocol(tmp_path):
    from localbench.provenance import freeze_run
    config = freeze_run(tmp_path/'frozen', {'command': 'question_test'})
    assert 'student_questions/protocol.py' in config['source_hashes']
    assert (tmp_path/'frozen/source_snapshot/student_questions/protocol.py').is_file()


def test_category_is_metadata_and_known_prerequisite_uses_profile_evidence(context):
    profile, _, obs = context
    q = {**question(), 'category': 'terminology'}
    assert p.validate_questions({'questions': [q]}, obs)['questions'][0] == q
    row = {'status': 'prerequisite', 'reason': 'Explicitly declared known.', 'evidence_ids': [], 'prerequisite_ids': ['K0']}
    raw = {'items': {'Q1': row}}
    assert p.validate_gate(raw, {'Q1': q}, obs, profile) == raw
    for ids in ([], ['NOT_ASSUMED'], ['K99']):
        with pytest.raises(ValueError, match='prerequisite'):
            p.validate_gate({'items': {'Q1': {**row, 'prerequisite_ids': ids}}}, {'Q1': q}, obs, profile)


def test_semantic_audit_cannot_silently_drop_question():
    with pytest.raises(ValueError, match='every'):
        p.validate_pool_audit({'groups': {}}, {'S01': group()})


def test_audio_is_physically_cut_at_prefix_boundaries(tmp_path):
    import subprocess
    import wave
    import imageio_ffmpeg
    from localbench.evidence import extract
    video = tmp_path/'test.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'color=c=white:s=64x64:r=12:d=4',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=4',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(video)], check=True)
    packet = extract(video, tmp_path/'evidence', audio_fractions=(.25, .5, .75))
    assert [(a['start_s'], a['end_s']) for a in packet['audio']] == [(0,1),(1,2),(2,3),(3,4)]
    for a in packet['audio']:
        with wave.open(a['path']) as wav:
            assert wav.getnframes()/wav.getframerate() == pytest.approx(1, abs=.001)


def test_transport_normalization_preserves_judgments_and_raw_input():
    raw={'required_output_template':{'groups':{'S01':{'status':'insufficient_references','reason':'No source.'}}}}
    original=copy.deepcopy(raw)
    normalized,receipt=p.normalize_transport(raw,'audit')
    assert raw==original
    assert normalized['groups']['S01']=={'status':'unverified','reason':'No source.'}
    assert len(receipt['actions'])==2
    scored=score()
    assert p.normalize_transport({'required_output_template':scored},'assessment')[0]==scored
    ambiguous={**raw,'extra':'must not discard me'}
    assert p.normalize_transport(ambiguous,'audit')[0]==ambiguous


def test_failed_assessment_batch_does_not_skip_later_groups(context,tmp_path):
    pool={f'S{i:02d}':group() for i in range(1,6)}
    class Reviewer:
        def chat(self,messages,**kwargs):
            data=json.loads(messages[1]['content'][0]['text'])
            if 'S01' in data['question_groups']:
                return {'groups':{}}  # both bounded attempts invalid
            return {'groups':{'S05':score()['groups']['S01']}}
    assessed,errors=pipeline.assess_frozen(pool,{},context[2],{'TASK':{}},tmp_path,Reviewer())
    assert set(assessed['groups'])=={'S05'}
    assert errors[0]['group_ids']==['S01','S02','S03','S04']
    sessions=[{'status':'complete','planned_prefixes':1,'prefixes':[{'status':'complete'}]}]
    assert pipeline.assessment_summary(assessed,pool,sessions)['specific_score'] is None
