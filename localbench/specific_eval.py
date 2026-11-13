"""Evaluate a task-bound, pre-frozen question pack with the same three judges."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re

from .common import digest, write_json
from .judge_panel import combine_votes, VERSION as PANEL_VERSION
from .provenance import file_hash

VERSION = 'fixed-specific-v1'


def load_questions(filename, cases, base):
    if not isinstance(filename, str) or not filename:
        raise ValueError('specific_questions must be a path to a frozen JSON question pack')
    path = Path(filename)
    path = path if path.is_absolute() else Path(base)/path
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or raw.get('version') != VERSION or not isinstance(raw.get('cases'), dict):
        raise ValueError('Specific pack requires version fixed-specific-v1 and a cases mapping')
    selected = {}
    for case in cases:
        entry = raw['cases'].get(case['id'], {})
        if not isinstance(entry, dict) or entry.get('case_hash') != digest(case):
            raise ValueError('missing or stale Specific task binding: '+case['id'])
        refs, questions = entry.get('references'), entry.get('questions')
        if not isinstance(refs, dict) or not refs or not isinstance(questions, list) or not questions:
            raise ValueError('Specific task needs nonempty references and questions: '+case['id'])
        for value in refs.values():
            if not isinstance(value, dict) or not isinstance(value.get('statement'), str) or not value['statement'].strip():
                raise ValueError('each Specific reference requires a statement')
        ids = set()
        for q in questions:
            if not isinstance(q, dict) or not isinstance(q.get('id'), str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,47}', q['id']):
                raise ValueError('Specific question needs a safe id')
            if q['id'] in ids:
                raise ValueError('duplicate Specific question id')
            ids.add(q['id'])
            if not isinstance(q.get('question'), str) or not q['question'].strip():
                raise ValueError('Specific question text is required')
            if q.get('reference_status') not in {'draft', 'insufficient'} or not isinstance(q.get('targets'), list):
                raise ValueError('Specific question needs reference_status and targets')
            if q['reference_status'] == 'draft' and not q['targets']:
                raise ValueError('scorable Specific question needs at least one frozen target')
            for target in q['targets']:
                if (not isinstance(target, dict) or not isinstance(target.get('criterion'), str)
                        or not target['criterion'].strip() or type(target.get('visual_required')) is not bool
                        or not isinstance(target.get('source_ids'), list) or not target['source_ids']
                        or any(not isinstance(r, str) or r not in refs for r in target['source_ids'])):
                    raise ValueError('Specific target needs criterion, visual_required and known source_ids')
        selected[case['id']] = copy.deepcopy(entry)
    return {'path': str(path.resolve()), 'sha256': file_hash(path), 'cases': selected}


def full_observation(packet, audio):
    # Shared final-media evidence only. Never use generated narration/scripts.
    transcripts = [{'id': a['id'], 'start_s': a['start_s'], 'end_s': a['end_s'], 'text': a['transcript']}
                   for a in audio if a.get('transcript_valid') and isinstance(a.get('transcript'), str)]
    return {'cutoff_s': packet['metadata']['duration'], 'is_final': True,
            'frames': packet['frames'], 'transcripts': transcripts,
            'evidence_ids': [r['id'] for r in packet['frames']+transcripts],
            'audio_transcript_intervals': [{'start_s': a['start_s'], 'end_s': a['end_s']} for a in transcripts],
            'limitations': packet.get('temporal_limit'),
            'evidence_errors': [{'audio_id': a['id'], 'reason': 'transcript unavailable'}
                                for a in audio if not a.get('transcript_valid')],
            'transcript_boundary_notice': 'Audio chunk boundaries are extraction artifacts, not video defects.'}


def aggregate_assessments(pool, results):
    if len(results) != 3 or len({r['id'] for r in results}) != 3:
        raise ValueError('Specific requires three distinct judge results')
    groups, pending = {}, []
    for key, group in pool.items():
        votes, targets = [], {}
        for member in results:
            row = (member.get('assessment') or {}).get('groups', {}).get(key, {})
            targets[member['id']] = copy.deepcopy(row.get('targets', []))
            votes.append({'judge_id': member['id'], 'status': 'observed' if row.get('status') == 'scored' else 'unverified',
                          'score': row.get('score'), 'reason': row.get('reason', 'Judge did not return a valid assessment.'),
                          'evidence_ids': sorted({e for t in row.get('targets', []) for e in t.get('evidence_ids', [])})})
        combined = combine_votes(votes)
        target_conflicts = []
        for i in range(len(group['targets'])):
            states = {ts[i]['status'] for ts in targets.values() if len(ts) > i}
            if 'met' in states and states & {'missing', 'incorrect'}:
                target_conflicts.append(i)
        if target_conflicts or group['reference_status'] == 'insufficient':
            combined.update(status='unverified', score=None,
                            reason='Frozen reference is insufficient or judges disagree on whether a target is met versus missing/incorrect.')
        combined['targets_by_judge'] = targets
        combined['target_conflicts'] = target_conflicts
        combined['status'] = 'scored' if combined['status'] == 'observed' else 'unverified'
        groups[key] = combined
        if combined['status'] != 'scored':
            pending.append(key)
    valid = [r['score'] for r in groups.values() if r['status'] == 'scored']
    mean = (sum(valid)/len(valid)-1)*25 if valid else None
    complete = bool(pool) and len(valid) == len(pool)
    return {'status': 'complete' if complete else 'incomplete', 'groups': groups,
            'specific_score': mean if complete else None, 'mean_among_scored_questions': mean,
            'planned_questions': len(pool), 'scored_questions': len(valid), 'pending_questions': pending,
            'score_coverage': len(valid)/len(pool) if pool else 0}


def evaluate_specific(case, entry, evaluation_dir, members):
    from .student_questions.pipeline import assess_frozen
    if len(members) != 3 or entry['case_hash'] != digest(case):
        raise ValueError('Specific requires three judges and a matching frozen task')
    directory = Path(evaluation_dir)
    packet = json.loads((directory/'evidence/packet.json').read_text())
    audio = json.loads((directory/'actual_audio.json').read_text())
    observation = full_observation(packet, audio)
    out = directory/'specific'
    pool = {q['id']: {k: copy.deepcopy(v) for k, v in q.items() if k != 'id'} for q in entry['questions']}
    write_json(out/'frozen_questions.json', entry)
    write_json(out/'observation.json', observation)
    def one(pair):
        spec, client = pair
        destination = out/'judges'/spec.id
        try:
            assessment, errors = assess_frozen(copy.deepcopy(pool), {}, copy.deepcopy(observation),
                                               copy.deepcopy(entry['references']), destination, client)
        except Exception as exc:
            assessment, errors = {'groups': {}}, [{'error_type': type(exc).__name__,
                'error': str(exc).replace(spec.service.api_key, '[redacted]')[:600]}]
        result = {'id': spec.id, 'assessment': assessment, 'errors': errors}
        write_json(destination/'assessment.json', result)
        return result
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = list(workers.map(one, members))
    result = {**aggregate_assessments(pool, results), 'version': VERSION+'+'+PANEL_VERSION,
              'case_id': case['id'], 'case_hash': digest(case), 'video_sha256': packet['video_sha256'],
              'question_pack_hash': digest(entry), 'shared_observation_hash': digest(observation),
              'members': [{**spec.public(), 'assessment_path': str((out/'judges'/spec.id/'assessment.json').resolve())}
                          for spec, _ in members], 'judge_errors': {r['id']: r['errors'] for r in results},
              'scope': 'Fixed task-specific video assessment, independent of General and student diagnostics.'}
    write_json(out/'scores.json', result)
    write_json(out/'review_queue.json', {k: result['groups'][k] for k in result['pending_questions']})
    return result
