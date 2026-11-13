"""Evidence-limited layer ordering for ordinary diagram strokes.

Black/white counterfactuals distinguish hidden authored strokes from absent ones.
An explicit model-selected dependency may put a detected occluder behind a stroke.
All primitives remain byte-equivalent as JSON objects; only their order changes.
This does not decide whether an occlusion was pedagogically intentional.
"""
from __future__ import annotations

import copy
import heapq
import json
from pathlib import Path

import numpy as np

from .common import digest, public_case, write_json
from .evidence import image_content
from .scene import render_frame

VERSION = 'source-preserving-layer-order-v1'
STROKES = {'line', 'arrow', 'arc', 'polyline'}
PROTECTED = {'state_visual', 'source_visual', 'spoken_units', 'teaching_cues',
             'nephron_path', 'contact_pair', 'bond_cashflows'}


def _static(p):
    return all(p.get(k, 0) == 0 for k in ('appear', 'dx', 'dy'))


def _ordinary(scene):
    return not PROTECTED.intersection(scene) and all(p['type'] in
        {'text', 'line', 'arrow', 'rect', 'circle', 'arc', 'sector', 'polyline'}
        for p in scene['primitives'])


def _support(scene, index, *, isolate=False, remove=None):
    """Pixels affected by changing this stroke's color, after other drawing."""
    arrays = []
    for color in ('#000000', '#ffffff'):
        probe = copy.deepcopy(scene)
        target = probe['primitives'][index]
        target['color'] = color
        if isolate:
            probe['primitives'] = [target]
        elif remove is not None:
            probe['primitives'].pop(remove)
        arrays.append(np.asarray(render_frame(probe, .5)[0]).astype(np.int16))
    return np.max(np.abs(arrays[0]-arrays[1]), axis=2) >= 192


def inspect_scene(scene):
    """Identify static strokes with at least80% masked support and later occluders."""
    if not _ordinary(scene) or any(not _static(p) for p in scene['primitives']):
        return []
    rows = []
    for index, p in enumerate(scene['primitives']):
        if p['type'] not in STROKES or p.get('closed'):
            continue
        authored = _support(scene, index, isolate=True)
        n = int(authored.sum())
        if n < 12:
            continue
        visible = _support(scene, index) & authored
        hidden = 1-float(visible.sum())/n
        if hidden < .8:
            continue
        occluders = []
        for later in range(index+1, len(scene['primitives'])):
            q = scene['primitives'][later]
            if q['type'] not in {'rect', 'circle', 'sector', 'polyline'}:
                continue
            if q['type'] == 'polyline' and not q.get('closed'):
                continue
            revealed = _support(scene, index, remove=later) & authored & ~visible
            count = int(revealed.sum())
            if count >= 12:
                occluders.append({'primitive': later, 'revealed_support_pixels': count})
        if occluders:
            rows.append({'primitive': index, 'stroke_type': p['type'],
                'authored_support_pixels': n, 'visible_support_pixels': int(visible.sum()),
                'hidden_fraction': hidden, 'occluders': occluders})
    return rows


def inspect_plan(plan, targets):
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or any(
            type(i) is not int or not 0 <= i < len(plan['scenes']) for i in targets):
        raise ValueError('distinct in-range target scenes required')
    return [{'scene': i, **row} for i in targets for row in inspect_scene(plan['scenes'][i])]


