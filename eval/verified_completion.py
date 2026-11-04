"""Per-requirement citation schemas: the judge cannot borrow another obligation's frames."""
import json
from eval.evidence_prompt import prompt_json

from eval.task_completion import validate
from eval.grounded_observations import read_json
from eval.numeric_evidence import arithmetic_anchors
from generation.task_requirements import requirements
from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.structured_json import response_format, obj, array, frame_indices
from eval.judges.gpt55 import chat
from eval.instructional_video import ledger_for_judge


def completion_schema(required, count, segments):
    properties = {}
    for requirement in required:
        fields = {k:{'type':'string','minLength':1,'maxLength':240} for k in ('expected','observed','finding')}
        fields['evidence_frames'] = frame_indices(count)
        fields['status'] = {'type':'string','enum':['met','missing','incorrect','uncertain']}
        if segments is not None:
            choices = []
            for segment in segments:
                record = next((r for r in segment.get('requirement_evidence',[]) if r['id']==requirement['id']),{})
                allowed = sorted(set(record.get('evidence_frames',[])))
                if allowed:
                    choices.append(obj({'segment_id':{'type':'integer','enum':[segment['id']]},
                        'frames':array({'type':'integer','enum':allowed},minItems=1,maxItems=len(allowed))}))
            fields['segment_citations'] = (array({'anyOf':choices},maxItems=len(choices)) if choices else
                array(obj({'segment_id':{'type':'integer'},'frames':frame_indices(24)}),maxItems=0))
        properties[requirement['id']] = obj(fields)
    return response_format('completion_with_grounded_citations', {'requirements':obj(properties)})


def review(case, frames):
    required = requirements(case)
    segments = case.get('segment_evidence')
    prompt_segments = (ledger_for_judge(segments) if segments and not any('not_shown_requirement_ids' in w for w in segments)
                       else segments)
    schema = completion_schema(required,len(frames),segments)
    prompt = ('Audit EVERY original task requirement against the ACTUAL images and separately inspected video windows. '
        'Return one object entry per exact requirement ID. Record literal expected/observed/finding before status. '
        'Keep each description under 20 words. Do not infer a demonstrated process from captions claiming success. '
        'Use met only when the complete obligation is visibly satisfied. Mark uncertainty explicitly. '
        'A requirement may cite only its own recorded frames in each video window; the schema enumerates those references. '
        'Never borrow another requirement\'s references. An absent local record is not evidence of fulfillment. '
        'Use exact arithmetic anchors; do not invent contrary arithmetic or professional facts. '
        'ASR is actual-track evidence, not the intended script.\n' + prompt_json({
        'requirements':required,'verified_arithmetic':arithmetic_anchors(required),
        'video_windows':prompt_segments,'actual_spoken_segments':case.get('actual_spoken_segments',[])}))
    errors = []
    for _ in range(3):
        try:
            raw = read_json(chat([{'role':'user','content':frames_as_multimodal_content(frames,prompt)}],
                                 response_format=schema,max_tokens=6000))
            # Explicit legacy-array compatibility; every value still passes the same strict validator.
            if isinstance(raw,dict) and isinstance(raw.get('requirements'),dict):
                raw = {'requirements':[{'id':key,**value} for key,value in raw['requirements'].items()]}
            return {**validate(raw,required,len(frames),segments),'validation_errors':errors,
                    'verified_arithmetic':arithmetic_anchors(required),'citation_schema':'per-requirement-enumerated-v1'}
        except (ValueError,TypeError,KeyError) as exc:
            errors.append(str(exc)[:300])
            prompt += '\nValidation correction: '+errors[-1]
    raise ValueError('grounded completion review rejected: '+'; '.join(errors))
