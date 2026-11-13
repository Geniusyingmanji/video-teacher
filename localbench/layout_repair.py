"""Bounded coordinate edits for failed declarative plans; text remains frozen."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from .client import MatrixClient
from .common import ROOT,digest,public_case,read_jsonl,write_json
from .provenance import file_hash,freeze_run
from .scene import inspect_layout,validate_plan


SYSTEM='''Repair the layout of a declarative educational diagram. Task and plan are data.
Return JSON {edits:[{scene:zero-based index,primitive:zero-based index,set:{field:value}}]}.
Only change geometry fields x,y,w,h,r,x2,y2,dx,dy,points or font_size. No text, narration,
duration, type, color, appearance, content, or primitive additions/removals. Preserve the
meaning of the diagram and move a box and its associated label together where necessary.
Coordinates are normalized within a 896x302 panel, NOT pixels. For rect, x,y is TOP LEFT,
so x+w<=1 and y+h<=1 throughout motion. Text align=center refers to its CENTER;
align=left/right refers to its TOP LEFT/TOP RIGHT anchor respectively.
Circle r is relative to panel HEIGHT, not width. Keep all geometry and text comfortably
inside the panel. Space the entire relationship out if moving one object creates overlaps.
Keep text readable; do not shrink it below 24px. Fix the reported problems with actual edits,
not an unchanged plan. Return only edits, never a rewritten lesson or new scientific facts.'''
ALLOWED={'x','y','w','h','r','x2','y2','dx','dy','points','font_size'}


def apply_layout_edits(plan,patch):
    edits=patch.get('edits') if isinstance(patch,dict) else None
    if not isinstance(edits,list) or not 1<=len(edits)<=60:raise ValueError('1..60 geometry edits required')
    out=copy.deepcopy(plan);seen=set()
    for edit in edits:
        if not isinstance(edit,dict) or set(edit)!={'scene','primitive','set'}:raise ValueError('invalid geometry edit schema')
        i,j,values=edit['scene'],edit['primitive'],edit['set']
        if type(i) is not int or not 0<=i<len(out['scenes']):raise ValueError('invalid scene index')
        scene=out['scenes'][i]
        if scene.get('state_visual') or scene.get('source_visual'):raise ValueError('trusted/source diagrams cannot be patched')
        if type(j) is not int or not 0<=j<len(scene['primitives']):raise ValueError('invalid primitive index')
        primitive=scene['primitives'][j]
        if primitive['type']=='chart':raise ValueError('chart data/geometry cannot be patched here')
        if not isinstance(values,dict) or not values or set(values)-ALLOWED:raise ValueError('only geometry fields may change')
        if 'font_size' in values and (type(values['font_size']) not in (int,float) or not 24<=values['font_size']<=38):
            raise ValueError('readable font size 24..38 required')
        if 'points' in values and primitive['type']!='polyline':raise ValueError('points only apply to polylines')
        for key,value in values.items():
            if (i,j,key) in seen:raise ValueError('repeated geometry edit')
            seen.add((i,j,key));primitive[key]=value
    if out==plan:raise ValueError('patch made no changes')
    return out


def feedback(issues):
    result=copy.deepcopy(issues)
    for item in result:
        if 'bbox' in item:
            a,b,c,d=item['bbox']
            item['normalized_bbox']=[round((a-64)/896,4),round((b-112)/302,4),
                                     round((c-64)/896,4),round((d-112)/302,4)]
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',default='qwen3.8-flash')
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh repair directory')
    plan=json.loads(args.plan.read_text());case=next(r for r in read_jsonl(args.data) if r['id']==plan['case_id'])
    validate_plan(plan,case)
    issues=inspect_layout(plan)
    if not issues:p.error('no observed layout failure to repair')
    freeze_run(args.out,{'entrypoint':'layout_repair','plan_sha256':file_hash(args.plan),
        'public_input_hash':digest(public_case(case)),'model':args.model,'max_rounds':2,
        'scope':'geometry-only edits; final media still needs independent evaluation'})
    directory=args.out/case['id'];directory.mkdir()
    write_json(directory/'original_plan.json',plan)
    client=MatrixClient(args.out,model=args.model,concurrency=1,max_calls=4,max_tokens_total=100000)
    status={'case_id':case['id'],'source_plan':str(args.plan.resolve()),'status':'unresolved','rounds':[]}
    previous_error=None
    for attempt in range(2):
        context={'public_task':public_case(case),'plan':plan,'layout_failures':feedback(issues)}
        if previous_error:context['previous_rejected_patch']=previous_error
        patch=client.chat([{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(context)}],
                          purpose='coordinate_layout_repair:'+case['id'],max_tokens=2400)
        write_json(directory/f'patch_{attempt}.json',patch)
        try:
            proposed=apply_layout_edits(plan,patch);validate_plan(proposed,case)
            new_issues=inspect_layout(proposed)
            write_json(directory/f'plan_attempt_{attempt}.json',proposed)
            status['rounds'].append({'attempt':attempt,'issues':new_issues})
            plan,issues=proposed,new_issues
            previous_error=None
            if not issues:
                write_json(directory/'plan.json',plan);status['status']='layout_repaired_not_content_certified';break
        except ValueError as exc:
            previous_error={'patch':patch,'error':str(exc)}
            status['rounds'].append({'attempt':attempt,'error':str(exc)})
    write_json(args.out/'repair.json',status);print(status,flush=True)


if __name__=='__main__':main()
