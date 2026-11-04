"""Recompute the frozen rubric after localized severe-defect verification.

Preserve the full base evaluation. A rejected allegation prompts a fresh rating
of the affected criterion without revealing its previous numeric score. An
unresolved allegation blocks the total; it never becomes an invented zero.
"""
import copy
import hashlib
import json
from eval.evidence_prompt import prompt_json
from pathlib import Path

from eval import benchmark_scoring as scoring, instructional_video as presentation, narration, task_completion, delivery_pacing
from eval.claim_grounding import verify_presentation, VERSION as GROUNDING_VERSION
from eval.evidence_audit import reconcile
from eval.frame_extractor import extract_frames, extract_window, frames_as_multimodal_content
from eval.judges.gpt55 import judge_config
from eval.judges.structured_json import response_format, array, obj, frame_indices

VERSION = scoring.VERSION + '+grounded-v2'


def code_hash():
    return hashlib.sha256(b''.join(Path(__file__).with_name(name).read_bytes() for name in
        ('verified_scoring.py','claim_grounding.py','verified_completion.py','evidence_prompt.py'))).hexdigest()


def rerate(case, frames, ids, corrections):
    prompt = ('Independently rate ONLY the specified presentation criteria against the actual images. '
        'Use the same anchors: 1 unusable/absent, 2 weak, 3 adequate, 4 strong, 5 exceptional; half points allowed. '
        'Do not target an increase, decrease, pass or desired total. Prior numerical ratings are withheld. '
        'A localized verification contradicted factual allegations. Do not repeat rejected claims. '
        'Inspect the images as authority and describe actual conditions before assigning a rating. '
        'For a local window do not require the entire lesson there. For the whole lesson inspect its overview. '
        'Every rating needs literal observations and actual in-range image citations.\n' + prompt_json({
        'task':case.get('prompt_text'), 'criteria':{k:presentation.CRITERIA[k] for k in ids},
        'verified_corrections':corrections}))
    schema = response_format('correct_factual_presentation_rating', {'criteria':array(obj({
        'id':{'type':'string','enum':sorted(ids)}, 'finding':{'type':'string','minLength':1,'maxLength':240},
        'evidence_frames':frame_indices(len(frames)),
        'score':{'type':'number','enum':[1,1.5,2,2.5,3,3.5,4,4.5,5]}}), minItems=len(ids), maxItems=len(ids))})
    def validate(raw):
        rows = raw.get('criteria', [])
        if len(rows) != len(ids) or {r.get('id') for r in rows} != set(ids):
            raise ValueError('all affected criteria required exactly once')
        for row in rows:
            if type(row.get('score')) not in (int,float) or not 1 <= row['score'] <= 5 or row['score']*2 != round(row['score']*2):
                raise ValueError('invalid corrected criterion score')
            presentation._indices(row.get('evidence_frames'), len(frames))
            if not row['evidence_frames'] or not isinstance(row.get('finding'),str) or not row['finding'].strip():
                raise ValueError('corrected rating requires visible evidence')
        return raw
    return presentation._ask([{'role':'user','content':frames_as_multimodal_content(frames,prompt)}],
                              schema, validate, tokens=1800)


