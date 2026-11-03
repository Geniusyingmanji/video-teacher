"""Project-authored review of readable layout and information conveyed by time.

Research motivations and attribution: docs/SCORING_V7_DESIGN.md. This module
contains no external implementation, copied rubric, or learned reward weights.
"""
import json
import math

import numpy as np

from eval.frame_extractor import frames_as_multimodal_content
from eval.judges.gpt55 import chat
from eval.judges.structured_json import obj, array, response_format, frame_indices
from generation.task_requirements import requirements

VERSION = 'instructional-video-v2-segmented'
CRITERIA = {
    'layout_readability': 'Essential text, marks and diagrams are readable, separated and unobscured at delivery resolution.',
    'visual_explanation': 'Visible correspondences, comparisons or operations make the requested relationship understandable.',
    'temporal_contribution': 'Time reveals an inspectable operation or reasoning dependency beyond the strongest final still.',
    'representation_integrity': 'Objects, connectors, arrows, identities and states form a coherent representation of the task.',
    'instructional_focus': 'Relevant information is selected and organized; captions do not merely declare success.',
    'perceptual_pacing': 'Changes can be followed and important states inspected within actual playback time.',
}
SUBSTANTIVE = {'operation', 'reasoning', 'comparison'}
TEXT = {'type':'string', 'minLength':1, 'maxLength':480}
BOX = array({'type':'number', 'minimum':0, 'maximum':1}, minItems=4, maxItems=4)


def _box(value):
    if (not isinstance(value,list) or len(value)!=4
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in value)
            or not 0<=value[0]<value[2]<=1 or not 0<=value[1]<value[3]<=1):
        raise ValueError('region must be a nonempty normalized image rectangle')


def _indices(value, count):
    if not isinstance(value,list) or any(type(i) is not int or not 1<=i<=count for i in value):
        raise ValueError('frame citations must be in-range 1-based integers')


def validate(raw, count):
    if not isinstance(raw,dict):
        raise ValueError('review must be an object')
    rows=raw.get('criteria')
    if not isinstance(rows,list) or len(rows)!=len(CRITERIA):
        raise ValueError('all six presentation criteria required')
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or row.get('id') not in CRITERIA or row['id'] in seen:
            raise ValueError('unknown or duplicate presentation criterion')
        seen.add(row['id'])
        if type(row.get('score')) is not int or not 1<=row['score']<=5:
            raise ValueError('criterion score must be integer 1..5')
        _indices(row.get('evidence_frames'),count)
        if row['score']>=3 and not row['evidence_frames']:
            raise ValueError('positive rating needs visible evidence')
        if not isinstance(row.get('finding'),str) or not row['finding'].strip():
            raise ValueError('criterion finding missing')
    for field in ('events','issues'):
        if not isinstance(raw.get(field),list) or len(raw[field])>12:
            raise ValueError(f'{field} must be an array of at most twelve records')
    for event in raw['events']:
        if event.get('kind') not in SUBSTANTIVE|{'reveal','decoration'}:
            raise ValueError('unknown event kind')
        a,b=event.get('before_frame'),event.get('after_frame')
        if type(a) is not int or type(b) is not int or not 1<=a<b<=count:
            raise ValueError('event needs ordered before and after frames')
        _box(event.get('region'))
        for field in ('before','after','learning_value'):
            if not isinstance(event.get(field),str) or not event[field].strip():
                raise ValueError('event description missing')
    for issue in raw['issues']:
        if issue.get('severity') not in ('minor','severe') or type(issue.get('essential')) is not bool:
            raise ValueError('invalid issue severity or applicability')
        _indices(issue.get('frames'),count);_box(issue.get('region'))
        if not issue['frames'] or not isinstance(issue.get('finding'),str) or not issue['finding'].strip():
            raise ValueError('issue must be located and explained')
        if issue.get('kind') not in ('overlap','occlusion','illegible','clipped','disconnected','wrong_state'):
            raise ValueError('unknown presentation defect')
    if not isinstance(raw.get('summary'),str) or not raw['summary'].strip():
        raise ValueError('review summary missing')
    return raw


def _ask(messages, schema, validator, tokens=4000):
    errors=[]
    for _ in range(3):
        request=list(messages)
        if errors:
            request.append({'role':'user','content':'Response validation failed: '+errors[-1]+'. Reinspect the same evidence and obey the schema.'})
        try:
            value=validator(json.loads(chat(request,max_tokens=tokens,response_format=schema)))
            return {**value,'validation_errors':errors}
        except (ValueError,TypeError,KeyError) as exc:
            errors.append(str(exc)[:300])
    raise ValueError('instructional review rejected after bounded retries: '+'; '.join(errors))


