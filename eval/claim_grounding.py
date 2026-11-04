"""Independent, localized verification of observations that trigger hard score caps.

This is a sampled-frame verification, not human certification. The verifier sees
no prior numeric score. Uncertain factual claims cannot authorize a hard cap.
"""
import copy
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image

from eval.judges.gpt55 import chat, judge_config
from eval.judges.structured_json import response_format, obj, array
from eval.frame_extractor import frames_as_multimodal_content, frame_to_data_url
from eval.instructional_video import _ask

VERSION = 'localized-claim-grounding-v1'


def samples_for_claim(row, claim):
    presentation = row.get('instructional_presentation', {})
    if claim.get('evidence_scope') == 'segment_local_frames':
        window = next(w for w in presentation['segments'] if w['id'] == claim['segment_id'])
        times = window['timestamps_s']
    else:
        times = presentation.get('overview_timestamps_s', [])
    cited = sorted(set(claim.get('frames') or claim.get('evidence_frames') or []))
    if not cited:
        cited = list(range(1, len(times)+1))
    if not cited or any(type(i) is not int or not 1 <= i <= len(times) for i in cited):
        raise ValueError('claim has no reconstructable actual-frame evidence')
    if len(cited) == 1:
        neighbors = [i for i in range(1, len(times)+1) if abs(times[i-1]-times[cited[0]-1]) >= 1]
        if neighbors:
            cited.append(min(neighbors, key=lambda i: abs(times[i-1]-times[cited[0]-1])))
    return [{'source_frame_reference':i, 'time_s':times[i-1]} for i in sorted(cited)]


