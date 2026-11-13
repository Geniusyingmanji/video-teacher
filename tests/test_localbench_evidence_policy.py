import copy
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import pytest
from PIL import Image

from localbench.evidence import extract, probe_audio
from localbench.judge import assess_audio
from localbench.rubric import DIMENSIONS, aggregate_dimensions
from localbench.score_validity import apply, invalid_reasons, valid_score
from localbench.acceptance import assess
from localbench.compare import paired_summary


def scored():
    dims = {name: {'score': 100, 'criteria': {k: {
        'status': 'observed', 'score': 5, 'severity': 'none', 'evidence_ids': ['F00'],
        'reason': 'Observed support.', 'limitation': 'none observed',
        'high_score_evidence': 'Specific demonstrated support.'}
        for k in d['criteria']}} for name, d in DIMENSIONS.items()}
    return {'case_id': 'a', 'dimensions': dims, 'scoring': aggregate_dimensions(dims),
            'critical_verification': {'status': 'reviewed', 'checks': []},
            'timeline_review': {'status': 'reviewed', 'checks': [], 'unreviewed_frame_ids': []},
            'output_checks': {'failed': [], 'review': [], 'unverified': []}}


def make_video(path, audio=False, flash=False):
    video = 'color=c=white:s=64x64:r=10:d=3'
    if flash:
        video += ",drawbox=x=0:y=0:w=64:h=64:color=red:t=fill:enable='between(t,1.1,1.19)'"
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', video]
    if audio:
        command += ['-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=3']
    command += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p']
    if audio:
        command += ['-c:a', 'aac', '-shortest']
    subprocess.run(command + [str(path)], check=True, capture_output=True)


def test_missing_audio_is_observed_absence_without_any_model_or_asr_call(tmp_path):
    video = tmp_path / 'noaudio.mp4'; make_video(video)
    packet = extract(video, tmp_path / 'evidence')
    assert packet['audio_stream_probe']['status'] == 'absent'
    row = packet['audio'][0]
    assert row['status'] == 'audio_stream_missing'
    class NoCalls:
        def chat(self, *a, **kw):
            raise AssertionError('no listener call for verified missing stream')
    reviewed = assess_audio(NoCalls(), row)
    assert reviewed['narration_presence']['status'] == 'observed_absent'
    assert reviewed['transcript_valid'] and reviewed['status'] == 'reviewed'
    assert {x['score'] for x in reviewed['criteria'].values()} == {1}
    assert reviewed['transcript'] == ''


def test_probe_failure_and_extraction_failure_never_become_silence(tmp_path, monkeypatch):
    import localbench.evidence as e
    monkeypatch.setattr(e.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, 1, '', 'bad media'))
    assert probe_audio(tmp_path / 'bad.mp4')['status'] == 'probe_failed'
    assert assess_audio(None, {'status': 'extraction_failed', 'id': 'A00'})['status'] == 'unverified'
    assert 'narration_presence' not in assess_audio(None, {'status': 'extraction_failed'})


def test_probe_unavailable_does_not_prevent_successful_audio_extraction(tmp_path, monkeypatch):
    import localbench.evidence as e
    video = tmp_path / 'audio.mp4'; make_video(video, audio=True)
    monkeypatch.setattr(e, 'probe_audio', lambda _: {'status': 'probe_failed', 'error': 'ffprobe unavailable'})
    packet = extract(video, tmp_path / 'evidence')
    assert packet['audio'][0]['status'] == 'extracted'
    assert Path(packet['audio'][0]['path']).exists()


def test_dense_sampling_includes_short_flash_and_last_frame(tmp_path):
    video = tmp_path / 'flash.mp4'; make_video(video, flash=True)
    packet = extract(video, tmp_path / 'evidence')
    frames = packet['review_frames']
    assert any(f['time_s'] == pytest.approx(1.1) for f in frames)
    assert frames[-1]['frame_index'] == packet['metadata']['decoded_frame_count'] - 1
    assert max(b['time_s'] - a['time_s'] for a, b in zip(frames, frames[1:])) <= .5 + 1e-5
    flash = next(f for f in frames if f['time_s'] == pytest.approx(1.1))
    assert Image.open(flash['path']).getpixel((32, 32))[0] > 200


@pytest.mark.parametrize('inject,blocked,retained', [
    ({'reference_concerns': [{'affected': ['conceptual_correctness.facts'], 'reason': 'reference disagrees'}]}, 'conceptual_correctness', 'visual_quality'),
    ({'reference_concerns': ['unstructured conflict']}, 'task_completeness', 'audio_quality'),
    ({'critical_verification': {'status': 'auxiliary_check_error', 'checks': [], 'affected': ['visual_teaching.correspondence']}}, 'visual_teaching', 'visual_quality'),
    ({'critical_verification': {'status': 'reviewed', 'checks': [{'id': 'q', 'verdict': 'unverified', 'affected': ['task_completeness.coverage']}]}}, 'task_completeness', 'audio_quality'),
    ({'critical_verification': {'status': 'reviewed', 'checks': [], 'screen_relation_review': {'status': 'partial'}}}, 'conceptual_correctness', 'audio_quality'),
    ({'timeline_review': {'status': 'partial', 'checks': [], 'unreviewed_frame_ids': ['F01']}}, 'temporal_consistency', 'audio_quality'),
    ({'verification_conflicts': [{'criterion': 'crossmodal_alignment.agreement'}]}, 'crossmodal_alignment', 'visual_quality'),
    ({'transcript_evidence_validity': {'all_transcript_evidence_resolved': False}}, 'pedagogical_clarity', 'visual_quality'),
])
def test_uncertainty_propagates_only_to_affected_dimensions_and_groups(inject, blocked, retained):
    original = scored(); original.update(copy.deepcopy(inject)); before = copy.deepcopy(original)
    result = apply(original)
    assert original == before
    assert result['dimensions'][blocked]['score'] is None
    assert result['dimensions'][blocked]['raw_score_before_validity'] == 100
    assert result['dimensions'][blocked]['criteria'] == before['dimensions'][blocked]['criteria']
    assert result['dimensions'][retained]['score'] == 100
    assert result['scoring']['overall'] is None
    assert assess(result)['status'] == 'unverified'
    assert apply(result) == result


