"""Required, bounded calls covering every selected dense/change-boundary frame."""
from __future__ import annotations

import json
from pathlib import Path

from .common import write_json
from .evidence import image_content
from .rubric import DIMENSIONS

VERSION = 'timeline-window-review-v1'


def windows(frames, size=16):
    if size < 2:
        raise ValueError('window size must allow adjacent frames')
    result = []
    start = 0
    while start < len(frames):
        batch = frames[start:start + size]
        result.append(batch)
        if start + size >= len(frames):
            break
        start += size - 1  # Consecutive calls share the boundary frame.
    return result


def validate(raw, frames):
    ids = {f['id'] for f in frames}
    if not isinstance(raw, dict):
        raise ValueError('timeline review must be an object')
    seen = raw.get('reviewed_frame_ids')
    if not isinstance(seen, list) or len(seen) != len(ids) or set(seen) != ids:
        raise ValueError('every supplied timeline frame must be reviewed exactly once')
    findings = raw.get('findings')
    if not isinstance(findings, list) or not isinstance(raw.get('summary'), str) or not raw['summary'].strip():
        raise ValueError('timeline findings and concrete summary required')
    for finding in findings:
        if not isinstance(finding, dict) or finding.get('verdict') not in {'fail', 'unverified'}:
            raise ValueError('invalid timeline finding verdict')
        if finding.get('severity') not in {'minor', 'major', 'critical'}:
            raise ValueError('invalid timeline severity')
        refs = finding.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(x not in ids for x in refs):
            raise ValueError('timeline finding must cite supplied frames')
        affected = finding.get('affected')
        if not isinstance(affected, list) or not affected:
            raise ValueError('timeline finding needs affected criteria')
        for key in affected:
            parts = key.split('.') if isinstance(key, str) else []
            if len(parts) != 2 or parts[0] not in DIMENSIONS or parts[1] not in DIMENSIONS[parts[0]]['criteria']:
                raise ValueError('unknown affected timeline criterion')
        if not isinstance(finding.get('reason'), str) or not finding['reason'].strip():
            raise ValueError('concrete timeline finding required')
    return findings


def review(client, packet, audio, case, out):
    out = Path(out)
    selected = packet.get('review_frames', [])
    batches = windows(selected)
    reviewed = set(); checks = []; errors = []; receipts = []
    rubric = {name: list(d['criteria']) for name, d in DIMENSIONS.items()}
    for index, batch in enumerate(batches):
        start, end = batch[0]['time_s'], batch[-1]['time_s']
        speech = [{k: a.get(k) for k in ('id', 'transcript', 'utterances', 'start_s', 'end_s',
                                         'transcript_valid', 'narration_presence', 'transcript_guard')}
                  for a in audio if a['start_s'] <= end and a['end_s'] >= start]
        content = [{'type': 'text', 'text': json.dumps({
            'task': case.get('prompt_text'), 'start_s': start, 'end_s': end,
            'actual_audio': speech, 'criteria': rubric,
            'instruction': 'Inspect ALL ordered frames in this window, including changes and captions. '
            'Check transient wrong states, stale captions, disappearing labels, unreadable/overlapping text, '
            'incorrect concepts and step transitions. Use transcript only when transcript_valid; do not invent missing speech. '
            'These are local review boundaries, not video cuts: do not penalize a continuing action, sentence or hold '
            'for extending beyond this batch. Never infer a whole-video task omission from this local window; '
            'report only defects supported by the supplied interval. Whole-video coverage is assessed globally. '
            'Speech chunk timing is approximate; timed alignment is separately checked. '
            'Return JSON {reviewed_frame_ids:[every supplied ID exactly once],summary:concrete observation,'
            'findings:[{verdict:fail|unverified,severity:minor|major|critical,affected:[dimension.criterion],'
            'evidence_ids:[supplied IDs],reason:concrete evidence}]}. '
            'An empty findings list means no defect observed here, not proof about unobserved times. '
            'Use unverified for unreadable or conflicting essential evidence, not for observed defects. '
            'Do not invent task requirements or judge unsupplied frames.'}, ensure_ascii=False)}]
        for frame in batch:
            content.extend(image_content(frame))
        messages = [{'role': 'user', 'content': content}]
        try:
            for attempt in range(2):
                raw = client.chat(messages, purpose=f'timeline_window:{case["id"]}:{index}:{attempt}', max_tokens=3500)
                write_json(out / f'raw_{index}_{attempt}.json', raw)
                try:
                    findings = validate(raw, batch)
                    break
                except (ValueError, TypeError) as exc:
                    if attempt:
                        raise
                    messages += [{'role': 'assistant', 'content': json.dumps(raw)},
                                 {'role': 'user', 'content': 'Repair this schema against the SAME frames: ' + str(exc)}]
            reviewed.update(f['id'] for f in batch)
            receipts.append({'window': index, 'start_s': start, 'end_s': end,
                             'frame_ids': [f['id'] for f in batch], 'summary': raw['summary']})
            checks.extend({'id': f'timeline_{index}_{j}', **f} for j, f in enumerate(findings))
        except Exception as exc:
            errors.append({'window': index, 'frame_ids': [f['id'] for f in batch], 'error': str(exc)[:500]})
    sampling=packet.get('review_sampling',{})
    if sampling.get('required_scope')=='all_decoded_frames' and len(selected)!=packet['metadata']['decoded_frame_count']:
        errors.append({'error':'Full-frame review inventory does not match decoded frame count.'})
    result = {'version': VERSION, 'status': 'reviewed' if batches and not errors else 'partial',
              'requested_frames': len(selected), 'reviewed_frames': len(reviewed),
              'unreviewed_frame_ids': [f['id'] for f in selected if f['id'] not in reviewed],
              'checks': checks, 'windows': receipts, 'errors': errors,
              'sampling': packet.get('review_sampling'),
              'scope': 'All selected dense/change-boundary frames, not continuous human audiovisual certification.'}
    write_json(out / 'review.json', result)
    return result


def context_summary(result, limit=32):
    """Bound global-judge context; full receipts/checks still drive validity."""
    priority = {'critical': 0, 'major': 1, 'minor': 2}
    checks = sorted(result.get('checks', []), key=lambda c: priority.get(c.get('severity'), 3))
    return {k: result.get(k) for k in ('version', 'status', 'requested_frames', 'reviewed_frames')} | {
        'checks': checks[:limit], 'total_checks': len(checks),
        'checks_omitted_from_global_context': max(0, len(checks) - limit),
        'errors_count': len(result.get('errors', [])),
        'scope': 'Bounded summary only; every original check remains in saved review and validity/acceptance.'}