def review(case, frames):
    count=len(frames)
    initial=np.asarray(frames[0].convert('RGB')).astype(float)
    unchanged=all(not np.any(np.max(np.abs(np.asarray(frame.convert('RGB')).astype(float)-initial),axis=2)>24) for frame in frames[1:])
    prompt=('Review a short teaching video independently of its generator and all previous grades. '
        'A correct answer, sharp encoding, black background or stable diagram does not establish instructional excellence. '
        '1=unusable or absent, 2=weak, 3=adequate execution, 4=strong evidenced teaching, '
        '5=exceptionally effective and concretely justified. Do not give 5 merely for meeting a requirement. '
        'Inspect essential text overlap/occlusion and readable duration, not just whether words exist. '
        'For paths/flows, check visible connections and that arrow endpoints attach to the represented route; '
        'disconnected decorative curves plus arrows do not demonstrate a coherent mechanism. '
        'For sorting or transformations, track object identities and every intermediate state. '
        'List only actual changes visible between the supplied frames. If there are no changes, events must be []. '
        'Never put a static image or an inferred task step in events. Every event has before_frame strictly less than after_frame. '
        'Classify initial drawing, label/answer reveals, highlighting and fading as reveal; unrelated motion as decoration. '
        'For each substantive event cite its full start/end span, including at least one sampled intermediate frame. '
        'An operation requires actual entity manipulation or a demonstrated relation, comparison juxtaposes relevant states, '
        'and reasoning visibly links an intermediate justification to its consequence. Never relabel a reveal as reasoning. '
        'Only report severe layout defects persisting in at least two settled frames, excluding transient writing animation. '
        'Use regions in normalized image coordinates [left,top,right,bottom]. Explain observations before scoring. '
        'Do not invent extra task requirements, infer unobserved expertise, or reward animation quantity. '
        + ('Measured sampled-frame evidence: every sampled image is unchanged at a 24-level RGB tolerance. Events MUST be empty; no operation, reveal or transition is visible in these samples. '
         if unchanged else '')+
        'Task obligations: '+json.dumps(requirements(case),ensure_ascii=False)+'\nCriteria: '+json.dumps(CRITERIA))
    if case.get('segment_evidence'):
        prompt += ('\nEvery ten-second window was separately inspected. Use this timestamped ledger together '
                   'with the overview images; do not invent operations absent from the ledger. A window can '
                   'omit later steps without being defective. Reconcile object identities and values across windows. '
                   'These are fallible model observations, not external truth:\n'+json.dumps(case['segment_evidence'],ensure_ascii=False))
    if case.get('segment_context'):
        prompt += ('\nTHIS IS ONE WINDOW OF A LONGER LESSON. Judge layout, local state integrity and pacing here. '
                   'Do not require the entire lesson or final answer within this window; introductions, transitions '
                   'and recaps can be legitimate. Record actual visible intermediate states and explanations in summary. '
                   'For EVERY task requirement, record whether this window fully meets it, partially shows it, '
                   'contradicts it, does not show it, or leaves it uncertain. Cite only local frames. '
                   'A static caption claiming success is not process evidence.\nWindow: '+json.dumps(case['segment_context']))
    properties={
        'events':array(obj({'kind':{'type':'string','enum':sorted(SUBSTANTIVE|{'reveal','decoration'})},
            'before_frame':{'type':'integer','minimum':1,'maximum':count},
            'after_frame':{'type':'integer','minimum':1,'maximum':count},'region':BOX,
            'before':TEXT,'after':TEXT,'learning_value':TEXT}),maxItems=0 if unchanged else 12),
        'issues':array(obj({'kind':{'type':'string','enum':['overlap','occlusion','illegible','clipped','disconnected','wrong_state']},
            'severity':{'type':'string','enum':['minor','severe']},'essential':{'type':'boolean'},
            'frames':frame_indices(count),'region':BOX,'finding':TEXT}),maxItems=12),
        'criteria':array(obj({'id':{'type':'string','enum':list(CRITERIA)},'finding':TEXT,
            'evidence_frames':frame_indices(count),'score':{'type':'integer','minimum':1,'maximum':5}}),minItems=6,maxItems=6),
        'summary':TEXT}
    required=requirements(case)
    if case.get('segment_context'):
        properties['requirement_evidence']=array(obj({
            'id':{'type':'string','enum':[r['id'] for r in required]},
            'status':{'type':'string','enum':['met','partial','incorrect','not_shown','uncertain']},
            'evidence_frames':frame_indices(count),'finding':TEXT}),minItems=len(required),maxItems=len(required))
    schema=response_format('instructional_presentation',properties)
    def validator(raw):
        validate(raw,count)
        if case.get('segment_context'):
            rows=raw.get('requirement_evidence')
            if not isinstance(rows,list) or len(rows)!=len(required) or {r.get('id') for r in rows}!={r['id'] for r in required}:
                raise ValueError('segment must record every requirement exactly once')
            for row in rows:
                if row.get('status') not in ('met','partial','incorrect','not_shown','uncertain'):
                    raise ValueError('invalid segment requirement status')
                _indices(row.get('evidence_frames'),count)
                if row['status'] in ('met','partial','incorrect') and not row['evidence_frames']:
                    raise ValueError('segment observation needs visible evidence')
                if not isinstance(row.get('finding'),str) or not row['finding'].strip():
                    raise ValueError('segment finding missing')
        return raw
    return _ask([{'role':'user','content':frames_as_multimodal_content(frames,prompt)}],schema,validator,tokens=6000 if case.get('segment_context') else 4000)


