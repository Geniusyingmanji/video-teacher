import copy
import json
from pathlib import Path
import threading

import pytest

from localbench.common import digest, write_json
from localbench.judge import evaluation_version
from localbench.judge_panel import aggregate_panel, combine_votes, evaluate_panel
from localbench.provenance import file_hash
from localbench.rubric import DIMENSIONS, aggregate_dimensions
from localbench.services import JudgeClient, ServicePool, judge_panel_from


def config():
    return {'generator': {'model': 'generator', 'url': 'https://generator.test/v1', 'api_key': 'GENERATOR_SECRET'},
            'judges': [{'id': 'judge_'+str(i), 'family': 'family_'+str(i), 'model': 'model_'+str(i),
                        'url': f'https://judge{i}.test/v1', 'api_key': 'JUDGE_SECRET_'+str(i)} for i in range(3)],
            'audio_judge': False}


def evidence(video, out):
    packet = {'video_sha256': file_hash(video), 'frames': [{'id': 'F00', 'time_s': 0}],
              'audio': [], 'metadata': {'duration': 60, 'decoded_duration_s': 60}}
    audio = [{'id': 'A00', 'start_s': 0, 'end_s': 60, 'status': 'reviewed', 'transcript': 'Actual spoken words.',
              'transcript_valid': True, 'timing_valid': True,
              'criteria': {k: {'score': 4} for k in DIMENSIONS['audio_quality']['criteria']}}]
    write_json(out/'evidence/packet.json', packet)
    write_json(out/'actual_audio.json', audio)
    return {'packet': packet, 'audio': audio, 'transcript_guard': False}


def result(case, video, score=4):
    dims = {name: {'score': (score-1)*25, 'criteria': {
        key: {'status': 'observed', 'score': score, 'reason': 'A concrete observation.', 'evidence_ids': ['F00']}
        for key in definition['criteria']}} for name, definition in DIMENSIONS.items()}
    return {'case_id': case['id'], 'case_hash': digest(case), 'video_sha256': file_hash(video),
            'rubric_version': evaluation_version(), 'dimensions': dims, 'scoring': aggregate_dimensions(dims),
            'evaluation_status': 'scored_all_dimensions', 'verification_conflicts': [], 'stage_errors': []}


@pytest.mark.parametrize('change', ['count', 'id', 'family', 'model', 'missing_url', 'missing_audio', 'single_and_panel'])
def test_explicit_distinct_panel_configuration(change):
    cfg = config()
    assert len(judge_panel_from(cfg)) == 3
    public = json.dumps([s.public() for s in judge_panel_from(cfg)])
    assert 'SECRET' not in public
    if change == 'count': cfg['judges'].pop()
    elif change in {'id', 'family', 'model'}: cfg['judges'][1][change] = cfg['judges'][0][change]
    elif change == 'missing_url': cfg['judges'][0].pop('url')
    elif change == 'missing_audio': cfg.pop('audio_judge')
    else: cfg['judge'] = {'model': 'another'}
    with pytest.raises(ValueError): judge_panel_from(cfg)


def test_safe_judge_id_and_no_generator_credential_fallback(monkeypatch):
    cfg = config(); cfg['judges'][0]['id'] = '../escape'
    with pytest.raises(ValueError, match='safe identifier'): judge_panel_from(cfg)
    cfg = config(); cfg['judges'][0].pop('api_key')
    monkeypatch.delenv('VIDEO_TEACHER_API_KEY', raising=False)
    with pytest.raises(ValueError): judge_panel_from(cfg)


@pytest.mark.parametrize('scores,expected,candidate', [([3,4,4],4,4), ([1,4,4],None,4), ([4,4,None],None,None)])
def test_item_median_does_not_average_or_hide_missing_and_disagreement(scores, expected, candidate):
    votes = [{'judge_id': str(i), 'status': 'observed' if score else 'unverified', 'score': score,
              'reason': 'evidence', 'evidence_ids': ['F00']} for i, score in enumerate(scores)]
    got = combine_votes(votes)
    assert got['score'] == expected and got['candidate_median'] == candidate
    assert got['votes'] == votes


