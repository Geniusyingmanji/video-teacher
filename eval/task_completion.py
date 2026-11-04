"""Check every current obligation against frames, independently of numeric axes."""
import json
from eval.evidence_prompt import prompt_json
from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat
from eval.judges.structured_json import response_format, obj, array, STRING, frame_indices
from eval.grounded_observations import read_json
from generation.task_requirements import requirements
from eval.numeric_evidence import arithmetic_anchors

VERSION = 'task-completion-v1'


def validate(raw, required, frame_count, segments=None):
    rows = raw.get('requirements') if isinstance(raw, dict) else None
    expected = {row['id'] for row in required}
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError('every task requirement needs exactly one review')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('id') not in expected or row['id'] in seen:
            raise ValueError('unknown or duplicate requirement')
        seen.add(row['id'])
        if row.get('status') not in ('met', 'missing', 'incorrect', 'uncertain'):
            raise ValueError('invalid requirement status')
        frames = row.get('evidence_frames')
        if not isinstance(frames, list) or any(type(i) is not int or not 1 <= i <= frame_count for i in frames):
            raise ValueError('invalid requirement evidence frames')
        citations=row.get('segment_citations',[])
        if segments is not None:
            if not isinstance(citations,list):raise ValueError('segment citations must be an array')
            by_segment={s['id']:s for s in segments}
            for citation in citations:
                if type(citation.get('segment_id')) is not int or citation['segment_id'] not in by_segment:
                    raise ValueError('unknown cited segment')
                segment=by_segment[citation['segment_id']]
                evidence=next((r for r in segment['requirement_evidence'] if r['id']==row['id']),None)
                allowed=set(evidence['evidence_frames']) if evidence else set()
                cited=citation.get('frames')
                if not isinstance(cited,list) or not cited or any(type(i) is not int or i not in allowed for i in cited):
                    raise ValueError('segment citation not supported by inspected requirement evidence')
        elif citations:
            raise ValueError('segment citations require actual segment observations')
        if row['status'] in ('met', 'incorrect') and not frames and not citations:
            raise ValueError('visible claim requires frame evidence')
        for key in ('finding', 'expected', 'observed'):
            if not isinstance(row.get(key), str) or not row[key].strip() or len(row[key]) > 480:
                raise ValueError(f'missing {key}')
    by_id = {row['id']: row for row in rows}
    ordered = [{**item, **by_id[item['id']]} for item in required]
    failed = [row['id'] for row in ordered if row['status'] != 'met']
    return {'version': VERSION, 'valid': True, 'passed': not failed,
            'requirements': ordered, 'failures': failed,
            'coverage': sum(row['status'] == 'met' for row in ordered) / len(ordered)}


def review(case, frames):
    required = requirements(case)
    prompt = ('Audit task completion against the ACTUAL ordered video frames. Review EVERY obligation below. '
              'For the full prompt check every clause, prohibition, requested answer and target location. '
              'Use the supplied exact arithmetic anchors for sums; never invent contrary arithmetic. '
              'Quantities and relationships in the diagram can satisfy an equation requirement; do not demand '
              'literal equation text unless the task explicitly requires writing that equation. '
              'For a sequence check the actual ordered actions, not only the final labels. '
              'Text claiming flow, sorting, explanation or an audit does not demonstrate that action. '
              'A caption saying an answer or classification is correct is not evidence of correctness: inspect '
              'the actual object-to-category correspondence, visible labels, values and targets. '
              'Do not demand extra content absent from the task. Mark uncertain when correctness or legibility '
              'cannot be established; never guess molecule identity or unseen movement. '
              'Keep expected, observed and finding concise (at most 20 words each); do not repeat long identifiers. '
              'Use status met only when ALL parts of that obligation are visibly satisfied. '
              'Write the literal observation and finding BEFORE deciding the status. '
              'Return JSON {"requirements":[{"id":string,"expected":string,"observed":string,'
              '"finding":string,"evidence_frames":[1-based integers],"status":"met|missing|incorrect|uncertain"}]}. '
              'For absent evidence use an empty array and explain what was inspected.\n'
              + prompt_json({'requirements':required, 'verified_arithmetic':arithmetic_anchors(required)}))
    segments=case.get('segment_evidence')
    if segments is not None:
        prompt += ('\nThis is a long lesson. All ten-second windows were separately inspected. '
                   'Combine supported observations across windows to check complete obligations, order and consistent states. '
                   'Partial evidence in one window is not by itself complete fulfillment. '
                   'Cite overview images in evidence_frames, and separately cite ledger evidence as '
                   'segment_citations:[{segment_id:int,frames:[local frame indices]}]. '
                   'Copy only citations actually recorded for this requirement in that segment. '
                   'No useful evidence means uncertain or missing. Model observations remain fallible; '
                   'reconcile contradictions rather than selecting the favorable report.\nSEGMENT EVIDENCE:\n'
                   +prompt_json(segments))
    row_schema={
        'id': {'type':'string', 'enum':[r['id'] for r in required]},
        'expected': {'type':'string','minLength':1,'maxLength':480},
        'observed': {'type':'string','minLength':1,'maxLength':480},
        'finding': {'type':'string','minLength':1,'maxLength':480},
        'evidence_frames': frame_indices(len(frames)),
        'status': {'type':'string', 'enum':['met','missing','incorrect','uncertain']}}
    if segments is not None:
        row_schema['segment_citations']=array(obj({'segment_id':{'type':'integer','enum':[s['id'] for s in segments]},
                                                 'frames':array({'type':'integer','minimum':1,'maximum':24},minItems=1)}),maxItems=36)
    schema = response_format('task_completion', {'requirements':array(obj(row_schema),minItems=len(required),maxItems=len(required))})
    errors = []
    for _ in range(3):
        try:
            raw = read_json(chat([{'role':'user', 'content': frames_as_multimodal_content(frames, prompt)}],
                                 max_tokens=6000, response_format=schema))
            return {**validate(raw, required, len(frames),segments), 'validation_errors': errors,
                    'verified_arithmetic': arithmetic_anchors(required)}
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(str(exc)[:300])
            prompt += '\nSchema correction: ' + errors[-1]
    raise ValueError('task completion schema rejected: ' + '; '.join(errors))


def defects(review):
    """Apply the existing severe omission cap only to explicit observed failures."""
    return [{'axis': 'conceptual_correctness', 'axis_cap': 40.0, 'overall_cap': 50.0,
             'reason': 'task_requirement_' + row['status'] + ':' + row['id'],
             'evidence_frames': row['evidence_frames'], 'segment_citations':row.get('segment_citations',[]), 'finding': row['finding']}
            for row in review.get('requirements', []) if row['status'] in ('missing', 'incorrect')]
