"""Localize changed source regions from final-video pixels, without generator data."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image


def change_boxes(before, after, max_regions=4):
    if before.size!=after.size:raise ValueError('frame sizes differ')
    w,h=before.size
    difference=np.max(np.abs(np.asarray(before,dtype=np.int16)-np.asarray(after,dtype=np.int16)),axis=2)>45
    # This profile requires a fixed upper reference viewport. Lower teaching
    # panels and the top title are excluded from this auxiliary diagnostic.
    difference[:round(h*.10)]=False;difference[round(h*.73):]=False
    block=16
    active={}
    for y in range(0,h,block):
        for x in range(0,w,block):
            count=int(difference[y:y+block,x:x+block].sum())
            if count>=8:active[(x//block,y//block)]=count
    components=[]
    while active:
        start=next(iter(active));stack=[start];points=[];mass=0
        while stack:
            point=stack.pop()
            if point not in active:continue
            mass+=active.pop(point);points.append(point)
            x,y=point
            stack.extend((x+dx,y+dy) for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
        xs,ys=zip(*points);pad=max(32,round(min(w,h)*.075))
        bbox=[max(0,min(xs)*block-pad),max(0,min(ys)*block-pad),
              min(w,(max(xs)+1)*block+pad),min(h,(max(ys)+1)*block+pad)]
        components.append({'bbox':bbox,'changed_pixel_count':mass})
    return sorted(components,key=lambda x:-x['changed_pixel_count'])[:max_regions]


def verify_changed_regions(client, case, packet):
    first,last=packet['frames'][0],packet['frames'][-1]
    before=Image.open(first['path']).convert('RGB');after=Image.open(last['path']).convert('RGB')
    boxes=change_boxes(before,after)
    if not boxes:return {'status':'no_detected_changes_in_upper_viewport','checks':[],'regions':[]}
    content=[{'type':'text','text':'''Compare these SAME-COORDINATE before/after crops from a teaching video.
The public task requires preserving the source diagram except authorized label/mark changes.
Inspect actual strokes: does an originally continuous line acquire a white erasure gap, break,
overlap, or other unauthorized geometry change? Labels themselves may change as requested.
Return JSON {verdict:"pass"|"fail"|"unverified",evidence_ids:[...],reason,
observed_positions_or_counts}. Report exact visible continuity/line endpoints near the edited
text. Do not assume geometry is preserved because the numerical answer is correct.
Public task: '''+case['prompt_text'].split('\n')[0]}]
    for i,region in enumerate(boxes):
        for frame,im,label in [(first,before,'BEFORE'),(last,after,'AFTER')]:
            crop=im.crop(region['bbox'])
            crop=crop.resize((840,round(crop.height*840/crop.width)))
            buffer=io.BytesIO();crop.save(buffer,format='PNG')
            content.extend([{'type':'text','text':f"Region {i}, bbox {region['bbox']}, {label} {frame['id']} at {frame['time_s']} seconds."},
                            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()}}])
    messages=[{'role':'user','content':content}]
    allowed={first['id'],last['id']}
    for attempt in range(2):
        raw=client.chat(messages,purpose='source_changed_pixels:'+case['id'],max_tokens=1400)
        if (isinstance(raw,dict) and raw.get('verdict') in {'pass','fail','unverified'}
                and isinstance(raw.get('evidence_ids'),list) and raw['evidence_ids']
                and all(x in allowed for x in raw['evidence_ids']) and raw.get('reason')
                and raw.get('observed_positions_or_counts')):
            break
        if attempt:raise ValueError('invalid changed-region verification response')
        messages.extend([{'role':'assistant','content':json.dumps(raw,ensure_ascii=False)},
                         {'role':'user','content':'Return the requested JSON object, citing '+', '.join(sorted(allowed))+', with nonempty concrete visual observations.'}])
    check={**raw,'id':'source_changed_region_geometry',
           'failure_type':'incorrect_relation' if raw['verdict']=='fail' else None,
           'affected':['task_completeness.givens','visual_quality.artifact_control','visual_teaching.representation']}
    return {'status':'reviewed','checks':[check],'regions':boxes,
            'scope':'first/last video-frame changes in upper viewport; no guarantee about intermediate or excluded regions'}
