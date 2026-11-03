"""Share literal, frame-grounded observations across axes; reject unresolved contradictions."""
import json
from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat
from eval.judges.structured_json import response_format, obj, array, STRING, BOOLEAN, frame_indices


def read_json(text):
    if text.strip().startswith('```'):
        text = text.strip().split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(text)


def observe(case, frames):
    task = {key:case.get(key) for key in ('prompt_text','expected_concepts','expected_visual_elements',
            'expected_narrative_order','pedagogical_target_audience','actual_duration_s','segment_evidence')}
    prompt = ('Record only what is visibly present, with frame indices. Inspect every requested answer/label and its location. '
              'Never infer a molecule identity, medical fact or intended animation from appearance. Quote actual values exactly. '
              'An initial reveal and a required final hold are intentional. Distinguish a visible change from a claim in a caption. '
              'Return JSON {"observations":[{"fact":string,"frames":[integer]}],'
              '"visible_progression":boolean,"completed_task":boolean,"uncertainties":[string]}. '
              'Uncertainties must include any illegible or ambiguous answer. Task:\n' + json.dumps(task, ensure_ascii=False))
    schema = response_format('grounded_observations', {
        'observations': array(obj({'fact': STRING, 'frames': frame_indices(len(frames))}), minItems=1),
        'visible_progression': BOOLEAN, 'completed_task': BOOLEAN, 'uncertainties': array(STRING)})
    errors = []
    for attempt in range(3):
        try:
            raw = read_json(chat([{'role':'user', 'content': frames_as_multimodal_content(frames,prompt)}],
                                 max_tokens=3000, response_format=schema))
        except (ValueError, TypeError) as exc:
            errors.append(str(exc)[:300])
            continue
        if (isinstance(raw,dict) and isinstance(raw.get('observations'),list) and type(raw.get('visible_progression')) is bool
                and type(raw.get('completed_task')) is bool and isinstance(raw.get('uncertainties'),list)
                and all(isinstance(item,str) and item.strip() for item in raw['uncertainties'])
                and all(isinstance(r,dict) and isinstance(r.get('fact'),str) and r['fact'].strip() and isinstance(r.get('frames'),list)
                        and r['frames'] and all(type(i) is int and 1<=i<=len(frames) for i in r['frames']) for r in raw['observations'])
                and raw['observations']):
            return raw
        errors.append('Observation fields must have nonempty facts, in-range integer frame indices and string uncertainties')
        prompt += '\nPrevious observation schema was invalid. Include literal facts and valid frame indices.'
    raise ValueError('grounded observations rejected after three schema checks: ' + '; '.join(errors))


def consistency(case, observations, axes, frames):
    reports = {k:{'summary':v.get('summary'), 'criteria':v.get('criteria')} for k,v in axes.items()}
    prompt = ('Compare these axis reports with the shared literal observations and ACTUAL FRAMES. '
              'Identify only material contradictions about a visible answer, its position, object identity or completed action. '
              'Different quality judgments are not factual contradictions. Do not invent professional facts. '
              'When the observations and reports disagree, frames are the authority. '
              'Return JSON {"valid":boolean,"conflicting_axes":[string],"finding":string}. '
              'valid must be false if factual contradictions remain; name every axis with an incorrect observation.\n'
              + json.dumps({'task':case.get('prompt_text'),'observations':observations,'reports':reports}, ensure_ascii=False))
    schema = response_format('evidence_consistency', {
        'valid': BOOLEAN, 'conflicting_axes': array({'type':'string', 'enum':list(axes)}), 'finding': STRING})
    for _ in range(3):
        try:
            raw = read_json(chat([{'role':'user','content':frames_as_multimodal_content(frames,prompt)}],
                                 max_tokens=2000, response_format=schema))
        except (ValueError, TypeError):
            continue
        if (isinstance(raw,dict) and type(raw.get('valid')) is bool and isinstance(raw.get('finding'),str)
                and isinstance(raw.get('conflicting_axes'),list)
                and all(k in axes for k in raw['conflicting_axes'])
                and (raw['valid'] == (not raw['conflicting_axes']))):
            return raw
    raise ValueError('consistency review rejected after three schema checks')