def compile_order(raw, plan, case, targets, inventory=None):
    # Callers may reuse a locally computed inventory; model output cannot supply it.
    inventory = inspect_plan(plan, targets) if inventory is None else inventory
    permitted = {(r['scene'], o['primitive'], r['primitive'])
                 for r in inventory for o in r['occluders']}
    if not isinstance(raw, dict) or set(raw) != {'orders'} or not isinstance(raw['orders'], list):
        raise ValueError('orders array required')
    if len(raw['orders']) > 12:
        raise ValueError('at most12order records')
    edges = {}; records = []
    for row in raw['orders']:
        if not isinstance(row, dict) or set(row) != {'scene','background','foreground','reason','witness'}:
            raise ValueError('order requires scene, background, foreground, reason and witness')
        s, back, front = row['scene'], row['background'], row['foreground']
        if type(s) is not int or type(back) is not int or s not in targets:
            raise ValueError('order outside frozen target scenes')
        if not isinstance(front, list) or not front or any(type(i) is not int for i in front) or len(set(front)) != len(front):
            raise ValueError('distinct foreground indices required')
        if any((s, back, f) not in permitted for f in front):
            raise ValueError('only detected stroke/occluder pairs may be reordered')
        if not isinstance(row['reason'], str) or not row['reason'].strip():
            raise ValueError('semantic ordering reason required')
        quote = row['witness']
        if not isinstance(quote, str) or not quote.strip() or quote not in public_case(case)['prompt_text']:
            raise ValueError('exact public-task witness required')
        edges.setdefault(s, set()).update((back, f) for f in front)
        records.append(copy.deepcopy(row))
    candidate = copy.deepcopy(plan); permutations = []
    for s, constraints in sorted(edges.items()):
        n = len(plan['scenes'][s]['primitives'])
        incoming = [0]*n; outgoing = [[] for _ in range(n)]
        for a,b in sorted(constraints):
            incoming[b] += 1; outgoing[a].append(b)
        available = [i for i in range(n) if incoming[i] == 0]
        heapq.heapify(available); order = []
        while available:
            a = heapq.heappop(available); order.append(a)
            for b in outgoing[a]:
                incoming[b] -= 1
                if incoming[b] == 0: heapq.heappush(available, b)
        if len(order) != n:
            raise ValueError('cyclic layer dependencies')
        candidate['scenes'][s]['primitives'] = [copy.deepcopy(plan['scenes'][s]['primitives'][i]) for i in order]
        # Visibility must actually improve for every selected stroke. This is an
        # execution check, not a semantic or scientific quality judgment.
        for _, original_index in constraints:
            p = order.index(original_index)
            before = int(_support(plan['scenes'][s], original_index).sum())
            after = int(_support(candidate['scenes'][s], p).sum())
            if after <= before:
                raise ValueError('selected ordering does not reveal the requested stroke')
        permutations.append({'scene': s, 'original_indices_in_new_order': order})
    return candidate, {'version': VERSION, 'status': 'changed' if edges else 'unchanged',
        'source_plan_hash': digest(plan), 'candidate_plan_hash': digest(candidate),
        'orders': records, 'permutations': permutations, 'inventory': inventory,
        'semantic_acceptance': 'unverified',
        'scope': 'Static ordinary-stroke visibility and exact primitive/text preservation only; no content truth, continuous perception or teaching certification.'}


def propose(client, plan, case, targets, frames, out):
    out = Path(out); inventory = inspect_plan(plan, targets)
    data = {'public_task': public_case(case), 'target_scenes': targets, 'occlusion_inventory': inventory,
        'scenes': [{'scene': i, 'title': s['title'], 'narration': s['narration'], 'caption': s['caption'],
            'primitives': [{'primitive_index': j, **p} for j,p in enumerate(s['primitives'])]}
            for i,s in enumerate(plan['scenes']) if i in targets]}
    write_json(out/'input.json', data)
    if not inventory:
        return compile_order({'orders': []}, plan, case, targets, inventory)
    content = [{'type':'text','text':json.dumps(data)}]
    for frame in frames: content.extend(image_content(frame))
    system = '''Decide whether a detected covered stroke should be visible in this educational diagram.
Return only JSON {orders:[{scene:integer,background:integer,foreground:[integer],
reason:"why the depicted relationship requires this ordering",witness:"exact public-task span"}]}.
All indices are the explicit zero-based indices. Select ONLY detected stroke/occluder pairs.
Background is a later filled shape currently masking a stroke; the compiler places it behind
the selected foreground strokes. Keep intentional occlusion when needed for the subject.
An empty orders list is valid. Do not invent strokes, move objects, change labels or styles,
fix unrelated facts, or optimize scores. The original objects, text and actual audio remain.
Use the public prompt and actual frames to decide whether this is an accidental masking of
the requested relation. A color-probe finding alone does not prove a pedagogical defect.
Do not mistake a filled object's physical interior occlusion for an error without context.'''
    messages = [{'role':'system','content':system},{'role':'user','content':content}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'layer_order:{case["id"]}:{attempt}', max_tokens=2600)
        write_json(out/f'raw_{attempt}.json', raw)
        try:
            result, receipt = compile_order(raw, plan, case, targets, inventory)
            write_json(out/'program.json', raw)
            return result, receipt
        except (ValueError,KeyError,TypeError) as exc:
            write_json(out/f'error_{attempt}.json', {'error': str(exc)})
            if attempt: raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                {'role':'user','content':'Correct only the schema/dependency error; empty orders remain valid: '+str(exc)}])
