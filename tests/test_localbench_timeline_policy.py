import copy
import json

import pytest
from PIL import Image

from localbench import alignment, timeline_review
from localbench.rubric import DIMENSIONS


def frame_packet(tmp_path, count=35):
    p = tmp_path / 'frame.jpg'; Image.new('RGB', (64, 64), 'white').save(p)
    frames = [{'id': f'F{i:06d}', 'time_s': i / 2, 'frame_index': i, 'path': str(p)} for i in range(count)]
    return {'frames': frames, 'review_frames': frames, 'review_sampling': {'interval_s': .5}}


def test_window_partition_overlaps_and_covers_every_frame(tmp_path):
    frames = frame_packet(tmp_path)['frames']
    batches = timeline_review.windows(frames)
    assert len(batches) == 3
    assert batches[0][-1] == batches[1][0]
    assert batches[1][-1] == batches[2][0]
    assert {f['id'] for b in batches for f in b} == {f['id'] for f in frames}
    assert max(map(len, batches)) == 16


@pytest.mark.parametrize('failure', [False, True])
def test_timeline_checks_all_windows_and_records_missing_coverage(tmp_path, failure):
    packet = frame_packet(tmp_path)
    class Client:
        def chat(self, messages, **kw):
            ids = [p['text'].split()[0] for p in messages[0]['content']
                   if p['type'] == 'text' and p['text'].startswith('F')]
            index = int(kw['purpose'].split(':')[-2])
            if failure and index == 1:
                raise RuntimeError('judge unavailable')
            return {'reviewed_frame_ids': ids, 'summary': 'Observed labels and changes.', 'findings': []}
    result = timeline_review.review(Client(), packet, [], {'id': 'a', 'prompt_text': 'Explain.'}, tmp_path / 'review')
    assert result['requested_frames'] == 35
    assert result['status'] == ('partial' if failure else 'reviewed')
    if failure:
        assert result['unreviewed_frame_ids'] and result['errors']
    else:
        assert result['reviewed_frames'] == 35 and not result['unreviewed_frame_ids']
        assert result['windows'][-1]['frame_ids'][-1] == packet['frames'][-1]['id']


def test_timeline_rejects_fabricated_or_omitted_frames_and_bad_affected_criteria(tmp_path):
    frames = frame_packet(tmp_path, 3)['frames']
    good = {'reviewed_frame_ids': [f['id'] for f in frames], 'summary': 'Observed a stale label.',
            'findings': [{'verdict': 'fail', 'severity': 'major', 'affected': ['temporal_consistency.state_continuity'],
                          'evidence_ids': [frames[1]['id']], 'reason': 'Old equation remains after the change.'}]}
    assert timeline_review.validate(good, frames)
    for change in [lambda r: r['reviewed_frame_ids'].pop(),
                   lambda r: r['findings'][0].update(evidence_ids=['F999999']),
                   lambda r: r['findings'][0].update(affected=['fake.criterion'])]:
        bad = copy.deepcopy(good); change(bad)
        with pytest.raises(ValueError):
            timeline_review.validate(bad, frames)


