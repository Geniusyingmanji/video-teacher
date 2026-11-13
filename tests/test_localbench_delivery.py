import argparse
import json
from pathlib import Path

import httpx
import pytest

from localbench.common import digest, write_json
from localbench.delivery import build_report
from localbench.rubric import DIMENSIONS, aggregate_dimensions
from localbench.services import Service, ServicePool, JudgeClient, chat_url, service_from


def test_service_urls_and_secrets(monkeypatch):
    assert chat_url('https://example.test') == 'https://example.test/v1/chat/completions'
    assert chat_url('https://example.test/compatible-mode/v1/') == 'https://example.test/compatible-mode/v1/chat/completions'
    assert chat_url('https://example.test/v1/chat/completions') == 'https://example.test/v1/chat/completions'
    for url in ['invalid', 'https://key@example.test', 'https://example.test?key=secret']:
        with pytest.raises(ValueError): chat_url(url)
    base = Service('vlm', 'https://example.test/v1', 'secret-example')
    assert 'secret-example' not in repr(base)
    assert 'secret-example' not in json.dumps(base.public())
    monkeypatch.delenv('VIDEO_TEACHER_API_KEY', raising=False)
    assert service_from({'model': 'audio'}, fallback=base).api_key == base.api_key
    with pytest.raises(ValueError):
        service_from({'url': 'https://other.test/v1'}, fallback=base)
    omni = service_from({'model': 'qwen3.5-omni-flash'}, fallback=base)
    assert omni.json_format is False
    assert service_from({}, fallback=omni).json_format is False
    assert service_from({'json_format': True}, fallback=omni).json_format is True


def test_audio_routing_and_endpoint_specific_cache(tmp_path, monkeypatch):
    calls = []
    def post(self, url, **kwargs):
        calls.append((url, kwargs['json'], kwargs['headers']))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"ok":true}'}, 'finish_reason': 'stop'}],
                                        'usage': {'total_tokens': 10}})
    monkeypatch.setattr(httpx.Client, 'post', post)
    pool = ServicePool(tmp_path, max_calls=3, max_tokens=100000)
    visual = pool.client(Service('vlm', 'https://vision.test/v1', 'vision-secret'))
    audio = pool.client(Service('listener', 'https://audio.test/v1', 'audio-secret', json_format=False))
    client = JudgeClient(visual, audio)
    assert client.chat([{'role': 'user', 'content': 'hello'}], purpose='visual') == {'ok': True}
    assert client.chat([{'role': 'user', 'content': [{'type': 'input_audio', 'input_audio': {'data': 'dummy', 'format': 'wav'}}]}],
                       purpose='audio', model='hardcoded-legacy-model') == {'ok': True}
    assert calls[1][0] == 'https://audio.test/v1/chat/completions'
    assert calls[1][1]['model'] == 'listener' and 'response_format' not in calls[1][1]
    other = pool.client(Service('vlm', 'https://other.test/v1', 'other-secret'))
    other.chat([{'role': 'user', 'content': 'hello'}], purpose='different-provider')
    assert len(calls) == 3
    log = (tmp_path/'usage.jsonl').read_text()
    assert 'vision-secret' not in log and 'audio-secret' not in log
    pool.close()


def test_reporting_hierarchy_preserves_weights_and_missing_dimensions():
    dims = {name: {'score': i*10} for i, name in enumerate(DIMENSIONS)}
    result = aggregate_dimensions(dims)
    teaching = [dims[k]['score'] for k, d in DIMENSIONS.items() if d['group'] == 'teaching']
    assert result['groups']['teaching'] == sum(teaching)/7
    parents = result['teaching_groups']
    assert sum(p['score']*p['weight_within_teaching'] for p in parents.values()) == pytest.approx(sum(teaching)/7)
    dims['crossmodal_alignment']['score'] = None
    result = aggregate_dimensions(dims)
    assert result['teaching_groups']['content']['score'] is not None
    assert result['teaching_groups']['expression']['score'] is None
    assert result['overall'] is None