def test_legacy_conflicting_dimension_cannot_enter_pair_mean_even_if_numeric():
    left = scored(); left.update(mode='code', verification_conflicts=[{'criterion': 'conceptual_correctness.facts'}])
    right = scored(); right['mode'] = 'slides'
    result = paired_summary([left, right], expected_ids=['a', 'failed'])
    assert result['dimensions']['conceptual_correctness']['n_pairs'] == 0
    assert result['dimensions']['overall']['n_pairs'] == 0
    assert result['dimensions']['visual_quality']['n_pairs'] == 1
    assert result['dimensions']['conceptual_correctness']['n_tasks'] == 2
    assert result['evidence_exclusions'][0]['invalid_dimensions']['conceptual_correctness']


def test_high_mean_does_not_compensate_major_content_defect():
    result = scored()
    result['dimensions']['conceptual_correctness']['criteria']['facts'].update(score=2, severity='major')
    result['dimensions']['conceptual_correctness']['score'] = 87.5
    result['scoring'] = aggregate_dimensions(result['dimensions'])
    before = copy.deepcopy(result)
    assert result['scoring']['overall'] > 99
    acceptance = assess(result)
    assert acceptance['status'] == 'failed' and not acceptance['passed']
    assert 'critical_criterion:conceptual_correctness.facts' in acceptance['failures']
    assert result == before


def test_pass_and_unknown_and_observed_failure_remain_distinct():
    result = scored()
    assert assess(result)['status'] == 'passed'
    result['output_checks']['unverified'] = ['audio_probe']
    assert assess(result)['status'] == 'unverified'
    result['output_checks']['failed'] = ['missing_speech']
    assert assess(result)['status'] == 'failed'
    assert assess(result)['unverified']


def test_strict_extraction_retains_every_decoded_frame(tmp_path):
    video = tmp_path / 'full.mp4'; make_video(video, flash=True)
    packet = extract(video, tmp_path / 'full', review_every_frame=True)
    assert len(packet['review_frames']) == packet['metadata']['decoded_frame_count']
    assert [f['frame_index'] for f in packet['review_frames']] == list(range(packet['metadata']['decoded_frame_count']))
    assert packet['review_sampling']['required_scope'] == 'all_decoded_frames'


def test_legacy_conflicts_cannot_show_valid_group_or_pass_in_delivery(tmp_path):
    from localbench.delivery import build_report
    result = scored()
    result['verification_conflicts'] = [{'criterion': 'conceptual_correctness.facts'}]
    summary = build_report(tmp_path, [{'id': 'a'}], [], [result])
    row = summary['cases'][0]
    assert row['overall'] is None and row['conceptual_correctness'] is None
    assert row['teaching'] is None and row['content'] is None
    assert row['video'] == 100
    assert summary['accepted_cases'] == 0 and summary['acceptance_rate'] == 0
    assert row['acceptance_status'] == 'unverified'
    assert '质量验收' in (tmp_path / 'REPORT.md').read_text()


def test_acknowledged_major_layout_does_not_become_a_false_scoring_conflict():
    original = scored()
    quality = original['dimensions']['visual_quality']
    quality['layout_audit'] = {'status': 'reviewed', 'frames': [{'issues': [{'kind': 'small_text', 'severity': 'major'}]}]}
    assert 'visual_quality' in invalid_reasons(original)
    quality['criteria']['legibility'].update(score=2, severity='major')
    quality['score'] = 87.5
    assert 'visual_quality' not in invalid_reasons(original)
    assert assess(original)['status'] == 'failed'


def test_legacy_failed_check_disagreement_is_excluded_without_saved_conflict_list():
    result = scored()
    result['critical_verification']['checks'] = [{'id': 'direction', 'verdict': 'fail', 'severity': 'major',
                                                'affected': ['conceptual_correctness.relationships']}]
    assert valid_score(result, 'conceptual_correctness') is None
    assert valid_score(result, 'visual_quality') == 100


def test_missing_score_validity_is_idempotent_and_never_manufactures_zero():
    result = scored(); result['dimensions']['audio_quality']['score'] = None
    clean = apply(result)
    assert clean['scoring']['overall'] is None
    assert clean['dimensions']['audio_quality']['score'] is None
    assert apply(clean) == clean


def test_legacy_panel_empty_concern_wrappers_are_not_invented_conflicts():
    result = scored()
    result['reference_concerns'] = [{'judge_id': str(i), 'concerns': []} for i in range(3)]
    assert not invalid_reasons(result)
    result['reference_concerns'][1]['concerns'] = [{'affected': ['task_completeness.coverage']}]
    assert set(invalid_reasons(result)) == {'task_completeness'}
