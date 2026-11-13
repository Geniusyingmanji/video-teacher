"""Explicit, source-bound insertion of an experimental mechanism diagram.

This checks rendered occupancy, not semantic correctness. A caller must select
the scene and any replaceable existing chain before seeing comparative scores.
Existing diagrams are never automatically compressed or deleted to make space.
"""
from __future__ import annotations

import copy
import math

from PIL import ImageChops

from .common import digest
from .mechanism_chain import REGION, compile_extractive
from .scene import FPS, render_frame

VERSION = 'mechanism-binding-v1'
PROTECTED = {'state_visual', 'source_visual', 'teaching_cues', 'spoken_units',
             'nephron_path', 'contact_pair', 'bond_cashflows'}
SIMPLE = {'circle', 'rect', 'text', 'line', 'arrow', 'arc', 'sector', 'polyline'}


def _box():
    x, y, w, h = REGION
    # Outward rounding includes outlines on the region boundary.
    return (math.floor(64 + x * 896), math.floor(112 + y * 302),
            math.ceil(64 + (x + w) * 896) + 1,
            math.ceil(112 + (y + h) * 302) + 1)


def inspect_binding(plan, binding):
    """Check every encoded scene frame, plus its terminal state, before an API call."""
    if not isinstance(binding, dict) or set(binding) != {'plan_hash', 'scene', 'replace_indices'}:
        raise ValueError('binding requires plan_hash, scene and replace_indices')
    if binding['plan_hash'] != digest(plan):
        raise ValueError('binding refers to a different source plan')
    index = binding['scene']
    if type(index) is not int or not 0 <= index < len(plan['scenes']):
        raise ValueError('binding scene is out of range')
    scene = plan['scenes'][index]
    receipt = {'version': VERSION, 'binding': copy.deepcopy(binding),
               'region': list(REGION), 'semantic_acceptance': 'unverified'}

    def refuse(reason, **details):
        return {**receipt, 'status': 'not_applicable', 'reason': reason, **details}

    protected = sorted(PROTECTED.intersection(scene))
    if protected:
        return refuse('protected_scene_backend', protected_fields=protected)
    primitives = scene.get('primitives')
    if not isinstance(primitives, list) or any(p.get('type') not in SIMPLE for p in primitives):
        return refuse('unsupported_primitive_backend')
    indices = binding['replace_indices']
    if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(primitives) for i in indices):
        raise ValueError('replacement indices must select existing primitives')
    if len(indices) != len(set(indices)):
        raise ValueError('replacement indices must be distinct')
    if not isinstance(scene.get('narration'), str) or not scene['narration'].strip():
        raise ValueError('single-scene narration required')
    duration = scene.get('duration_s')
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 4 <= duration <= 24:
        raise ValueError('scene duration outside renderer bounds')
    kept = [copy.deepcopy(p) for i, p in enumerate(primitives) if i not in indices]
    removed = [copy.deepcopy(primitives[i]) for i in indices]
    # Match encode's cumulative boundary rounding, including fractional durations.
    boundary = sum(s['duration_s'] for s in plan['scenes'][:index])
    count = round((boundary + duration) * FPS) - round(boundary * FPS)
    box = _box()
    for frame in range(count + 1):
        progress = frame / max(1, count - 1) if frame < count else 1.0
        opts = {'index': index, 'total': len(plan['scenes'])}
        empty = render_frame({**scene, 'primitives': []}, progress, **opts)[0]
        preserved = render_frame({**scene, 'primitives': kept}, progress, **opts)[0]
        if ImageChops.difference(empty, preserved).crop(box).getbbox():
            return refuse('preserved_diagram_occupies_region', frame=frame, progress=progress)
        if removed:
            replaced = render_frame({**scene, 'primitives': removed}, progress, **opts)[0]
            diff = ImageChops.difference(empty, replaced)
            diff.paste((0, 0, 0), box)
            if diff.getbbox():
                return refuse('replacement_would_remove_outside_region', frame=frame, progress=progress)
    return {**receipt, 'status': 'eligible', 'checked_frames_including_terminal': count + 1,
            'narration_hash': digest(scene['narration']), 'preserved_primitives_hash': digest(kept),
            'checked_scope': 'Declared source and single scene; preserved diagram is absent from reserved region at every encoded frame. No semantic or actual-video acceptance.'}


def bind_extractive(plan, binding, raw, references):
    receipt = inspect_binding(plan, binding)
    if receipt['status'] != 'eligible':
        return None, receipt
    index = binding['scene']
    primitives, compilation = compile_extractive(raw, plan['scenes'][index]['narration'], references)
    receipt['compilation'] = compilation
    if primitives is None:
        return None, {**receipt, 'status': 'not_applicable', 'reason': compilation['reason']}
    out = copy.deepcopy(plan)
    kept = [p for i, p in enumerate(out['scenes'][index]['primitives']) if i not in binding['replace_indices']]
    out['scenes'][index]['primitives'] = kept + primitives
    return out, {**receipt, 'status': 'bound', 'output_plan_hash': digest(out),
                 'preserved_fields': 'All plan fields except the specified scene primitives; all unselected primitives remain unchanged and in order.'}
