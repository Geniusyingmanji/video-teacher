"""Synthetic omission control: same completed lesson/audio, omit negative-x shading."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np

from .common import ROOT,digest,public_case,read_jsonl,write_json
from .pipeline import encode,resolve_source_plan
from .provenance import file_hash,freeze_run
from .rerender import decoded_audio_hash
from .scene import inspect_layout,render_frame,validate_plan


def omit_negative(plan):
    out=copy.deepcopy(plan);changed=[]
    for i,scene in enumerate(out['scenes']):
        for edit in scene.get('source_visual',{}).get('edits',[]):
            if edit.get('kind')=='fill_between':edit['restriction']='positive_only';changed.append(i)
    if not changed:raise ValueError('control needs an existing region lesson')
    # Top-level source_edits is provenance, not the actual per-scene renderer input.
    for edit in out.get('source_edits',[]):
        if edit.get('kind')=='fill_between':edit['restriction']='positive_only'
    return out,sorted(set(changed))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-run',type=Path,required=True);p.add_argument('--id',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    args=p.parse_args()
    if args.out.exists():p.error('use a fresh control directory')
    case=next(r for r in read_jsonl(args.data) if r['id']==args.id)
    run=json.loads((args.source_run/'manifest.json').read_text())
    source=next(c for c in run['cases'] if c['id']==args.id)
    media=next(a for a in source['artifacts'] if a['mode']=='code' and a['complete'])
    if any(a.get('complete') and file_hash(a['video_path'])!=a['sha256'] for a in source['artifacts']):
        raise ValueError('source artifact changed')
    if media['sha256']!=file_hash(media['video_path']) or source['public_input_hash']!=digest(public_case(case)):
        raise ValueError('source media or public task changed')
    plan_path=resolve_source_plan(args.source_run,args.id);plan=json.loads(plan_path.read_text())
    control,changed=omit_negative(plan);validate_plan(control,case)
    issues=inspect_layout(control)
    if issues:raise ValueError('control layout invalid: '+str(issues[:5]))
    freeze_run(args.out,{'entrypoint':'region_omission_control','id':args.id,'source_media_sha256':media['sha256'],
        'source_plan_sha256':file_hash(plan_path),'changed_scenes':changed,'new_model_calls':0,
        'scope':'Synthetic visual omission; same authored speech, timing and captions. Not a generated-method baseline.'})
    directory=args.out/args.id;directory.mkdir(exist_ok=True)
    write_json(directory/'plan.json',control);write_json(directory/'original_plan.json',plan)
    # Check pre-encoding frames; codec differences are not asserted pixel-identical.
    proof=[]
    for i,(a,b) in enumerate(zip(plan['scenes'],control['scenes'])):
        for progress in (0.,.5,1.):
            before,_=render_frame(a,progress,index=i,total=len(plan['scenes']),mode='code')
            after,_=render_frame(b,progress,index=i,total=len(plan['scenes']),mode='code')
            ba,aa=np.array(before),np.array(after)
            if not np.array_equal(ba[650:],aa[650:]):raise ValueError('control changed the lower teaching panel')
            proof.append({'scene':i,'progress':progress,'changed_pixels':int(np.any(ba!=aa,axis=2).sum()),'lower_panel_identical':True})
    artifact=encode(control,directory,media['video_path'],mode='code',copy_audio=True)
    before_hash=decoded_audio_hash(media['video_path']);after_hash=decoded_audio_hash(artifact['video_path'])
    slide_hashes={a['mode']:decoded_audio_hash(a['video_path']) for a in source['artifacts'] if a['mode']=='slides' and a['complete']}
    receipt={'source_video_sha256':media['sha256'],'control_video_sha256':artifact['sha256'],
             'source_audio_hash':before_hash,'control_audio_hash':after_hash,'decoded_audio_identical':before_hash==after_hash,
             'same_scene_durations':True,'same_narration_and_captions':True,'pre_encoding_frame_checks':proof,
             'slide_decoded_audio_hashes':slide_hashes,
             'scope':'Frame checks sample three progress points per scene; audio hash covers the whole decoded stream.'}
    write_json(directory/'control_receipt.json',receipt)
    if before_hash!=after_hash:raise ValueError('control audio changed')
    if any(h!=before_hash for h in slide_hashes.values()):raise ValueError('paired slide audio differs')
    artifacts=[{**media,'mode':'complete_region'},{**artifact,'mode':'negative_region_omitted'}]
    artifacts.extend({**a,'mode':'unshaded_slides'} for a in source['artifacts'] if a['mode']=='slides' and a['complete'])
    write_json(args.out/'manifest.json',{'cases':[{'id':args.id,'status':'synthetic_control_created',
        'public_input_hash':source['public_input_hash'],'artifacts':artifacts}]})
    print(json.dumps({'decoded_audio_identical':before_hash==after_hash,'changed_scenes':changed}),flush=True)


if __name__=='__main__':main()
