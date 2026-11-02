"""Share literal, frame-grounded observations across axes; reject unresolved contradictions."""
import json
from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat


def read_json(text):
    if text.strip().startswith('```'):
        text = text.strip().split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(text)


def observe(case, frames):
    task = {key:case.get(key) for key in ('prompt_text','expected_concepts','expected_visual_elements',
            'expected_narrative_order','pedagogical_target_audience','actual_duration_s')}
    prompt = ('Record only what is visibly present, with frame indices. Inspect every requested answer/label and its location. '
              'Never infer a molecule identity, medical fact or intended animation from appearance. Quote actual values exactly. '
              'An initial reveal and a required final hold are intentional. Distinguish a visible change from a claim in a caption. '
              'Return JSON {"observations":[{"fact":string,"frames":[integer]}],'
              '"visible_progression":boolean,"completed_task":boolean,"uncertainties":[string]}. '
              'Uncertainties must include any illegible or ambiguous answer. Task:\n' + json.dumps(task, ensure_ascii=False))
    for attempt in range(3):
        try:
            raw = read_json(chat([{'role':'user', 'content': frames_as_multimodal_content(frames,prompt)}],
                                 max_tokens=1800, response_format={'type':'json_object'}))
        except (ValueError, TypeError):
            continue
        if (isinstance(raw,dict) and isinstance(raw.get('observations'),list) and type(raw.get('visible_progression')) is bool
                and type(raw.get('completed_task')) is bool and isinstance(raw.get('uncertainties'),list)
                and all(isinstance(r,dict) and isinstance(r.get('fact'),str) and isinstance(r.get('frames'),list)
                        and r['frames'] and all(type(i) is int and 1<=i<=len(frames) for i in r['frames']) for r in raw['observations'])
                and raw['observations']):
            return raw
        prompt += '\nPrevious observation schema was invalid. Include literal facts and valid frame indices.'
    raise ValueError('grounded observations rejected after three schema checks')


def consistency(case, observations, axes, frames):
    reports = {k:{'summary':v.get('summary'), 'criteria':v.get('criteria')} for k,v in axes.items()}
    prompt = ('Compare these axis reports with the shared literal observations and ACTUAL FRAMES. '
              'Identify only material contradictions about a visible answer, its position, object identity or completed action. '
              'Different quality judgments are not factual contradictions. Do not invent professional facts. '
              'When the observations and reports disagree, frames are the authority. '
              'Return JSON {"valid":boolean,"conflicting_axes":[string],"finding":string}. '
              'valid must be false if factual contradictions remain; name every axis with an incorrect observation.\n'
              + json.dumps({'task':case.get('prompt_text'),'observations':observations,'reports':reports}, ensure_ascii=False))
    for _ in range(3):
        try:
            raw = read_json(chat([{'role':'user','content':frames_as_multimodal_content(frames,prompt)}],
                                 max_tokens=1500, response_format={'type':'json_object'}))
        except (ValueError, TypeError):
            continue
        if (isinstance(raw,dict) and type(raw.get('valid')) is bool and isinstance(raw.get('finding'),str)
                and isinstance(raw.get('conflicting_axes'),list)
                and all(k in axes for k in raw['conflicting_axes'])
                and (raw['valid'] == (not raw['conflicting_axes']))):
            return raw
    raise ValueError('consistency review rejected after three schema checks')
