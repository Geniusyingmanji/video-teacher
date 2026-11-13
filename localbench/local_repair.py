"""Explicit text/speech patching of a bound existing declarative delivery."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .common import digest, public_case, write_json
from .provenance import file_hash


def apply_patch(plan, patch):
    from .content_review import apply_text_repairs
    from .pipeline import spoken_text
    for replacement in patch.get('replacements',[]):
        i=replacement.get('scene');field=replacement.get('field')
        if type(i) is not int or not 0<=i<len(plan['scenes']):raise ValueError('invalid target scene')
        scene=plan['scenes'][i]
        if field=='caption' and scene.get('teaching_cues'):
            raise ValueError('caption is computed by teaching cues; patch its state-aware producer')
        if field=='narration' and scene.get('spoken_units'):
            raise ValueError('spoken-unit narration needs its timed compiler, not a plain text patch')
    revised=apply_text_repairs(plan,patch)
    changed=[i for i,(a,b) in enumerate(zip(plan['scenes'],revised['scenes'])) if a!=b]
    speech=[i for i in changed if spoken_text(plan['scenes'][i])!=spoken_text(revised['scenes'][i])]
    if [s['duration_s'] for s in plan['scenes']] != [s['duration_s'] for s in revised['scenes']]:
        raise ValueError('local repair cannot move scene boundaries')
    return revised,changed,speech


def verify_untargeted(before, after, changed):
    from .scene import render_frame
    checks=[]
    for i,(a,b) in enumerate(zip(before['scenes'],after['scenes'])):
        if i in changed:continue
        if a!=b:raise ValueError('non-target scene changed')
        hashes=[]
        for progress in (0,.25,.5,.75,1):
            old,_=render_frame(a,progress,index=i,total=len(before['scenes']))
            new,_=render_frame(b,progress,index=i,total=len(after['scenes']))
            if old.tobytes()!=new.tobytes():raise ValueError('non-target rendered pixels changed')
            hashes.append(hashlib.sha256(old.tobytes()).hexdigest())
        checks.append({'scene':i,'input_pixel_hashes':hashes})
    return checks


def repair(case, source, patch, out, *, tts=None):
    """All source media/plans immutable; failed candidates retain original artifact."""
    from .pipeline import encode
    from .scene import validate_plan, inspect_layout, renderer_fingerprint, VERSION
    from .layout_geometry import blocking_issues
    from .rerender import decoded_audio_hash
    out=Path(out).resolve()
    if out.exists():raise ValueError('local repair requires a fresh output directory')
    if source.get('id')!=case['id'] or patch.get('case_id')!=case['id']:
        raise ValueError('repair task mismatch')
    if source.get('public_input_hash')!=digest(public_case(case)):
        raise ValueError('source public input mismatch or unavailable')
    artifacts=[a for a in source.get('artifacts',[]) if a.get('complete') and a.get('mode')=='code']
    if len(artifacts)!=1:raise ValueError('one declared code artifact required; upstream Manim/native media cannot use this patcher')
    artifact=copy.deepcopy(artifacts[0]);video=Path(artifact['video_path']).resolve()
    if file_hash(video)!=artifact['sha256'] or patch.get('video_sha256')!=artifact['sha256']:
        raise ValueError('repair media binding mismatch')
    plan_path=video.parent/'plan.json';plan=json.loads(plan_path.read_text())
    if patch.get('plan_sha256')!=digest(plan):raise ValueError('repair plan binding mismatch')
    if artifact.get('plan_sha256')!=digest(plan) or artifact.get('scene_version')!=VERSION or artifact.get('renderer_sha256')!=renderer_fingerprint():
        raise ValueError('source generation plan/renderer receipt missing or changed; do not infer provenance from mutable plan.json')
    out.mkdir(parents=True)
    write_json(out/'source_binding.json',{'video_sha256':artifact['sha256'],'plan_sha256':digest(plan),
                                        'case_hash':digest(case),'patch':patch})
    result={**copy.deepcopy(source),'original_artifacts':copy.deepcopy(source['artifacts'])}
    try:
        revised,changed,speech=apply_patch(plan,patch)
        validate_plan(copy.deepcopy(revised),case)
        issues=[x for x in inspect_layout(revised,include_warnings=True) if x.get('scene') in changed]
        if blocking_issues(issues):raise ValueError('target scene still has blocking layout defects')
        unchanged=verify_untargeted(plan,revised,changed)
        audio=video;audio_receipt=None
        if speech:
            from .fixed_scene_speech import synthesize
            audio,audio_receipt=synthesize(revised,plan,video,speech,out/'speech',tts=tts)
        write_json(out/'plan.json',revised)
        candidate=encode(revised,out,audio,mode='code',copy_audio=not speech)
        identical=decoded_audio_hash(video)==decoded_audio_hash(candidate['video_path']) if not speech else None
        if not speech and not identical:raise ValueError('caption-only patch changed original decoded audio')
        for key in ('scoring','dimensions','acceptance','quality_passed','evaluation','evaluation_status','scores_path'):
            result.pop(key,None)
        result.update(status='rendered',evaluation_status='not_evaluated_after_repair',
            generation_content_review='patched_requires_review',artifacts=[candidate],local_repair={
            'status':'rendered_requires_independent_evaluation','changed_scenes':changed,'speech_scenes':speech,
            'same_scene_boundaries':True,'untargeted_render_checks':unchanged,
            'decoded_audio_identical':identical,'speech_receipt':audio_receipt,
            'speech_preservation_scope':'Fixed-slot 24kHz PCM splice before final AAC encode; not a bit-exact final AAC guarantee.' if speech else 'Exact decoded audio copied.'})
    except Exception as exc:
        result.update(status='repair_failed_original_retained',artifacts=[artifact],
                      local_repair={'status':'failed_original_retained','error':str(exc)[:1400]})
    write_json(out/'delivery.json',result)
    write_json(out/'manifest.json',{'cases':[result],'planned_ids':[case['id']]})
    return result


def execute(args):
    if not args.manifest or not args.patch or not args.ids or len(args.ids)!=1:
        raise ValueError('repair requires --manifest, --patch and exactly one --ids')
    from .common import read_jsonl
    case=next((c for c in read_jsonl(args.data) if c['id']==args.ids[0]),None)
    if case is None:raise ValueError('unknown repair case')
    manifest=json.loads(args.manifest.read_text())
    rows=[r for r in manifest['cases'] if r['id']==case['id']]
    if len(rows)!=1:raise ValueError('repair source case missing or duplicated')
    source=copy.deepcopy(rows[0])
    for artifact in source.get('artifacts',[]):
        p=Path(artifact['video_path'])
        artifact['video_path']=str((args.manifest.parent/p).resolve()) if not p.is_absolute() else str(p)
    config=json.loads(args.config.read_text()) if args.config else {}
    result=repair(case,source,json.loads(args.patch.read_text()),args.out,tts=config.get('tts'))
    print(json.dumps({'status':result['status'],'out':str(args.out)},ensure_ascii=False))
    return 0 if result['status']=='rendered' else 2