def test_general_aggregates_at_criterion_level_and_counts_shared_audio_once(tmp_path):
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture')
    case = {'id': 'a', 'target_duration_s': 60}
    prepared = evidence(video, tmp_path/'out')
    members = [{'id': str(i), 'result': result(case, video, s)} for i, s in enumerate([3,4,4])]
    got = aggregate_panel(case, prepared, members, tmp_path/'out', evaluation_version())
    assert got['scoring']['overall'] == 75
    assert got['judge_panel']['complete_judges'] == 3
    assert got['dimensions']['audio_quality']['independent_judge_votes'] is None
    assert got['judge_panel']['pending_criteria'] == 0
    assert not (tmp_path/'out/review_queue.json').read_text().count('candidate_median')


@pytest.mark.parametrize('block', ['dimension_gate', 'verification', 'missing', 'disagreement', 'transcript'])
def test_panel_cannot_resurrect_unknown_or_conflicting_scores(tmp_path, block):
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture')
    case = {'id': 'a', 'target_duration_s': 60}; out = tmp_path/'out'
    prepared = evidence(video, out)
    members = [{'id': str(i), 'result': result(case, video)} for i in range(3)]
    first = members[0]['result']; dim = first['dimensions']['conceptual_correctness']
    if block == 'dimension_gate':
        dim.update(score=None, evidence_status='incomplete_actual_audio'); first['scoring']['overall'] = None
    elif block == 'verification':
        first['verification_conflicts'] = [{'criterion': 'conceptual_correctness.facts', 'check': 'check1'}]
        first['scoring']['overall'] = None
    elif block == 'missing': members[0]['result'] = {'error': 'provider failed', 'scoring': {'overall': None}}
    elif block == 'disagreement': dim['criteria']['facts']['score'] = 1
    else:
        prepared['audio'][0]['transcript_guard'] = {'status': 'partial', 'unresolved_spans': [{'id': 'U00'}]}
    got = aggregate_panel(case, prepared, members, out, evaluation_version())
    assert got['scoring']['overall'] is None
    assert got['dimensions']['visual_quality']['score'] == (None if block == 'missing' else 75)
    if block == 'dimension_gate': assert got['dimensions']['conceptual_correctness']['score'] is None
    if block == 'verification': assert got['verification_conflicts'][0]['judge_id'] == '0'


def test_optional_criterion_requires_unanimous_applicability(tmp_path):
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture'); case = {'id': 'a'}
    prepared = evidence(video, tmp_path/'out')
    members = [{'id': str(i), 'result': result(case, video)} for i in range(3)]
    for m in members:
        m['result']['dimensions']['task_completeness']['criteria']['verification'].update(status='not_applicable', score=None)
    got = aggregate_panel(case, prepared, members, tmp_path/'out', evaluation_version())
    assert got['dimensions']['task_completeness']['applicable_criteria_count'] == 5
    assert got['scoring']['overall'] == 75
    members[0]['result']['dimensions']['task_completeness']['criteria']['verification'].update(status='observed', score=4)
    assert aggregate_panel(case, prepared, members, tmp_path/'out', evaluation_version())['scoring']['overall'] is None


@pytest.mark.parametrize('invalid', ['count', 'id', 'family', 'model'])
def test_direct_panel_rejects_invalid_members_before_media_or_api(tmp_path, monkeypatch, invalid):
    from localbench import judge
    specs = judge_panel_from(config())
    if invalid == 'count':
        specs.pop()
    elif invalid == 'model':
        specs[1].service.model = specs[0].service.model
    else:
        setattr(specs[1], invalid, getattr(specs[0], invalid))
    def forbidden(*args, **kwargs):
        pytest.fail('invalid panel reached media preparation or audio calls')
    monkeypatch.setattr(judge, 'prepare_evidence', forbidden)
    with pytest.raises(ValueError, match='three distinct'):
        evaluate_panel(tmp_path/'absent.mp4', {'id': 'a'}, tmp_path/'out',
                       [(spec, None) for spec in specs], None)
    assert not (tmp_path/'out').exists()


