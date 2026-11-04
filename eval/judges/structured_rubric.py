"""Schema-constrained rubric judgments with bounded, evidence-preserving retries."""
import json


def response_format(ids, frame_count):
    return {'type': 'json_schema', 'json_schema': {'name': 'evidence_rubric', 'strict': True,
        'schema': {'type': 'object', 'additionalProperties': False,
            'required': ['criteria', 'summary'], 'properties': {
                'summary': {'type': 'string'},
                'criteria': {'type': 'array', 'minItems': len(ids), 'maxItems': len(ids),
                    'items': {'type': 'object', 'additionalProperties': False,
                        'required': ['id', 'applicable', 'score', 'evidence_frames', 'finding'],
                        'properties': {
                            'id': {'type': 'string', 'enum': list(ids)},
                            'finding': {'type': 'string', 'minLength': 1, 'maxLength': 240},
                            'evidence_frames': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1, 'maximum': frame_count}},
                            'applicable': {'type': 'boolean'},
                            'score': {'anyOf': [{'type': 'number', 'enum': [1,1.5,2,2.5,3,3.5,4,4.5,5]}, {'type': 'null'}]}}}}}}}}


def judge(chat, messages, ids, frame_count, validate, *, attempts=3):
    errors = []
    for attempt in range(attempts):
        request = list(messages)
        if errors:
            request.append({'role': 'user', 'content': 'The previous response failed validation: '
                + errors[-1] + '. Return all required criteria using the schema. Recheck the supplied frames. '
                'Do not invent evidence, convert invalid values silently, or change the rubric.'})
        try:
            raw = chat(request, max_tokens=3500, response_format=response_format(ids, frame_count))
            result = validate(json.loads(raw))
            result['structured_validation'] = {'attempts': attempt+1, 'errors': errors}
            return result
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
    raise ValueError('Rubric rejected after bounded retries: ' + '; '.join(errors))
