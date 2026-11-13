"""Model-bound, executable guards for pure reversal edits of paired arrows.

The model chooses a task relation and arrow identities before seeing a patch.
Geometry checks direction only; task semantics and object binding stay unverified.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from .common import digest, public_case, write_json
from .evidence import image_content

VERSION = 'paired-arrow-reversal-guard-v1'
RELATIONS = {'toward_each_other', 'away_from_each_other', 'opposite_parallel'}


def eligible_scenes(source):
    result = []
    for index, scene in enumerate(source['scenes']):
        arrows = []
        for j, primitive in enumerate(scene['primitives']):
            try:
                vector(primitive)
            except ValueError:
                continue
            arrows.append(j)
        if len(arrows) >= 2:
            result.append({'scene': index, 'arrow_indices': arrows})
    return result


def vector(arrow):
    if arrow.get('type') != 'arrow' or any(arrow.get(k, 0) for k in ('dx', 'dy')):
        raise ValueError('stationary arrow geometry required')
    values = [arrow.get(k) for k in ('x', 'y', 'x2', 'y2')]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('finite arrow endpoints required')
    x, y, x2, y2 = values
    v = (x2-x, y2-y)
    length = math.hypot(*v)
    if length < 1e-6:
        raise ValueError('zero-length arrow cannot encode direction')
    return ((x+x2)/2, (y+y2)/2), (v[0]/length, v[1]/length)


def relation_measure(a, b, relation):
    ca, va = vector(a); cb, vb = vector(b)
    axis = (cb[0]-ca[0], cb[1]-ca[1])
    length = math.hypot(*axis)
    if length < 1e-6:
        raise ValueError('distinct arrow centers required')
    axis = (axis[0]/length, axis[1]/length)
    dot = lambda u, v: sum(x*y for x, y in zip(u, v))
    pa, pb, parallel = dot(va, axis), dot(vb, axis), dot(va, vb)
    if relation == 'toward_each_other':
        satisfied = pa > .1 and pb < -.1
    elif relation == 'away_from_each_other':
        satisfied = pa < -.1 and pb > .1
    elif relation == 'opposite_parallel':
        satisfied = parallel < -.99
    else:
        raise ValueError('unsupported paired-arrow relation')
    return {'satisfied': satisfied, 'first_projection': pa, 'second_projection': pb,
            'direction_cosine': parallel,
            'scope': 'Normalized diagram directions only, not speeds, physical trajectories or knowledge truth.'}


def bind(raw, source, case):
    if not isinstance(raw, dict) or set(raw) != {'constraints'} or not isinstance(raw['constraints'], list):
        raise ValueError('constraints array required')
    if len(raw['constraints']) > 12:
        raise ValueError('at most12constraints')
    constraints = []; seen = set()
    for r in raw['constraints']:
        if not isinstance(r, dict) or set(r) != {'scene', 'arrows', 'relation', 'prompt_quote', 'reason'}:
            raise ValueError('constraint needs scene, arrows, relation, prompt_quote and reason')
        s, indices = r['scene'], r['arrows']
        if type(s) is not int or not 0 <= s < len(source['scenes']):
            raise ValueError('invalid scene index')
        primitives = source['scenes'][s]['primitives']
        if not isinstance(indices, list) or len(indices) != 2 or any(type(i) is not int or not 0 <= i < len(primitives) for i in indices) or len(set(indices)) != 2:
            raise ValueError('two distinct in-range arrow indices required')
        if r['relation'] not in RELATIONS:
            raise ValueError('unsupported relation')
        key = (s, tuple(sorted(indices)))
        if key in seen:
            raise ValueError('duplicate arrow pair')
        seen.add(key)
        if not isinstance(r['prompt_quote'], str) or not r['prompt_quote'].strip() or r['prompt_quote'] not in public_case(case)['prompt_text']:
            raise ValueError('exact public-task quote required')
        if not isinstance(r['reason'], str) or not r['reason'].strip():
            raise ValueError('object/relation binding reason required')
        measure = relation_measure(*(primitives[i] for i in indices), r['relation'])
        constraints.append({**copy.deepcopy(r), 'source_measure': measure})
    return {'version': VERSION, 'source_plan_hash': digest(source), 'public_task_hash': digest(public_case(case)),
            'constraints': constraints, 'semantic_binding_status': 'model_proposed_unverified'}


def check(contract, source, candidate):
    if contract.get('version') != VERSION or contract.get('source_plan_hash') != digest(source):
        raise ValueError('stale direction contract')
    if len(source['scenes']) != len(candidate['scenes']):
        raise ValueError('scene identity changed')
    records = []
    for row in contract['constraints']:
        scene, ids = row['scene'], row['arrows']
        old = source['scenes'][scene]['primitives']; new = candidate['scenes'][scene]['primitives']
        record = {'scene': scene, 'arrows': ids, 'relation': row['relation']}
        if not row['source_measure']['satisfied']:
            record['status'] = 'source_relation_unsatisfied'
        elif len(old) != len(new) or any(old[i] != new[i] for i in range(len(old)) if i not in ids):
            record['status'] = 'binding_changed_unassessed'
        else:
            def support(p):
                return sorted([(p.get('x'), p.get('y')), (p.get('x2'), p.get('y2'))])
            def attributes(p):
                return {k: v for k, v in p.items() if k not in {'x', 'y', 'x2', 'y2'}}
            if any(support(old[i]) != support(new[i]) or attributes(old[i]) != attributes(new[i]) for i in ids):
                record['status'] = 'not_a_pure_reversal_unassessed'
            else:
                after = relation_measure(*(new[i] for i in ids), row['relation'])
                record.update(status='preserved' if after['satisfied'] else 'violated',
                              source_measure=row['source_measure'], candidate_measure=after)
        records.append(record)
    violations = [r for r in records if r['status'] == 'violated']
    return {'version': VERSION, 'source_plan_hash': digest(source), 'candidate_plan_hash': digest(candidate),
        'status': 'reject_reversal' if violations else 'no_detected_reversal_violation',
        'constraints_checked': len(records), 'records': records,
        'semantic_binding_status': contract['semantic_binding_status'],
        'scope': 'Only pure paired-arrow reversal edits with stable surrounding primitives. No full patch acceptance or ground-truth certification.'}


def propose(client, source, case, frames, out):
    out = Path(out)
    eligible = eligible_scenes(source)
    data = {'public_task': public_case(case),
            'eligible_scenes': eligible,
            'scenes': [{'scene': i, 'title': s['title'], 'narration': s['narration'],
                        'primitives': [{'primitive_index': j, **p} for j, p in enumerate(s['primitives'])]}
                       for i, s in enumerate(source['scenes'])]}
    write_json(out/'input.json', data)
    if not eligible:
        result = bind({'constraints': []}, source, case)
        result['binding_status'] = 'no_eligible_arrow_pairs'
        write_json(out/'contract.json', result)
        return result
    content = [{'type': 'text', 'text': json.dumps(data)}]
    for frame in frames:
        content.extend(image_content(frame))
    messages = [{'role': 'system', 'content': '''Bind public-task motion relationships to pairs of existing diagram arrows.
You see the source diagram only, not a proposed patch, scores or expert answers.
Output JSON {"constraints":[{"scene":0,"arrows":[0,1],"relation":"toward_each_other",
"prompt_quote":"exact public-task span","reason":"which objects these arrows represent and why this relation follows from the task"}]}.
Allowed relations: toward_each_other, away_from_each_other, opposite_parallel.
Use the public task to determine the intended relation; do not call an existing arrow correct merely because it is present.
Identify the actual arrow indices from the numbered primitives and actual frame labels.
Only select ordinary stationary arrows; do not confuse object outlines with motion vectors.
Toward/away compares each direction to the line joining the arrow centers; opposite_parallel checks antiparallel directions.
Arrows convey direction only, not a speed magnitude. This geometry does not prove physical dynamics.
You may return an empty constraints array or omit ambiguous bindings. Do not invent objects,
change the source, or force every scene into one of these relationships.'''},
        {'role': 'user', 'content': content}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'arrow_direction_binding:{case["id"]}:{attempt}', max_tokens=2400)
        write_json(out/f'raw_{attempt}.json', raw)
        try:
            result = bind(raw, source, case)
            result['binding_status'] = 'bound' if result['constraints'] else 'no_relations_bound'
            write_json(out/'contract.json', result)
            return result
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out/f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                             {'role': 'user', 'content': 'Repair only the structure/binding error; omission is allowed: '+str(exc)}])