def apply_grounding(base, case, *, previous_claims=None, checkpoint=None):
    row = copy.deepcopy(base)
    row['base_evaluation'] = copy.deepcopy(base)
    row['version'] = VERSION
    row['verification_config'] = {'version':GROUNDING_VERSION, 'judge':judge_config(),
                                'code_sha256':code_hash(), 'base_code_sha256':base.get('evaluation_config',{}).get('scoring_code_sha256')}
    if 'generation_missing_or_failed' in base.get('errors', []):
        row['claim_grounding'] = {'status':'unavailable_video', 'claims':[]}
        return row
    if hashlib.sha256(Path(row['video_path']).read_bytes()).hexdigest() != row['video_sha256']:
        raise ValueError('video source changed after base evaluation')
    grounding = verify_presentation(base, previous=previous_claims, checkpoint=checkpoint)
    row['claim_grounding'] = grounding
    rejected = grounding['rejected_claims']
    if grounding['uncertain_claims']:
        row['scoring'].update(valid=False, score=None, groups=None, strict_pass=False)
        row['scoring'].setdefault('errors',[]).append('severe_defect_claim_unverified')
        return row
    completion_repaired = False
    if row.get('task_completion',{}).get('valid') is not True:
        from eval.verified_completion import review
        samples = extract_frames(row['video_path'],sample_fps=row['evaluation_config']['sample_fps'],resize_max=832)
        frames = [samples[i] for i in row['judge_frame_indices_in_sample']]
        judged_case = {**case,'segment_evidence':row['instructional_presentation'].get('segment_evidence'),
                      'actual_spoken_segments':[{k:s[k] for k in ('id','start_s','end_s','text')}
                                                for s in row.get('speech_transcript',{}).get('segments',[])]}
        row['task_completion'] = review(judged_case,frames)
        row['resolved_errors'] = [e for e in row.get('errors',[]) if e in ('task_completion_failed','task_completion_missing_or_invalid')]
        row['errors'] = [e for e in row.get('errors',[]) if e not in row['resolved_errors']]
        completion_repaired = True
    if not rejected and not completion_repaired:
        return row
    pr = row['instructional_presentation']
    rejected_keys = {json.dumps(r['claim'], sort_keys=True) for r in rejected}
    affected = {}
    changes = []
    for result in rejected:
        claim = result['claim']
        scope = claim.get('segment_id') if claim.get('evidence_scope') == 'segment_local_frames' else 'overview'
        target = 'representation_integrity' if claim.get('kind') in ('disconnected','wrong_state') else 'layout_readability'
        affected.setdefault(scope,set()).add(target)
    pr['issues'] = [issue for issue in pr['issues'] if json.dumps(issue,sort_keys=True) not in rejected_keys]
    windows = {w['id']:w for w in pr.get('segments',[])}
    for scope, ids in list(affected.items()):
        if scope == 'overview':
            continue
        window = windows[scope]
        local_corrections = [r for r in rejected if r['claim'].get('segment_id') == scope]
        frames, _ = extract_window(row['video_path'], window['start_s'], window['end_s'], resize_max=832)
        revised = rerate(case, frames, ids, local_corrections)
        for rating in revised['criteria']:
            old = next(c for c in window['review']['criteria'] if c['id']==rating['id'])
            changes.append({'scope':scope,'before':copy.deepcopy(old),'after':copy.deepcopy(rating)})
            old.clear(); old.update(rating)
        # Match local issue copies to their augmented ledger claims.
        window['review']['issues'] = [issue for issue in window['review']['issues'] if not any(
            r['claim'].get('segment_id') == scope and all(issue.get(k)==r['claim'].get(k) for k in issue)
            for r in local_corrections)]
    if affected:
        ids = set().union(*affected.values())
        overview = extract_frames(row['video_path'], n=18, resize_max=832)
        revised = rerate(case, overview, ids, rejected)
        for rating in revised['criteria']:
            old = next(c for c in pr['criteria'] if c['id']==rating['id'])
            changes.append({'scope':'overview','before':copy.deepcopy(old),'after':copy.deepcopy(rating)})
            old.clear(); old.update(rating)
    # Reapply the unchanged weakest-local-layout and pacing policy.
    for rating in pr['criteria']:
        if rating['id'] not in ('layout_readability','perceptual_pacing'):
            continue
        for window in windows.values():
            candidate = next(c for c in window['review']['criteria'] if c['id']==rating['id'])
            if candidate['score'] < rating['score']:
                rating.update(candidate)
                rating.update(evidence_scope='segment_local_frames',segment_id=window['id'],
                              evidence_timestamps_s=[window['timestamps_s'][i-1] for i in candidate['evidence_frames']])
    pr.update(presentation.score_review(pr, pr['events'], pr['still_comparisons']))
    row['claim_grounding']['criterion_corrections'] = changes
    # Undo only the prior derived constraints, then apply the same policy again.
    for axis in row['axes'].values():
        if 'overview_score_before_evidence_audit' in axis:
            axis['score'] = axis.pop('overview_score_before_evidence_audit')
        axis.pop('evidence_constraints',None)
    engagement = row.get('supplementary',{}).get('teaching_engagement',{})
    for criterion in engagement.get('criteria',[]):
        if 'overview_rating' in criterion:
            criterion['score'] = criterion.pop('overview_rating')
        criterion.pop('binding_segment_evidence',None)
    reconcile(row)
    row['defects'] = [d for d in row.get('defects',[]) if not d.get('reason','').startswith('task_requirement_')]
    row['defects'].extend(task_completion.defects(row.get('task_completion',{})))
    result = scoring.score_case({k:v.get('score') for k,v in row['axes'].items()},
        narration_required=row.get('narration_required',False), narration_detected=row.get('narration',{}).get('detected'),
        defects=row.get('defects',[]))
    if row.get('consistency_review',{}).get('valid') is not True or row.get('task_completion',{}).get('valid') is not True:
        result.update(valid=False,score=None,groups=None,strict_pass=False)
        result.setdefault('errors',[]).append('required_review_unverified')
    if row.get('task_completion',{}).get('passed') is not True:
        result['strict_pass'] = False
        result.setdefault('gates',[]).append('task_completion_not_verified')
    result = presentation.apply(result,pr)
    if row.get('narration_required'):
        result = narration.apply(result,row.get('narration_review',{}))
        result = delivery_pacing.apply(result,row.get('delivery_pacing',{}))
    if pr.get('all_windows_reviewed') is not True:
        result.update(valid=False,score=None,groups=None,strict_pass=False)
    row['scoring'] = result
    return row
