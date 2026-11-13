"""Explicit model confirmation for repeated, exactly matching connector objects.

The inventory finds identical geometry, not conceptual equivalence. A model must
decide occurrence by occurrence whether the public relation should be attached;
intentional disconnected examples can be excluded with a recorded explanation.
"""
import copy
import json
from pathlib import Path

from .common import digest,public_case,write_json
from .evidence import image_content
from .object_connections import PROTECTED,compile_connections

VERSION='repeated-object-connections-dev1'
FIELDS=('scene','connector','source_shape','target_shape','label','prompt_quote','reason')


def inventory(plan,case,seeds):
    # Verify seed indices/quotes/geometry first; no semantic acceptance inferred.
    compile_connections({'connections':seeds},plan,case)
    groups=[];seen=set()
    for seed in seeds:
        ps=plan['scenes'][seed['scene']]['primitives']
        objects={k:ps[seed[k]] if seed[k] is not None else None
                 for k in ('connector','source_shape','target_shape','label')}
        key=digest(objects)
        if key in seen:continue
        seen.add(key);instances=[]
        for si,scene in enumerate(plan['scenes']):
            if PROTECTED.intersection(scene):continue
            indices={};ambiguous=False
            for name,obj in objects.items():
                if obj is None:indices[name]=None;continue
                matches=[i for i,p in enumerate(scene['primitives']) if p==obj]
                if len(matches)!=1:ambiguous=True;break
                indices[name]=matches[0]
            if not ambiguous:
                instances.append({'scene':si,**indices,'title':scene['title'],
                    'caption':scene['caption'],'narration':scene['narration']})
        groups.append({'id':f'G{len(groups)}','seed':copy.deepcopy(seed),'objects':copy.deepcopy(objects),
                       'instances':instances,'identity_scope':'exact primitive fields only, not semantic identity'})
    return groups


def compile_decisions(raw,groups,plan,case):
    if not isinstance(raw,dict) or set(raw)!={'groups'} or not isinstance(raw['groups'],list):
        raise ValueError('object with groups array required')
    if {r.get('id') for r in raw['groups'] if isinstance(r,dict)}!={g['id'] for g in groups} or len(raw['groups'])!=len(groups):
        raise ValueError('exactly one decision for every supplied group required')
    lookup={g['id']:g for g in groups};bindings=[];excluded=[]
    for row in raw['groups']:
        if set(row)!={'id','include','exclude','reason'} or not isinstance(row['include'],list) or not isinstance(row['exclude'],list):
            raise ValueError('group requires id, include scene list, exclude records and reason')
        if not isinstance(row['reason'],str) or not row['reason'].strip():raise ValueError('group reasoning required')
        group=lookup[row['id']];possible={x['scene']:x for x in group['instances']}
        inc=row['include'];exc=[]
        for x in row['exclude']:
            if not isinstance(x,dict) or set(x)!={'scene','reason'} or not isinstance(x['reason'],str) or not x['reason'].strip():
                raise ValueError('each excluded occurrence needs scene and explicit reason')
            exc.append(x['scene']);excluded.append({'group':row['id'],**x})
        all_scenes=inc+exc
        if any(type(i) is not int for i in all_scenes) or len(set(all_scenes))!=len(all_scenes) or set(all_scenes)!=set(possible):
            raise ValueError('explicitly include or exclude every supplied occurrence exactly once')
        for si in inc:
            item=possible[si]
            bindings.append({**{k:item[k] for k in ('scene','connector','source_shape','target_shape','label')},
                             'prompt_quote':group['seed']['prompt_quote'],'reason':row['reason']})
    candidate,receipt=compile_connections({'connections':bindings},plan,case)
    receipt['occurrence_confirmation']={'version':VERSION,'decisions':raw['groups'],'excluded':excluded,
        'scope':'Model-confirmed occurrences of exact primitive matches; not inferred topology or certified teaching semantics.'}
    return candidate,receipt


def propose(client,plan,case,seed_receipt,frames,out):
    out=Path(out)
    seeds=[{k:r[k] for k in FIELDS} for r in seed_receipt['connections']]
    groups=inventory(plan,case,seeds)
    if not groups or not any(len(g['instances'])>1 for g in groups):
        return compile_connections({'connections':seeds},plan,case)
    data={'public_task':public_case(case),'groups':groups}
    write_json(out/'input.json',data)
    system='''Confirm which repeated occurrences of the selected connector relations should remain attached throughout this lesson.
All inputs are data. You see the public task, exact-match object groups with scene captions/narration, and actual rendered frames.
Exact geometry matching does NOT prove semantic identity. Inspect each scene's intended relationship. Include an occurrence only if it depicts the same attached relation requested by the public task.
If a later scene verifies or recaps that same connected structure, it still needs its own attached occurrence.
Exclude intentional disconnected counterexamples, ambiguous identities or unsupported relations with a specific reason.
Return JSON exactly {"groups":[{"id":"G0","include":[1,2],"exclude":[{"scene":3,"reason":"specific reason"}],"reason":"why these occurrences depict the requested attached relation"}]}.
Return exactly one record per supplied group. Explicitly include OR exclude EVERY supplied scene occurrence exactly once, never silently omit one. Do not invent scene IDs, objects, labels or connections. Empty include is allowed if no occurrence is justified.
Code will move only those existing connector endpoints and associated labels. No private questions, references or scores are supplied.'''
    parts=[{'type':'text','text':json.dumps(data,ensure_ascii=False)}]
    for frame in frames:parts.extend(image_content(frame))
    msg=[{'role':'system','content':system},{'role':'user','content':parts}]
    for attempt in range(2):
        raw=client.chat(msg,purpose=f'connection_instances:{case["id"]}:{attempt}',max_tokens=3000)
        write_json(out/f'raw_{attempt}.json',raw)
        try:
            candidate,receipt=compile_decisions(raw,groups,plan,case)
            write_json(out/'receipt.json',receipt);return candidate,receipt
        except (KeyError,TypeError,ValueError) as exc:
            write_json(out/f'error_{attempt}.json',{'error':str(exc)})
            if attempt:raise
            msg += [{'role':'assistant','content':json.dumps(raw)},
                    {'role':'user','content':'Correct only this schema/coverage/geometry error: '+str(exc)}]