def test_orchestration_shares_evidence_but_isolates_judges_and_retains_failure(tmp_path, monkeypatch):
    from localbench import judge
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture'); case = {'id': 'a'}; out = tmp_path/'out'
    prepared = evidence(video, out); expected_hash = digest(prepared)
    calls = []; barrier = threading.Barrier(3)
    def prepare(*args, **kwargs): calls.append('prepare'); return prepared
    def evaluate(video, case, directory, client, **kwargs):
        shared = kwargs['prepared_evidence']
        assert digest(shared) == expected_hash
        assert client.audio is None
        barrier.wait(timeout=5)
        shared['audio'][0]['transcript'] = client.model
        if client.model == 'model_2': raise RuntimeError('failed JUDGE_SECRET_2')
        output = result(case, video)
        write_json(directory/'scores.json', output)
        return output
    monkeypatch.setattr(judge, 'prepare_evidence', prepare)
    monkeypatch.setattr(judge, 'evaluate', evaluate)
    pool = ServicePool(tmp_path/'api')
    specs = judge_panel_from(config())
    members = [(s, JudgeClient(pool.client(s.service), None)) for s in specs]
    try:
        got = evaluate_panel(video, case, out, members, object())
    finally: pool.close()
    assert calls == ['prepare'] and digest(prepared) == expected_hash
    assert got['scoring']['overall'] is None
    assert got['judge_panel']['complete_judges'] == 2
    assert len(list((out/'judges').glob('*/scores.json'))) == 3
    assert 'JUDGE_SECRET' not in (out/'judges/judge_2/scores.json').read_text()


@pytest.mark.parametrize('route', ['bench', 'method', 'native', 'code2video', 'evaluate'])
def test_cli_routes_three_judges_resumes_and_freezes_services(tmp_path, monkeypatch, route):
    import sys
    from localbench import judge, run, native_pipeline
    case = {'id': 'a', 'prompt_text': 'Explain a public relation.', 'target_duration_s': 60,
            'expected_concepts': ['PRIVATE_REFERENCE']}
    data = tmp_path/'tasks.jsonl'; data.write_text(json.dumps(case)+'\n')
    cfg = config()
    if route == 'native':
        cfg['video'] = {'model': 'video', 'url': 'https://video.test/tasks',
                        'query_url': 'https://video.test/tasks/{task_id}', 'api_key': 'VIDEO_SECRET'}
    path = tmp_path/'services.json'; write_json(path, cfg)
    calls = []
    def generate(case, base, client, *args, **kwargs):
        calls.append('generator:'+client.model)
        video = base/case['id']/'code.mp4'; video.parent.mkdir(parents=True, exist_ok=True); video.write_bytes(b'fixture')
        from localbench.common import public_case
        return {'id': case['id'], 'status': 'rendered', 'public_input_hash': digest(public_case(case)),
                'artifacts': [{'mode': 'code', 'complete': True, 'video_path': str(video), 'sha256': file_hash(video)}]}
    def evaluate(video, case, out, client, **kwargs):
        calls.append('judge:'+client.model)
        got = result(case, video); write_json(out/'scores.json', got); return got
    monkeypatch.setattr(run, 'resolve_tts', lambda _: {'backend': 'test'})
    monkeypatch.setattr(run, 'generate_one', generate)
    monkeypatch.setattr(run, 'improve', lambda case, result, *a, **k: result)
    monkeypatch.setattr(native_pipeline, 'generate_native', generate)
    monkeypatch.setattr(judge, 'prepare_evidence', lambda video, out, *a, **k: evidence(Path(video), out))
    monkeypatch.setattr(judge, 'evaluate', evaluate)
    argv = ['teacher.py', 'bench' if route in {'native', 'code2video'} else route, '--config', str(path), '--data', str(data),
            '--num', '1', '--out', str(tmp_path/'run'), '--api-workers', '2']
    if route == 'native': argv += ['--backend', 'video']
    if route == 'code2video':
        from localbench import code2video, code2video_runtime
        monkeypatch.setattr(code2video_runtime, 'settings_from', lambda *a: {'upstream': {'commit': 'fixed'}})
        monkeypatch.setattr(code2video, 'generate_code2video', generate)
        argv += ['--framework', 'code2video']
    if route == 'evaluate':
        video = tmp_path/'import.mp4'; video.write_bytes(b'imported')
        manifest = tmp_path/'manifest.json'
        write_json(manifest, {'cases': [{'id': 'a', 'status': 'rendered', 'artifacts': [
            {'complete': True, 'mode': 'native', 'video_path': str(video), 'sha256': file_hash(video)}]}]})
        argv += ['--manifest', str(manifest)]
    monkeypatch.setattr(sys, 'argv', argv)
    assert run.main() == 0
    assert sorted(c for c in calls if c.startswith('judge:')) == ['judge:model_0', 'judge:model_1', 'judge:model_2']
    assert ('generator:generator' in calls) == (route != 'evaluate')
    frozen = (tmp_path/'run/run_config.json').read_text()
    assert 'SECRET' not in frozen
    assert 'PRIVATE_REFERENCE' not in (tmp_path/'run/generation_inputs.jsonl').read_text()
    assert json.loads((tmp_path/'run/summary.json').read_text())['cases'][0]['judge_count'] == 3
    assert '三评委' in (tmp_path/'run/REPORT.md').read_text()
    before = list(calls)
    monkeypatch.setattr(sys, 'argv', argv+['--resume'])
    assert run.main() == 0 and calls == before
    cfg['judges'][0]['model'] = 'changed-judge'; write_json(path, cfg)
    assert run.main() == 2 and calls == before


