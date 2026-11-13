"""Bounded checks between a generated scene's words and computed flow geometry.

This is generator-internal consistency, not a benchmark score or a scientific
truth oracle. It never reads hidden answers or substitutes script for audio.
Only one flow_path and unambiguous affirmative direction language are covered.
"""
from __future__ import annotations

import math
import re

from .flow import compile_flow

VERSION = 'single-flow-language-consistency-v1'


def direction_claims(scene):
    # Mixed alternatives, contrasts, conditions and negations require contextual
    # interpretation outside this small formal checker. Do not pick one reading.
    text = ' '.join(scene.get(k, '') for k in ('title', 'caption', 'narration'))
    if re.search(r'\b(no|not|never|incorrect|wrong|myth|if|would|could|unlike|instead)\b', text, re.I):
        return {}, 'conditional_or_contrastive_language'
    if not re.search(r'\b(spiral\w*|flow\w*|air|wind\w*)\b', text, re.I):
        return {}, 'no_flow_context'
    pairs = {'rotation': {'ccw': r'\b(?:counter[ -]?clockwise|anti[ -]?clockwise)\b',
                          'cw': r'(?<!counter-)(?<!counter )(?<!anti-)(?<!anti )\bclockwise\b'},
             'radial_direction': {'inward': r'\b(?:inward|inwards|inflow)\b',
                                  'outward': r'\b(?:outward|outwards|outflow)\b'}}
    claims = {}
    for field, patterns in pairs.items():
        matches = [(value, m.group()) for value, pattern in patterns.items()
                   for m in [re.search(pattern, text, re.I)] if m]
        if len(matches) == 1:
            claims[field] = {'expected': matches[0][0], 'quote': matches[0][1],
                             'source': 'authored_scene_words'}
    return claims, 'unambiguous_fields_only' if claims else 'no_single_direction_claim'


def flow_witness(spec):
    flow = compile_flow(spec)
    cx, cy = flow['center']
    vectors = [(x-cx, cy-y) for x, y in flow['points']]
    crosses = [a[0]*b[1]-a[1]*b[0] for a, b in zip(vectors, vectors[1:])]
    rotation = 'ccw' if all(c > 0 for c in crosses) else 'cw' if all(c < 0 for c in crosses) else 'unverified'
    radii = [math.hypot(*v) for v in vectors]
    diffs = [b-a for a,b in zip(radii, radii[1:])]
    radial = ('inward' if all(d < -1e-8 for d in diffs) else
              'outward' if all(d > 1e-8 for d in diffs) else
              'constant' if all(abs(d) <= 1e-8 for d in diffs) else 'unverified')
    return {'rotation': rotation, 'radial_direction': radial,
            'start_radius_px': radii[0], 'end_radius_px': radii[-1],
            'basis': 'Successive computed path vectors in x-right/y-up coordinates; arrow tips follow increasing path parameter.'}


def inspect_plan(plan):
    records = []
    for i, scene in enumerate(plan.get('scenes', [])):
        flows = [(j,p) for j,p in enumerate(scene.get('primitives', [])) if p.get('type') == 'flow_path']
        if not flows:
            continue
        claims, scope = direction_claims(scene)
        if len(flows) != 1 or scene.get('source_visual') or scene.get('state_visual'):
            records.append({'scene': i, 'status': 'unverified', 'reason': 'requires_one_visible_flow_path'})
            continue
        j, spec = flows[0]
        witness = flow_witness(spec)
        for field, claim in claims.items():
            records.append({'scene': i, 'primitive': j, 'field': field, **claim,
                            'observed': witness[field], 'witness': witness,
                            'status': 'consistent' if claim['expected'] == witness[field] else 'conflict'})
        if not claims:
            records.append({'scene': i, 'primitive': j, 'status': 'unverified', 'reason': scope})
    return {'version': VERSION, 'records': records,
            'scope': 'Authored text versus generated path; not actual speech, scientific correctness or final-video certification.'}


def validate(plan, *, reference=None):
    if reference is not None:
        for i, scene in enumerate(reference.get('scenes', [])):
            old = [p for p in scene.get('primitives', []) if p.get('type') == 'flow_path']
            claims, _ = direction_claims(scene)
            if len(old) == 1 and claims:
                new_scene = plan['scenes'][i]
                new = [p for p in new_scene.get('primitives', []) if p.get('type') == 'flow_path']
                if len(new) != 1 or new_scene.get('source_visual') or new_scene.get('state_visual'):
                    raise ValueError(f'scene {i}: cannot verify the declared flow after representation change; retain one flow_path')
    result = inspect_plan(plan)
    conflicts = [r for r in result['records'] if r['status'] == 'conflict']
    if conflicts:
        descriptions = [f"scene {r['scene']} flow {r['field']}: words {r['quote']!r} require {r['expected']}, computed path is {r['observed']}"
                        for r in conflicts]
        raise ValueError('program-language conflict: '+'; '.join(descriptions))
    return result
