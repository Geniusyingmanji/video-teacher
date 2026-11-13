"""Exercise selected-case dispatch without model calls or media rendering."""
import json
import sys

import pytest

from localbench.common import digest, public_case, write_json
from localbench.provenance import file_hash
from localbench.rubric import DIMENSIONS, aggregate_dimensions


@pytest.mark.parametrize('command', ['bench', 'method'])
def test_cli_batch_generates_and_scores_only_selected_cases_then_rejudges_subset(tmp_path, monkeypatch, command):
    from localbench import run, judge
    rows = [{'id': c, 'prompt_text': 'Explain concept '+c, 'target_duration_s': 60} for c in 'abcd']
    data = tmp_path/'tasks.jsonl'
    data.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    config = tmp_path/'services.json'
    config.write_text(json.dumps({'generator': {'model': 'mock', 'url': 'https://example.test/v1',
                                              'api_key': 'test-placeholder'}, 'audio_judge': False}))
    generated, evaluated, repaired = [], [], []

    def generate(case, out, client, modes, **kwargs):
        generated.append(case['id'])
        assert kwargs['use_state'] == (command == 'method')
        video = out/case['id']/'code.mp4'
        video.parent.mkdir(parents=True)
        video.write_bytes(b'test-media')
        return {'id': case['id'], 'status': 'rendered', 'public_input_hash': digest(public_case(case)),
                'artifacts': [{'mode': 'code', 'complete': True, 'video_path': str(video), 'sha256': file_hash(video)}]}

    def evaluate(video, case, out, client, **kwargs):
        evaluated.append(case['id'])
        result = {'case_id': case['id'], 'case_hash': digest(case), 'video_sha256': file_hash(video),
                  'scoring': aggregate_dimensions({k: {'score': 75} for k in DIMENSIONS})}
        write_json(out/'scores.json', result)
        return result

    def improve(case, result, *args, **kwargs):
        repaired.append(case['id'])
        return result

    monkeypatch.setattr(run, 'generate_one', generate)
    monkeypatch.setattr(run, 'improve', improve)
    monkeypatch.setattr(run, 'resolve_tts', lambda _: {'backend': 'test'})
    monkeypatch.setattr(judge, 'evaluate', evaluate)
    out = tmp_path/command
    common = ['--config', str(config), '--data', str(data), '--api-workers', '1', '--eval-workers', '1']
    argv = ['teacher.py', command, *common, '--num', '2', '--offset', '1', '--out', str(out)]
    monkeypatch.setattr(sys, 'argv', argv)
    assert run.main() == 0
    assert sorted(generated) == sorted(evaluated) == ['b', 'c']
    assert sorted(repaired) == (['b', 'c'] if command == 'method' else [])
    manifest = out/'manifest.json'
    assert json.loads(manifest.read_text())['planned_ids'] == ['b', 'c']
    assert json.loads((out/'summary.json').read_text())['planned_cases'] == 2
    # Same selection resumes without duplicate generation or scoring.
    monkeypatch.setattr(sys, 'argv', [*argv, '--resume'])
    assert run.main() == 0
    assert len(generated) == len(evaluated) == 2
    # Default evaluation pool is the supplied manifest, not the entire dataset.
    monkeypatch.setattr(sys, 'argv', ['teacher.py', 'evaluate', *common, '--manifest', str(manifest),
                                    '--num', '1', '--offset', '1', '--out', str(tmp_path/'review')])
    assert run.main() == 0
    assert len(generated) == 2 and evaluated[-1] == 'c'
    assert json.loads((tmp_path/'review/manifest.json').read_text())['planned_ids'] == ['c']


def test_student_cli_slices_manifest_before_profile_validation(tmp_path, monkeypatch):
    from localbench import run, student_run
    data = tmp_path/'tasks.jsonl'
    data.write_text(''.join(json.dumps({'id': c, 'prompt_text': c})+'\n' for c in 'abc'))
    manifest = tmp_path/'manifest.json'
    write_json(manifest, {'cases': [{'id': c, 'artifacts': []} for c in 'bc'], 'planned_ids': ['b', 'c']})
    config = tmp_path/'config.json'
    write_json(config, {})
    monkeypatch.setattr(run, 'resolve_services', lambda *args: (None, None, None))
    monkeypatch.setattr(student_run, 'settings_from', lambda *args: {})
    def settings(value, cases):
        assert [c['id'] for c in cases] == ['c']
        return {}
    monkeypatch.setattr(student_run, 'public_settings', settings)
    monkeypatch.setattr(student_run, 'run_stage', lambda out, cases, *args, **kwargs:
                        [{'case_id': c['id'], 'status': 'complete', 'metrics': {}} for c in cases])
    monkeypatch.setattr(sys, 'argv', ['teacher.py', 'student', '--config', str(config), '--data', str(data),
                                    '--manifest', str(manifest), '--num', '1', '--offset', '1',
                                    '--out', str(tmp_path/'students')])
    assert run.main() == 0
    assert json.loads((tmp_path/'students/manifest.json').read_text())['planned_ids'] == ['c']