def verify(row, claim, *, chat_fn=None):
    sample_info = samples_for_claim(row, claim)
    path = Path(row['video_path'])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != row['video_sha256']:
        raise ValueError('source video changed before claim verification')
    cap = cv2.VideoCapture(str(path))
    frames = []
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        for sample in sample_info:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(sample['time_s']*fps))
            ok, pixels = cap.read()
            if not ok:
                raise ValueError('claim evidence frame could not be decoded')
            frame = Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
            frame.info['video_timestamp_s'] = sample['time_s']
            frames.append(frame)
    finally:
        cap.release()
    prompt = ('Independently VERIFY this factual allegation against the exact supplied video frames. '
        'It may be false. Do not assume the previous reviewer was correct. Do not assign a quality score. '
        'First transcribe the actual visible text/object state in EACH image. Then decide whether the '
        'allegation is supported, contradicted, or unresolved. Distinguish low-contrast fading ghosts '
        'from essential unreadable overlapping text. A single transient crossfade does not establish '
        'a persistent severe defect. For a severe display defect require essential content actually '
        'unreadable in at least TWO settled images spanning at least one second. A clean settled image '
        'contradicts a claim that it contains severe overlap. Do not invent unseen text or motion. '
        'confirmed means the specific allegation is observed; rejected means the images contradict it; '
        'uncertain means insufficient evidence. Keep observations concise and literal.\n'
        + json.dumps({'allegation':claim.get('finding'), 'kind':claim.get('kind'),
                      'severity':claim.get('severity'), 'source_frames':sample_info}, ensure_ascii=False))
    content = frames_as_multimodal_content(frames, prompt)
    region = claim.get('region')
    if region:
        if len(region) != 4 or not 0 <= region[0] < region[2] <= 1 or not 0 <= region[1] < region[3] <= 1:
            raise ValueError('invalid claim region')
        for i, frame in enumerate(frames, 1):
            w, h = frame.size
            crop = frame.crop((int(region[0]*w), int(region[1]*h), int(region[2]*w), int(region[3]*h)))
            content.extend([{'type':'text','text':f'Detail crop of supplied frame {i}; actual pixels, same time.'},
                            {'type':'image_url','image_url':{'url':frame_to_data_url(crop)}}])
    schema = response_format('verify_factual_claim', {
        'observations':array(obj({'frame':{'type':'integer','minimum':1,'maximum':len(frames)},
                                 'visible_state':{'type':'string','minLength':1,'maxLength':240}}),
                             minItems=len(frames), maxItems=len(frames)),
        'decision':{'type':'string','enum':['confirmed','rejected','uncertain']},
        'supporting_frames':array({'type':'integer','minimum':1,'maximum':len(frames)}),
        'persistent_in_settled_frames':{'type':'boolean'},
        'essential_content_unreadable':{'type':'boolean'},
        'reason':{'type':'string','minLength':1,'maxLength':480}})
    def validate(raw):
        if len(raw.get('observations', [])) != len(frames) or {r.get('frame') for r in raw['observations']} != set(range(1,len(frames)+1)):
            raise ValueError('every actual supplied frame needs a literal observation')
        for observation in raw['observations']:
            if not isinstance(observation.get('visible_state'), str) or not observation['visible_state'].strip():
                raise ValueError('literal frame observation missing')
        if raw.get('decision') not in ('confirmed','rejected','uncertain'):
            raise ValueError('invalid factual verification decision')
        ids = raw.get('supporting_frames')
        if not isinstance(ids, list) or not ids or any(type(i) is not int or not 1 <= i <= len(frames) for i in ids):
            raise ValueError('decision requires actual image references')
        if any(type(raw.get(k)) is not bool for k in ('persistent_in_settled_frames','essential_content_unreadable')):
            raise ValueError('verification flags must be booleans')
        if raw['decision'] == 'confirmed' and claim.get('severity') == 'severe':
            if (len(set(ids)) < 2 or max(sample_info[i-1]['time_s'] for i in ids)-min(sample_info[i-1]['time_s'] for i in ids) < 1
                    or not raw['persistent_in_settled_frames'] or not raw['essential_content_unreadable']):
                raise ValueError('severe claim lacks repeated settled essential-content evidence')
        if not isinstance(raw.get('reason'),str) or not raw['reason'].strip():
            raise ValueError('verification reason missing')
        return raw
    if chat_fn is None:
        raw = _ask([{'role':'user','content':content}], schema, validate, tokens=2000)
    else:
        raw = validate(json.loads(chat_fn([{'role':'user','content':content}], response_format=schema)))
    return {**raw, 'version':VERSION, 'judge':judge_config(), 'video_sha256':digest,
            'claim':copy.deepcopy(claim), 'sample_info':sample_info,
            'verification_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'independent_model_observation_of_exact_sampled_frames_and_crops_not_human_certification'}


def verify_presentation(row, *, previous=None, checkpoint=None):
    """Retain raw claims; only confirmed allegations can authorize severe caps."""
    cached = {r['claim_key']:r for r in (previous or [])}
    results = []
    for claim in row.get('instructional_presentation', {}).get('issues', []):
        if claim.get('severity') != 'severe' or claim.get('essential') is not True:
            continue
        key = hashlib.sha256(json.dumps(claim, sort_keys=True).encode()).hexdigest()
        old = cached.get(key)
        if (old and old.get('decision') in ('confirmed', 'rejected') and old.get('video_sha256') == row.get('video_sha256')
                and old.get('verification_code_sha256') == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                and old.get('judge') == judge_config()):
            result = old
        else:
            try:
                result = {**verify(row, claim), 'claim_key':key}
            except Exception as exc:
                result = {'claim_key':key, 'claim':claim, 'decision':'uncertain',
                          'error':f'{type(exc).__name__}: {exc}'[:600]}
        results.append(result)
        if checkpoint:
            checkpoint(results)
    return {'version':VERSION, 'claims':results,
            'all_claims_confirmed':all(r['decision'] == 'confirmed' for r in results),
            'rejected_claims':[r for r in results if r['decision'] == 'rejected'],
            'uncertain_claims':[r for r in results if r['decision'] == 'uncertain']}