@pytest.mark.parametrize('failure', [False, True])
def test_alignment_reviews_beyond_eight_windows_and_preserves_late_mismatch(tmp_path, failure):
    packet = frame_packet(tmp_path, 42)
    audio = [{'id': 'A00', 'start_s': 0, 'end_s': 21, 'timing_valid': True,
              'utterances': [{'start_s': i, 'end_s': i + .5, 'text': 'Move.',
                              'words': [{'word': 'Move.', 'start_s': i, 'end_s': i + .5}]} for i in range(20)]}]
    assert len(alignment.make_probes(packet, audio)) == 20  # Short utterances count too.
    class Client:
        calls = 0
        def chat(self, messages, **kw):
            self.calls += 1
            probes = []
            for part in messages[0]['content']:
                if part['type'] == 'text' and part['text'].startswith('{'):
                    value = json.loads(part['text'])
                    if 'allowed_ids' in value:
                        probes.append(value)
            late = any(p['id'] == 'P19' for p in probes)
            if failure and late:
                raise RuntimeError('last batch failed')
            score = 1 if late else 5
            severity = 'critical' if late else 'none'
            observations = [{'probe_id': p['id'], 'verdict': 'misaligned' if p['id'] == 'P19' else 'aligned',
                             'evidence_ids': p['allowed_ids'], 'visible_content': 'Current state.',
                             'reason': 'Speech is offset.' if p['id'] == 'P19' else 'Matching current state.'} for p in probes]
            return {'observations': observations, 'dimensions': {'crossmodal_alignment': {'criteria': {
                key: {'status': 'observed', 'score': score, 'severity': severity,
                      'reason': 'Compared actual speech with local frames.', 'limitation': 'Late mismatch.' if late else 'none observed',
                      'high_score_evidence': '' if late else 'All supplied local steps align.',
                      'evidence_ids': probes[-1]['allowed_ids']}
                for key in DIMENSIONS['crossmodal_alignment']['criteria']}}}}
    client = Client()
    result = alignment.assess_alignment(client, packet, audio, 'a', tmp_path / 'alignment')
    assert client.calls == 3
    assert result['coverage']['expected_windows'] == 20
    assert result['coverage']['status'] == ('partial' if failure else 'reviewed')
    assert result['score'] is None if failure else result['score'] == 0
    if not failure:
        assert len(result['observations']) == 20
        assert result['criteria']['synchrony']['score'] == 1


def test_evaluate_persists_dimension_validity_and_acceptance_after_window_failure(tmp_path, monkeypatch):
    from localbench import judge, timeline_review, relation_audit
    from tests.test_localbench_evidence_policy import scored
    packet = frame_packet(tmp_path, 8)
    packet.update(metadata={'duration': 4, 'decoded_duration_s': 4}, audio=[],
                  video_sha256='fixture', sampling='fixture', temporal_limit='fixture')
    monkeypatch.setattr(judge, 'extract', lambda *a, **kw: packet)
    monkeypatch.setattr(judge, 'verify', lambda *a, **k: {'status': 'no_specialized_adapter', 'checks': []})
    monkeypatch.setattr(relation_audit, 'review_relations', lambda *a, **k: {'status': 'reviewed', 'checks': [], 'frames': []})
    monkeypatch.setattr(timeline_review, 'review', lambda *a: {'status': 'partial', 'checks': [], 'unreviewed_frame_ids': ['F000004']})
    dims = scored()['dimensions']
    monkeypatch.setattr(judge, 'assess_teaching', lambda *a: ({k: copy.deepcopy(dims[k]) for k in a[2]}, {}, []))
    monkeypatch.setattr(judge, 'assess_presentation', lambda *a: {k: copy.deepcopy(dims[k]) for k in ('visual_quality', 'temporal_consistency')})
    monkeypatch.setattr(judge, 'assess_alignment', lambda *a: copy.deepcopy(dims['crossmodal_alignment']))
    class Client:
        model = 'fixture'
        def chat(self, *a, **k):
            return {'observations': [{'evidence_ids': ['F000000'], 'reason': 'visible'}]}
    result = judge.evaluate(tmp_path / 'video.mp4', {'id': 'a', 'prompt_text': 'Explain.', 'target_duration_s': 4}, tmp_path / 'eval', Client())
    assert result['dimensions']['visual_quality']['score'] is None
    assert result['dimensions']['visual_quality']['raw_score_before_validity'] == 100
    assert result['scoring']['overall'] is None
    assert result['acceptance']['status'] == 'unverified'
    saved = json.loads((tmp_path / 'eval' / 'scores.json').read_text())
    assert saved['acceptance'] == result['acceptance']


def test_global_context_is_bounded_without_discarding_late_critical_findings():
    checks = [{'id': str(i), 'severity': 'minor'} for i in range(50)] + [{'id': 'late', 'severity': 'critical'}]
    raw = {'status': 'reviewed', 'checks': checks, 'windows': ['large full receipts']}
    summary = timeline_review.context_summary(raw)
    assert summary['checks'][0]['id'] == 'late'
    assert len(summary['checks']) == 32
    assert summary['total_checks'] == 51 and summary['checks_omitted_from_global_context'] == 19
    assert len(raw['checks']) == 51 and raw['windows']
    assert 'windows' not in summary