def verify_events(events, frames):
    """Verify local pixel transitions, never interpret pixel motion as learning."""
    output=[]
    for event in events:
        a,b=event['before_frame']-1,event['after_frame']-1
        box=event['region'];width,height=frames[a].size
        crop=(int(box[0]*width),int(box[1]*height),max(int(box[2]*width),int(box[0]*width)+1),max(int(box[3]*height),int(box[1]*height)+1))
        first=np.asarray(frames[a].convert('RGB').crop(crop)).astype(float)
        last=np.asarray(frames[b].convert('RGB').crop(crop)).astype(float)
        difference=lambda x,y:float(np.mean(np.max(np.abs(x-y),axis=2)>24))
        changed=difference(first,last)
        intermediate=[]
        for index in range(a+1,b):
            middle=np.asarray(frames[index].convert('RGB').crop(crop)).astype(float)
            if difference(middle,first)>=.02 and difference(middle,last)>=.02:
                intermediate.append(index+1)
        verified=(event['kind'] in SUBSTANTIVE and first.shape[0]*first.shape[1]>=256
                  and bool(intermediate))
        output.append({**event,'transition_verified':verified,'changed_roi_fraction':round(changed,5),
                       'intermediate_frames':intermediate})
    return output


def validate_comparison(raw,count):
    if not isinstance(raw,dict) or raw.get('preferred') not in ('A','B','tie','uncertain'):
        raise ValueError('invalid comparison preference')
    if raw.get('advantage') not in ('none','cosmetic','substantive','uncertain'):
        raise ValueError('invalid temporal advantage')
    for field in ('finding','lost_information'):
        if not isinstance(raw.get(field),str) or not raw[field].strip():
            raise ValueError('comparison explanation missing')
    a,b=raw.get('before_frame'),raw.get('after_frame')
    if type(a) is not int or type(b) is not int or not 0<=a<=count or not 0<=b<=count:
        raise ValueError('invalid comparison frame pair')
    if raw['advantage']=='substantive' and not 1<=a<b<=count:
        raise ValueError('substantive advantage needs an ordered visible transition')
    return raw


