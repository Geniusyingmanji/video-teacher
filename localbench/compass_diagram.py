"""Compile declared compass flows into an explicitly oriented schematic.

The compiler verifies geometry against model declarations, not domain truth.
Public-reference binding must be checked separately. No arbitrary code executes.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from PIL import ImageColor

from .common import digest, public_case, write_json
from .evidence import image_content
from .scene import inspect_layout, validate_plan

VERSION = 'declared-compass-flow-dev2-explicit-indices'
# Screen coordinates: x increases rightward, y downward.
DIRECTIONS = {'N': (0,-1), 'NE': (1,-1), 'E': (1,0), 'SE': (1,1),
              'S': (0,1), 'SW': (-1,1), 'W': (-1,0), 'NW': (-1,-1)}


def compile_diagram(spec, references):
    if not isinstance(spec, dict) or set(spec) != {'boundary_label', 'flows'}:
        raise ValueError('diagram requires boundary_label and flows')
    label, flows = spec['boundary_label'], spec['flows']
    if not isinstance(label, str) or not 1 <= len(label) <= 24:
        raise ValueError('boundary_label must contain1..24characters')
    if not isinstance(flows, list) or not 1 <= len(flows) <= 2:
        raise ValueError('diagram.flows must contain1or2flow objects; an empty array is invalid')
    ink = '#18334b'
    def text(x,y,value,color=ink,size=24):
        return {'type':'text','x':x,'y':y,'text':value,'color':color,'font_size':size,'align':'center'}
    primitives = [
        {'type':'arrow','x':.15,'y':.30,'x2':.15,'y2':.13,'color':ink},
        {'type':'arrow','x':.09,'y':.24,'x2':.21,'y2':.24,'color':ink},
        text(.15,.055,'N'), text(.15,.38,'S'), text(.045,.24,'W'), text(.27,.24,'E'),
        {'type':'line','x':.32,'y':.52,'x2':.92,'y2':.52,'color':'#1868ae','dash':True},
        text(.80,.60,label,'#1868ae'), text(.16,.72,'Map view',size=24),
    ]
    records = []
    for index, flow in enumerate(flows):
        if not isinstance(flow,dict) or set(flow) != {'name','from','to','color','reference_id','reference_quote'}:
            raise ValueError('flow needs name/from/to/color/reference_id/reference_quote')
        if flow['from'] not in DIRECTIONS or flow['to'] not in DIRECTIONS:
            raise ValueError('use N/NE/E/SE/S/SW/W/NW directions')
        origin, movement = DIRECTIONS[flow['from']], DIRECTIONS[flow['to']]
        if origin != tuple(-v for v in movement):
            raise ValueError('from is the source bearing, to is the opposite travel bearing')
        if not isinstance(flow['name'], str) or not 1 <= len(flow['name']) <= 18:
            raise ValueError('short readable flow name required')
        ImageColor.getrgb(flow['color'])
        rid, quote = flow['reference_id'], flow['reference_quote']
        if rid not in references or not isinstance(quote,str) or not quote.strip() or quote not in references[rid]['statement']:
            raise ValueError('exact public-reference quote required')
        end = (.56,.52)
        start = (end[0]+.20*origin[0], end[1]+.27*origin[1])
        primitive_index = len(primitives)
        primitives.append({'type':'arrow','x':start[0],'y':start[1],'x2':end[0],'y2':end[1],
                           'color':flow['color'],'stroke':4})
        row_y = .095 if origin[1] < 0 else .89
        if origin[1] == 0:
            row_y = .095 + index*.79
        primitives.append(text(.61,row_y,f"{flow['name']}: {flow['from']} to {flow['to']}",flow['color']))
        dx, dy = end[0]-start[0], end[1]-start[1]
        sign = lambda x: 0 if abs(x)<1e-9 else (1 if x>0 else -1)
        if (sign(dx),sign(dy)) != movement:
            raise ValueError('compiled arrow contradicts declared travel direction')
        records.append({'primitive_index':primitive_index,'from':flow['from'],'to':flow['to'],
            'start':start,'end':end,'screen_delta':[dx,dy],'reference_id':rid,'reference_quote':quote})
    return primitives, {'version':VERSION,'spec_hash':digest(spec),'flows':records,
        'orientation':'north_up_east_right','semantic_binding_status':'model_declared_not_certified'}


def apply_revision(plan, raw, case, references, allowed_scenes):
    if not isinstance(raw,dict) or set(raw) != {'replacements'} or not isinstance(raw['replacements'],list):
        raise ValueError('replacements list required')
    candidate = copy.deepcopy(plan)
    seen, receipts = set(), []
    for row in raw['replacements']:
        if not isinstance(row,dict) or set(row) != {'scene','title','narration','caption','diagram','reason'}:
            raise ValueError('replacement requires scene/title/narration/caption/diagram/reason')
        i = row['scene']
        if type(i) is not int or i not in allowed_scenes or i in seen:
            raise ValueError('unique allowed scene index required')
        seen.add(i)
        if any(not isinstance(row[k],str) or not row[k].strip() for k in ('title','narration','caption','reason')):
            raise ValueError('text fields required')
        primitives, receipt = compile_diagram(row['diagram'],references)
        candidate['scenes'][i].update({k:row[k] for k in ('title','narration','caption')})
        candidate['scenes'][i].update(primitives=primitives,slide_text=row['caption'])
        receipts.append({'scene':i,**receipt,'reason':row['reason']})
    if seen != set(allowed_scenes):
        raise ValueError('cover all frozen requested scenes, without silent omission')
    if sum(len(s['narration'].split()) for s in candidate['scenes']) > 155:
        raise ValueError('bounded pilot narration exceeds155words')
    candidate.pop('timing_compilation',None)
    validate_plan(copy.deepcopy(candidate),case)
    issues=inspect_layout(candidate)
    if issues:
        raise ValueError('blocking layout findings: '+json.dumps(issues[:8]))
    return candidate, {'version':VERSION,'source_hash':digest(plan),'candidate_hash':digest(candidate),
        'changed_scenes':sorted(seen),'diagrams':receipts,'semantic_acceptance':'unverified'}


def propose(client, plan, case, references, questions, frames, out, *, allowed_scenes):
    out=Path(out)
    data={'public_task':public_case(case),'original_plan':plan,'references':references,
          'development_questions':questions,'allowed_scene_indices':allowed_scenes,
          'editable_scenes':[{'zero_based_index':i,'original_scene':plan['scenes'][i]} for i in allowed_scenes]}
    write_json(out/'input.json',data)
    parts=[{'type':'text','text':json.dumps(data)}]
    for frame in frames:
        parts.extend(image_content(frame))
    system='''Revise the allowed scenes to explain the supplied development questions.
Use source references as factual authority; student doubts are not truth. This pilot
requires a compass-oriented map diagram. Code will create an N-up/E-right compass,
a horizontal boundary and one/two arrows ending on it from the declared bearings.
Choose each flow's FROM source bearing and opposite TO travel bearing from references.
Do not output pixel coordinates. Explain the distinction between a wind's origin
and its motion in clear spoken English. Preserve other teaching steps and keep the
whole lesson within155spoken words; about20words per edited scene. No optional seasons.
Scene indices are ZERO-BASED and explicitly attached to each editable_scenes item.
Keep EACH original scene's teaching purpose and relative order; do not insert a new
introduction or shift the Northern/Southern/Convergence scenes to different indices.
Each edited diagram MUST have1or2nonemptyflow objects, including convergence scenes.
Revise every allowed scene, no others. Return JSON only:
{"replacements":[{"scene":1,"title":"short title","narration":"English explanation",
"caption":"short caption","diagram":{"boundary_label":"Equator",
"flows":[{"name":"short name","from":"NE","to":"SW","color":"#b32938",
"reference_id":"R1","reference_quote":"exact quote from that reference statement"}]},
"reason":"which question is addressed"}]}.
Names <=18characters, title<=65, caption<=120. Use1..2flows/scene. No scores or claims
of learning. Schema/geometry checks do not certify the domain semantics.
'''
    messages=[{'role':'system','content':system},{'role':'user','content':parts}]
    for attempt in range(2):
        raw=client.chat(messages,purpose=f'compass_revision:{case["id"]}:{attempt}',max_tokens=4500)
        write_json(out/f'raw_{attempt}.json',raw)
        try:
            candidate,receipt=apply_revision(plan,raw,case,references,allowed_scenes)
            write_json(out/'receipt.json',receipt)
            return candidate,receipt
        except (ValueError,TypeError,KeyError) as exc:
            write_json(out/f'error_{attempt}.json',{'error':str(exc)})
            if attempt:
                raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                {'role':'user','content':'Correct the same proposal on the same references: '+str(exc)+'. Return complete JSON.'}])