def test_delivery_report_keeps_failed_cases_and_nulls(tmp_path):
    cases = [{'id': x, 'discipline': 'physics', 'task_type': 'explanation'} for x in ['a', 'b']]
    gen = [{'id': 'a', 'status': 'rendered', 'artifacts': [{'complete': True, 'video_path': str(tmp_path/'a.mp4')}]},
           {'id': 'b', 'status': 'planning_failed', 'artifacts': [], 'error': 'model failure'}]
    scored = [{'case_id': 'a', 'scoring': aggregate_dimensions({k: {'score': 80} for k in DIMENSIONS})}]
    report = build_report(tmp_path, cases, gen, scored)
    assert report['planned_cases'] == 2 and report['delivered_cases'] == 1
    assert report['valid_score_coverage'] == .5
    assert report['mean_overall_among_valid'] == 80 and report['all_cases_mean'] is None
    assert report['cases'][1]['overall'] is None
    assert 'planning_failed' in (tmp_path/'REPORT.md').read_text()


def test_one_command_generation_evaluation_resume_and_credential_isolation(tmp_path, monkeypatch):
    from localbench import run
    import localbench.judge
    data = tmp_path/'cases.jsonl'
    case = {'id': 'a', 'prompt_text': 'Explain a public concept', 'target_duration_s': 60,
            'expected_concepts': ['PRIVATE_REFERENCE_SENTINEL']}
    data.write_text(json.dumps(case)+'\n')
    config = tmp_path/'private.json'
    config.write_text(json.dumps({'generator': {'model': 'vlm', 'url': 'https://example.test/v1', 'api_key': 'PRIVATE_API_SENTINEL'},
                                 'audio_judge': False}))
    calls = []
    def generate(case, out, client, modes, **kwargs):
        from localbench.provenance import file_hash
        from localbench.common import public_case
        calls.append('generate'); p = out/case['id']/'code.mp4'; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'fixture')
        return {'id': case['id'], 'status': 'rendered', 'public_input_hash': digest(public_case(case)),
                'artifacts': [{'mode': 'code', 'complete': True, 'video_path': str(p), 'sha256': file_hash(p)}]}
    def evaluate(video, case, out, client, **kwargs):
        from localbench.provenance import file_hash
        calls.append('evaluate')
        result = {'case_id': case['id'], 'video_sha256': file_hash(video), 'case_hash': digest(case),
                  'scoring': aggregate_dimensions({k: {'score': 80} for k in DIMENSIONS})}
        write_json(out/'scores.json', result); return result
    monkeypatch.setattr(run, 'generate_one', generate)
    monkeypatch.setattr(localbench.judge, 'evaluate', evaluate)
    monkeypatch.setattr(run, 'resolve_tts', lambda _: {'backend': 'fixture'})
    args = argparse.Namespace(config=config, model=None, url=None, api_key_env=None, data=data, ids=['a'], suite='all',
        command='bench', backend='code', out=tmp_path/'run', resume=False, manifest=None, api_workers=2,
        render_workers=1, eval_workers=1, max_calls=20, max_tokens=100000, no_repair=False)
    assert run.execute(args) == 0
    args.resume = True
    assert run.execute(args) == 0
    assert calls == ['generate', 'evaluate']
    assert 'PRIVATE_API_SENTINEL' not in (args.out/'run_config.json').read_text()
    assert 'PRIVATE_REFERENCE_SENTINEL' not in (args.out/'generation_inputs.jsonl').read_text()
    assert 'PRIVATE_REFERENCE_SENTINEL' in (args.out/'evaluation_tasks.jsonl').read_text()
    saved = args.out/'evaluation/a/scores.json'
    partial = json.loads(saved.read_text()); partial['scoring']['overall'] = None
    write_json(saved, partial)
    assert run.execute(args) == 2
    assert calls == ['generate', 'evaluate']
    args.retry_incomplete = True
    assert run.execute(args) == 0
    assert calls == ['generate', 'evaluate', 'evaluate']
    old = args.out/'evaluation/a/previous_attempts/attempt_001/scores.json'
    assert json.loads(old.read_text())['scoring']['overall'] is None

    # Evaluation defaults to every manifest case, even outside the built-in smoke IDs.
    args.command = 'evaluate'; args.manifest = args.out/'manifest.json'
    args.out = tmp_path/'rejudge'; args.resume = False; args.ids = None; args.suite = 'smoke'
    assert run.execute(args) == 0
    assert json.loads((args.out/'summary.json').read_text())['planned_cases'] == 1