def compare_still(case,frames,*,video_first):
    prompt=('Compare two presentations of the SAME current teaching task. Ignore previous scores. '
        'Choose which better exposes task-relevant operations, reasoning or comparisons at playback speed. '
        'One version has a chronological frame sequence; the other is the actual final frame held for the same duration. '
        'The question is what information time ADDS, not which has more pixels changing. '
        'A title, object drawing, answer/label reveal, fade, decorative movement, or sequential highlighting alone '
        'is at most cosmetic when the held final image conveys the same lesson. '
        'Substantive requires an inspectable manipulation, causal dependency or comparison lost in the held image. '
        'A final hold after such a process is legitimate. Relevant movement in a small region may be substantive. '
        'Do not require extra content absent from the task, but distinguish accurate task completion from video added value. '
        'Record exactly what useful information would be lost and cite its sequence-local before/after frame numbers. '
        'Use before_frame=after_frame=0 when no substantive transition can be established. '
        'Task: '+json.dumps(requirements(case),ensure_ascii=False))
    if case.get('segment_evidence'):
        prompt += ('\nTimestamped observations from every window of the chronological version follow. '
                   'Use them only as supporting observations; cite a visible ordered overview-frame pair '
                   'for substantive advantage, and mark uncertain when overview evidence cannot establish it.\n'
                   +json.dumps(case['segment_evidence'],ensure_ascii=False))
    content=[{'type':'text','text':prompt}]
    for label,is_video in [('A',video_first),('B',not video_first)]:
        content+=frames_as_multimodal_content(frames if is_video else [frames[-1]],
            f'Version {label}: '+('chronological frames 1..'+str(len(frames)) if is_video else 'single final frame, held'))
    schema=response_format('temporal_added_information',{'finding':TEXT,'lost_information':TEXT,
        'before_frame':{'type':'integer','minimum':0,'maximum':len(frames)},
        'after_frame':{'type':'integer','minimum':0,'maximum':len(frames)},
        'preferred':{'type':'string','enum':['A','B','tie','uncertain']},
        'advantage':{'type':'string','enum':['none','cosmetic','substantive','uncertain']}})
    result=_ask([{'role':'user','content':content}],schema,lambda raw:validate_comparison(raw,len(frames)),tokens=1300)
    result['video_label']='A' if video_first else 'B'
    result['video_preferred']=result['preferred']==result['video_label']
    return result


def assess(case,frames):
    if len(frames)<3:
        raise ValueError('presentation review needs at least three ordered frames')
    observed=review(case,frames)
    events=verify_events(observed['events'],frames)
    # Both orderings are required; a favorable position-biased answer cannot pass.
    comparisons=[compare_still(case,frames,video_first=first) for first in (True,False)]
    return score_review(observed,events,comparisons)


def assess_video(case, path, *, resize_max=854, previous=None):
    """Inspect every ten-second window, then judge the whole lesson and actual final still.

    Window observations remain VLM evidence, not independent factual ground truth.
    A failed window or unsupported global judgment cannot silently disappear.
    """
    from eval.frame_extractor import extract_frames, extract_window
    import cv2
    cap=cv2.VideoCapture(str(path))
    try:
        fps=cap.get(cv2.CAP_PROP_FPS);count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not cap.isOpened() or fps<=0 or count<=0:raise ValueError('unreadable video')
        duration=count/fps
    finally:cap.release()
    if duration<=10:
        return assess(case,extract_frames(path,n=18,resize_max=resize_max))
    windows=[]
    cached={w['id']:w for w in (previous or {}).get('segments',[]) if 'review' in w and not w.get('error')}
    for index in range(math.ceil(duration/10)):
        start=max(0,index*10-1);end=min(duration,(index+1)*10)
        if index in cached and cached[index].get('start_s')==start and cached[index].get('end_s')==end:
            windows.append(cached[index]);continue
        try:
            frames,timestamps=extract_window(path,start,end,resize_max=resize_max)
            local_case={**case,'segment_context':{'id':index,'start_s':start,'end_s':end,'timestamps_s':timestamps}}
            observed=review(local_case,frames)
            events=verify_events(observed['events'],frames)
            windows.append({'id':index,'start_s':start,'end_s':end,'timestamps_s':timestamps,
                            'review':observed,'events':events})
        except Exception as exc:
            windows.append({'id':index,'start_s':start,'end_s':end,'error':f'{type(exc).__name__}: {exc}'[:600]})
    if any(w.get('error') for w in windows):
        return {'version':VERSION,'valid':False,'passed':False,'score':None,'all_windows_reviewed':False,
                'duration_s':duration,'segments':windows,'failures':['segment_review_incomplete'],
                'error':'one or more windows could not be verified'}
    overview=extract_frames(path,n=18,resize_max=resize_max)
    ledger=[{'id':w['id'],'start_s':w['start_s'],'end_s':w['end_s'],'summary':w['review']['summary'],
             'issues':w['review']['issues'],'requirement_evidence':w['review']['requirement_evidence'],
             'timestamps_s':w['timestamps_s']} for w in windows]
    global_case={**case,'segment_evidence':ledger}
    try:
        observed=review(global_case,overview)
        comparisons=[compare_still(global_case,overview,video_first=first) for first in (True,False)]
    except Exception as exc:
        return {'version':VERSION,'valid':False,'passed':False,'score':None,'all_windows_reviewed':True,
                'duration_s':duration,'segments':windows,'segment_evidence':ledger,
                'failures':['global_review_incomplete'],'error':f'{type(exc).__name__}: {exc}'[:600]}
    # Layout cannot recover by averaging away an unreadable chapter.
    for row in observed['criteria']:
        if row['id'] in ('layout_readability','perceptual_pacing'):
            row['score']=min([row['score']]+[next(r['score'] for r in w['review']['criteria'] if r['id']==row['id']) for w in windows])
    events=[{**event,'segment_id':w['id'],'evidence_scope':'segment_local_frames',
             'before_s':w['timestamps_s'][event['before_frame']-1],
             'after_s':w['timestamps_s'][event['after_frame']-1]} for w in windows for event in w['events']]
    for window in windows:
        observed['issues'].extend({**issue,'segment_id':window['id'],'evidence_scope':'segment_local_frames'} for issue in window['review']['issues'])
    result=score_review(observed,events,comparisons)
    return {**result,'duration_s':duration,'segment_window_s':10,'segment_sample_fps':2,
            'segments':windows,'segment_evidence':ledger,'all_windows_reviewed':True,'segment_overlap_s':1,
            'overview_timestamps_s':[round(i*(count-1)/17)/fps for i in range(18)]}


