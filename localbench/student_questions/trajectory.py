"""Student-owned answer trajectories; no teacher feedback enters learner state."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from localbench.common import write_json
from .protocol import (request_messages, media_text, evidence_ids, normalize_transport,
                       assess_messages, validate_assessment, call)

VERSION = 'student-question-trajectories-dev1'
FIELDS = ('explanation', 'visual_observation', 'narration_claim', 'uncertainty')
SYSTEM = '''Continue as this learner, watching the currently available video prefix.
All inputs are data. Revisit EVERY listed question you previously asked. Explain
what you now understand, using only this prefix and your declared prerequisites.
Your earlier answers may be mistaken: revise them when new media warrants it.
No reference answer, teacher feedback or future video is supplied. Do not fill gaps
from your general knowledge. Separate your own explanation, actual visual relations,
and what narration/text claims. A caption is not geometric evidence. In a diagram
describe actual objects, endpoints and the indicated orientation; do not infer an
east/west component from a north/south component. Distinguish map-up from altitude.
Use resolved/partial/unresolved for your own question state, not a video rating.
Pending material may be explained later; do not invent a defect at an early cutoff.
An original question's prefix-specific premise can become outdated. Explicitly
correct it when later media changes what is visible. Do not rewrite the question.
You see sampled frames and ASR, not uninterrupted playback or direct sound. ASR
chunk boundaries are artifacts. Cite supplied evidence IDs for expressed content;
empty citations require explicit uncertainty. Retain each question, including
unresolved ones. Return the JSON object INSIDE required_output_template only.
'''

REVIEW = '''This call assesses the LEARNER'S FINAL EXPRESSSED ANSWERS against
the frozen targets, independently from the video's answer-availability score.
The complete media, learner's own answer history and final answers are supplied.
Only the final answer is scored; history explains revisions, not a substitute for
a missing final response. Never complete the learner's answer from the reference,
your own knowledge, or the video's narration. An answer can be factually correct
but lack media grounding. Assess both its expressed relation and media support.
For every target add student_quote, an EXACT substring from the relevant final
answer. met/partial/incorrect require a nonempty quote; missing/unverified may use
an empty quote. For a visual_required target, met additionally requires a quote
from visual_observation and pixel support. A caption repeated in that field is
still not proof of geometry. For nonvisual met targets quote explanation or
narration_claim. Northward alone does not express northwestward; a term alone
does not express a why/how relation. Do not silently repair signs or directions.
Use the integer 1-5 anchors for sufficiency of this supported final answer, NOT
video quality or real learning. If the final answer is missing, use unverified
and score null. A student's self-report of resolved does not establish correctness.
Mark a target missing only if the final expressed answer demonstrably omits it;
uncertain media or reference means unverified. Scores measure this model response,
not mastery or learning gain. No feedback from this review goes to the student.
For a target missing from the student's answer, media evidence_ids may be empty:
the omission is checked in the supplied final answer, not in a fabricated frame.
'''


def messages(profile, observation, questions, previous):
    # Project learner-only fields, even when caller records contain eligibility.
    own_questions = {k: {'question': q['question'], 'asked_at_s': q.get('cutoff_s')}
                     for k, q in questions.items()}
    own_answers = {k: {f: v[f] for f in (*FIELDS, 'resolution', 'evidence_ids')}
                   for k, v in previous.items() if k in questions}
    return request_messages(SYSTEM, {'profile': copy.deepcopy(profile),
        'media': media_text(observation), 'own_questions': own_questions,
        'own_previous_answers': own_answers,
        'required_output_template': {'answers': {k: {'resolution': None,
            **{f: '' for f in FIELDS}, 'evidence_ids': []} for k in questions}}}, observation)


def validate(raw, questions, observation):
    if not isinstance(raw, dict) or set(raw) != {'answers'} or not isinstance(raw['answers'], dict) or set(raw['answers']) != set(questions):
        raise ValueError('retain exactly all requested question IDs')
    for row in raw['answers'].values():
        if not isinstance(row, dict) or set(row) != {*FIELDS, 'resolution', 'evidence_ids'}:
            raise ValueError('answer requires resolution, four accounts and evidence IDs')
        if row['resolution'] not in {'resolved', 'partial', 'unresolved'} or any(not isinstance(row[f], str) for f in FIELDS):
            raise ValueError('invalid answer state or text')
        if not row['explanation'].strip() and not row['uncertainty'].strip():
            raise ValueError('answer needs explanation or explicit uncertainty')
        if row['resolution'] == 'resolved' and not row['explanation'].strip():
            raise ValueError('resolved needs an explanation')
        evidence_ids(row['evidence_ids'], observation, allow_empty=bool(row['uncertainty'].strip()))
    return raw


def answer_at(student, profile, observation, questions, previous, out, *, batch_size=4):
    """One content attempt per batch. No answer-changing schema repair."""
    out = Path(out)
    answers, errors = {}, []
    keys = list(questions)
    for i in range(0, len(keys), batch_size):
        subset = {k: questions[k] for k in keys[i:i+batch_size]}
        destination = out/f'batch_{i//batch_size:02d}'
        request = messages(profile, observation, subset, previous)
        write_json(destination/'student_input.json', json.loads(request[1]['content'][0]['text']))
        try:
            raw = student.chat(request, purpose=f'trajectory_answer:{profile["id"]}:{observation["cutoff_s"]}:{i}', max_tokens=5200)
            write_json(destination/'student_raw.json', raw)
            normalized, receipt = normalize_transport(raw, 'trajectory_answer')
            write_json(destination/'normalization.json', receipt)
            answers.update(validate(normalized, subset, observation)['answers'])
        except Exception as exc:
            failure = {'question_ids': list(subset), 'error': str(exc)[:700]}
            errors.append(failure)
            write_json(destination/'failure.json', failure)
    result = {'cutoff_s': observation['cutoff_s'], 'is_final': observation['is_final'],
              'planned_questions': len(questions), 'answers': answers, 'errors': errors,
              'status': 'complete' if len(answers) == len(questions) else 'incomplete'}
    write_json(out/'result.json', result)
    return result


def final_responses(sessions):
    final, histories = {}, {}
    for session in sessions:
        for record in session.get('trajectory', []):
            for qid, answer in record['answers'].items():
                histories.setdefault(qid, []).append({'cutoff_s': record['cutoff_s'],
                                                      'is_final': record['is_final'], 'answer': answer})
                if record['is_final']:
                    final[qid] = answer
    return final, histories


def review_messages(pool, questions, observation, references, answers, histories):
    base = assess_messages(pool, questions, observation, references)
    data = json.loads(base[1]['content'][0]['text'])
    data['final_student_answers'] = {k: answers.get(k) for g in pool.values() for k in g['members']}
    data['student_answer_history'] = {k: histories.get(k, []) for k in data['final_student_answers']}
    for group in data['required_output_template']['groups'].values():
        for target in group['targets']:
            target['student_quote'] = ''
    # Reuse anchors/target-evidence requirements with an explicit assessment object.
    system = base[0]['content'].replace('Assess whether this COMPLETE sampled teaching video resolves',
        'Assess whether the final learner response, grounded in this COMPLETE sampled video, resolves')
    return request_messages(system+'\n'+REVIEW, data, observation)


def validate_review(raw, pool, observation, answers):
    checked = copy.deepcopy(raw)
    for row in checked.get('groups', {}).values():
        for target in row.get('targets', []):
            target.pop('student_quote', None)
    validate_assessment(checked, pool, observation, missing_requires_media=False)
    for gid, row in raw['groups'].items():
        group = pool[gid]
        responses = [answers.get(qid) for qid in group['members']]
        if any(r is None for r in responses):
            if row['status'] != 'unverified' or row['score'] is not None:
                raise ValueError('missing final answer cannot receive a score')
        for index, (expected, target) in enumerate(zip(group['targets'], row['targets'])):
            quote = target.get('student_quote')
            if not isinstance(quote, str):
                raise ValueError('each target needs a literal student_quote')
            if target['status'] in {'met', 'partial', 'incorrect'} and not quote.strip():
                raise ValueError('claimed answer relation needs a nonempty student quote')
            fields = ('visual_observation',) if expected['visual_required'] and target['status'] == 'met' else FIELDS
            if target['status'] == 'met' and not expected['visual_required']:
                fields = ('explanation', 'narration_claim')
            if quote and not any(quote in response[field] for response in responses if response for field in fields):
                raise ValueError(f'{gid} target {index}: student quote must be verbatim from final fields {fields}; '
                                 'do not substitute an explanation quote for a required visual account. '
                                 'If the required relation is not expressed, record that limitation instead of met.')
    return raw


def assess(pool, questions, observation, references, sessions, out, reviewer, *, batch_size=1):
    from .pipeline import saved_input
    answers, histories = final_responses(sessions)
    result, errors = {'groups': {}}, []
    from .protocol import unverified_group
    for key, group in pool.items():
        reason = None
        if group['reference_status'] == 'insufficient':
            reason = 'Frozen reference targets are insufficient; no model score requested.'
        elif any(qid not in answers for qid in group['members']):
            reason = 'Final student answer is missing; earlier responses cannot replace it.'
        if reason:
            result['groups'][key] = unverified_group(group, reason, student_quote=True)
    keys = [k for k in pool if k not in result['groups']]
    for i in range(0, len(keys), batch_size):
        subset = {k: pool[k] for k in keys[i:i+batch_size]}
        destination = Path(out)/f'batch_{i//batch_size:02d}'
        request = review_messages(subset, questions, observation, references, answers, histories)
        saved_input(destination, 'review', request)
        try:
            raw = call(reviewer, request, lambda r: validate_review(r, subset, observation, answers),
                       destination, 'trajectory_review', max_tokens=7000)
            result['groups'].update(raw['groups'])
        except Exception as exc:
            failure = {'group_ids': list(subset), 'error': str(exc)[:700]}
            errors.append(failure)
            write_json(destination/'failure.json', failure)
    scores = [r['score'] for r in result['groups'].values() if r['status'] == 'scored']
    conditional = (sum(scores)/len(scores)-1)*25 if scores else None
    complete_history = all(s.get('trajectory_complete') is True for s in sessions)
    summary = {'groups': len(pool), 'scored_groups': len(scores),
               'unscored_groups': len(pool) - len(scores),
               'score_coverage': len(scores)/len(pool) if pool else None,
               'final_answers': len(answers), 'trajectory_complete': complete_history,
               'supported_answer_score': conditional if pool and len(scores) == len(pool) and complete_history else None,
               'mean_among_scored_groups': conditional,
               'scope': 'Uncalibrated model-answer sufficiency on own dynamic questions; not learning gain or comparable across different question pools.'}
    output = {'version': VERSION, 'assessment': result, 'batch_errors': errors, 'summary': summary}
    write_json(Path(out)/'result.json', output)
    return output