def test_specific_failure_keeps_general_and_retries_only_when_requested(tmp_path, monkeypatch):
    import sys
    from localbench import run, judge_panel, specific_eval
    from test_localbench_specific_eval import entry
    case = {'id': 'a', 'prompt_text': 'Explain a relation.'}
    video = tmp_path/'v.mp4'; video.write_bytes(b'fixture')
    data = tmp_path/'tasks.jsonl'; data.write_text(json.dumps(case)+'\n')
    manifest = tmp_path/'manifest.json'
    write_json(manifest, {'cases': [{'id': 'a', 'status': 'rendered', 'artifacts': [
        {'complete': True, 'video_path': str(video), 'sha256': file_hash(video)}]}]})
    qpath = tmp_path/'questions.json'; write_json(qpath, {'version': 'fixed-specific-v1', 'cases': {'a': entry(case)}})
    cfg = config(); cfg['specific_questions'] = str(qpath)
    cpath = tmp_path/'config.json'; write_json(cpath, cfg)
    calls = []
    def general(video, case, out, *a, **k):
        calls.append('general'); evidence(Path(video), out)
        got = result(case, video); write_json(out/'scores.json', got); return got
    def specific(*a, **k):
        calls.append('specific')
        if calls.count('specific') == 1: raise RuntimeError('one judge unavailable')
        return {'status': 'complete', 'specific_score': 75, 'scored_questions': 1, 'planned_questions': 1}
    monkeypatch.setattr(judge_panel, 'evaluate_panel', general)
    monkeypatch.setattr(specific_eval, 'evaluate_specific', specific)
    argv = ['teacher.py', 'evaluate', '--manifest', str(manifest), '--config', str(cpath), '--data', str(data), '--out', str(tmp_path/'run')]
    monkeypatch.setattr(sys, 'argv', argv)
    assert run.main() == 2
    score = json.loads((tmp_path/'run/evaluation/a/scores.json').read_text())
    assert score['scoring']['overall'] == 75 and score['specific']['specific_score'] is None
    monkeypatch.setattr(sys, 'argv', argv+['--resume'])
    assert run.main() == 2 and calls == ['general', 'specific']
    monkeypatch.setattr(sys, 'argv', argv+['--resume', '--retry-incomplete'])
    assert run.main() == 0 and calls == ['general', 'specific', 'general', 'specific']
    assert (tmp_path/'run/evaluation/a/previous_attempts/attempt_001/scores.json').exists()
    summary = json.loads((tmp_path/'run/summary.json').read_text())
    assert summary['specific_evaluation']['scored_cases'] == 1
    changed = entry(case); changed['questions'][0]['question'] = 'Another question'
    write_json(qpath, {'version': 'fixed-specific-v1', 'cases': {'a': changed}})
    assert run.main() == 2
