"""Diagram-only comparison: preserve exact scene boundaries and encoded audio."""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

import imageio_ffmpeg

from .common import ROOT, public_case, digest, read_jsonl, write_json
from .pipeline import encode, resolve_source_plan, run_command
from .provenance import file_hash, freeze_run
from .scene import FPS, inspect_layout, validate_plan
from .chart import plan_chart_receipts


def diagram_only_plan(original, proposed):
    if original['case_id']!=proposed['case_id'] or len(original['scenes'])!=len(proposed['scenes']):
        raise ValueError('diagram comparison requires the same case and scenes')
    out=copy.deepcopy(original)
    changes=[]
    for i,(a,b) in enumerate(zip(original['scenes'],proposed['scenes'])):
        if {k:v for k,v in a.items() if k!='primitives'}!={k:v for k,v in b.items() if k!='primitives'}:
            raise ValueError('diagram comparison cannot change narration, timing, captions or other scene fields')
        if a.get('primitives')!=b.get('primitives'):
            out['scenes'][i]['primitives']=copy.deepcopy(b['primitives'])
            changes.append(i)
    if not changes:raise ValueError('no diagram changes to compare')
    return out,changes


def decoded_audio_hash(video):
    result=run_command([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(video),
        '-map','0:a:0','-c:a','pcm_s16le','-f','hash','-hash','sha256','-'])
    return result.stdout.strip()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-run',type=Path,required=True)
    p.add_argument('--plans-from',type=Path,required=True)
    p.add_argument('--id',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--variant-label',default='chart_code',help='Name of the refined visual variant in the manifest')
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    args=p.parse_args()
    if not re.fullmatch('[a-z][a-z0-9_]{0,47}',args.variant_label) or args.variant_label=='general_code':
        p.error('variant label must be a distinct safe lowercase name')
    if args.out.exists():p.error('use a new output directory')
    case=next(r for r in read_jsonl(args.data) if r['id']==args.id)
    records=json.loads((args.source_run/'manifest.json').read_text())['cases']
    source=next(r for r in records if r['id']==args.id)
    artifact=next(a for a in source['artifacts'] if a['mode']=='code' and a['complete'])
    if artifact['fps']!=FPS or file_hash(artifact['video_path'])!=artifact['sha256']:
        raise ValueError('source fps or hash mismatch')
    if source['public_input_hash']!=digest(public_case(case)):
        raise ValueError('source public task mismatch')
    old_path=resolve_source_plan(args.source_run,args.id)
    new_path=resolve_source_plan(args.plans_from,args.id)
    old=json.loads(old_path.read_text());proposed=json.loads(new_path.read_text())
    plan,changed=diagram_only_plan(old,proposed)
    validate_plan(plan,case)
    issues=inspect_layout(plan)
    if issues:raise ValueError('new diagram layout invalid: '+json.dumps(issues[:6]))
    freeze_run(args.out,{'entrypoint':'rerender','id':args.id,'source_video':artifact['sha256'],
        'original_plan_sha256':file_hash(old_path),'proposed_plan_sha256':file_hash(new_path),
        'public_input_hash':digest(public_case(case)),'changed_scenes':changed,'variant_label':args.variant_label,
        'invariants':['exact original scene durations','unchanged narration and captions','copied original audio stream']})
    directory=args.out/args.id;directory.mkdir()
    write_json(directory/'plan.json',plan)
    write_json(directory/'original_plan.json',old)
    write_json(directory/'public_input.json',public_case(case))
    write_json(directory/'chart_computation.json',plan_chart_receipts(plan))
    from .flow import plan_flow_receipts
    write_json(directory/'flow_computation.json',plan_flow_receipts(plan))
    new_artifact=encode(plan,directory,artifact['video_path'],mode='code',copy_audio=True)
    before=decoded_audio_hash(artifact['video_path']);after=decoded_audio_hash(new_artifact['video_path'])
    receipt={'changed_scenes':changed,'same_narration':True,'same_scene_durations':True,
             'source_decoded_audio_hash':before,'output_decoded_audio_hash':after,
             'decoded_audio_identical':before==after,'source_video_sha256':artifact['sha256'],
             'output_video_sha256':new_artifact['sha256']}
    write_json(directory/'comparison_receipt.json',receipt)
    if before!=after:raise ValueError('copied audio failed exact decoded-sample comparison')
    write_json(args.out/'manifest.json',{'model':'qwen3.8-flash_plan_upgrade',
       'cases':[{'id':args.id,'public_input_hash':digest(public_case(case)),
         'status':'rendered','artifacts':[{**artifact,'mode':'general_code'},
                                         {**new_artifact,'mode':args.variant_label}]}]})
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