def score_review(observed,events,comparisons):
    scores={row['id']:row['score'] for row in observed['criteria']}
    raw_score=round(sum((scores[key]-1)*25 for key in CRITERIA)/len(CRITERIA),4)
    reasons=[];caps=[]
    severe=[issue for issue in observed['issues'] if issue['severity']=='severe' and issue['essential']
            and len(set(issue['frames']))>=2]
    if severe or scores['layout_readability']<=2 or scores['representation_integrity']<=2:
        reasons.append('essential_layout_or_representation_failure');caps.append(39.0)
    verified=[event for event in events if event['transition_verified']]
    if not verified:
        reasons.append('no_verified_instructional_transition');caps.append(49.0)
    if min(scores['visual_explanation'],scores['temporal_contribution'])<=2:
        reasons.append('weak_explanation_or_temporal_value');caps.append(49.0)
    uncertain=(len(comparisons)!=2 or any(x['preferred']=='uncertain' or x['advantage']=='uncertain' for x in comparisons))
    substantive=[x['video_preferred'] and x['advantage']=='substantive' for x in comparisons]
    if len(substantive)==2 and substantive[0]!=substantive[1]:
        uncertain=True
    if not uncertain and not all(substantive):
        reasons.append('final_still_preserves_instructional_information');caps.append(49.0)
    if uncertain:
        reasons.append('temporal_comparison_unresolved')
    bottlenecks=[(scores[key]-1)*25 for key in ('layout_readability','representation_integrity','visual_explanation','temporal_contribution')]
    score=min([raw_score]+caps+bottlenecks)
    conclusive_failure = bool(severe or scores['layout_readability']<=2 or scores['representation_integrity']<=2
                              or min(scores['visual_explanation'],scores['temporal_contribution'])<=2)
    bounded_rejection = uncertain and conclusive_failure
    if min(scores.values())<4 or score<70:
        reasons.append('presentation_below_strong_evidence_threshold')
    passed=not reasons and min(scores.values())>=4 and score>=70
    return {'version':VERSION,'valid':not uncertain or bounded_rejection,'score':score if not uncertain or bounded_rejection else None,
            'comparison_valid':not uncertain,
            'decision_type':'bounded_rejection' if bounded_rejection else 'complete_review' if not uncertain else 'unverified',
            'raw_review_score':raw_score,'passed':passed,'caps':caps,'failures':reasons,
            'criteria':observed['criteria'],'issues':observed['issues'],'events':events,
            'still_comparisons':comparisons,'summary':observed['summary'],
            'interpretation':'observable_instructional_presentation_not_measured_learning'}


def apply(scoring,review):
    """Bottleneck presentation score; preserve all raw eight-axis diagnostics."""
    result={**scoring,'eight_axis_diagnostic_score':scoring.get('score'),
            'presentation_score':review.get('score')}
    value=review.get('score')
    if (review.get('valid') is not True or type(value) not in (int,float)
            or not math.isfinite(value) or not 0<=value<=100):
        return {**result,'valid':False,'strict_pass':False,'score':None,
                'errors':list(scoring.get('errors',[]))+['instructional_presentation_unverified']}
    if result.get('valid'):
        result['score']=min(result['score'],review['score'])
    result['strict_pass']=bool(result.get('strict_pass') and review.get('passed'))
    result['gates']=list(result.get('gates',[]))+review.get('failures',[])
    return result
