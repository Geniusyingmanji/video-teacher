"""Bounded angle-cutting compiler with persistent sector identity and rigid motion.

The compiler reads a public task and a six-scene narrated plan. It does not
consume judging references. A diagram is a visual demonstration, not a general
proof of the Euclidean triangle angle-sum theorem.
"""
from __future__ import annotations

import copy
import math
import re

from PIL import ImageDraw

VERSION = 'triangle-cut-v1'
PHASES = ('identify', 'detach', 'rearrange', 'straight_angle')


def sectors(vertices, labels):
    if (len(vertices) != 3 or len(labels) != 3 or len(set(labels)) != 3 or
            any(len(p) != 2 or any(type(v) not in (float, int) or not math.isfinite(v) for v in p)
                for p in vertices)):
        raise ValueError('three finite vertices and distinct sector labels required')
    (ax, ay), (bx, by), (cx, cy) = vertices
    if abs((bx-ax)*(cy-ay)-(by-ay)*(cx-ax)) < 1e-6:
        raise ValueError('degenerate triangle')
    result = []
    for i, (x, y) in enumerate(vertices):
        q, r = vertices[(i+1) % 3], vertices[(i+2) % 3]
        a, b = [math.degrees(math.atan2(p[1]-y, p[0]-x)) % 360 for p in (q, r)]
        diff = (b-a) % 360
        start, sweep = (a, diff) if diff <= 180 else (b, 360-diff)
        result.append({'id': labels[i], 'origin': [x, y], 'start': start, 'sweep': sweep})
    cumulative = 180.0
    # The narrated label order is also the order in the assembled straight
    # angle. This keeps "attach B next to A, then C" true for A/B/C lessons.
    for p in result:
        p['joined_start'] = cumulative
        cumulative += p['sweep']
    if not math.isclose(cumulative, 360, abs_tol=1e-7):
        raise ValueError('invalid triangle angle geometry')
    return result


def snapshot(state, phase, progress):
    if state.get('version') != VERSION or phase not in PHASES:
        raise ValueError('unsupported angle-cutting state')
    if type(progress) not in (float, int) or not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError('progress must be finite within 0..1')
    parts = sectors(state['vertices'], state['labels'])
    radius = state['radius']
    if type(radius) not in (float, int) or not math.isfinite(radius) or not 10 <= radius <= 90:
        raise ValueError('invalid sector radius')
    # All three pieces keep their radius, sweep and ID. Scenes exchange the
    # same terminal/initial state; no fresh positioning at a scene boundary.
    joined = [512, 375]
    detached = [[180, 325], [512, 325], [844, 325]]
    result = []
    for i, p in enumerate(parts):
        amount = min(1, max(0, progress*3-i))
        if phase == 'identify':
            center, angle = p['origin'], p['start']
        elif phase == 'detach':
            side = p['origin'][0]-sum(v[0] for v in state['vertices'])/3
            control = [850 if side > 20 else 174 if side < -20 else p['origin'][0],
                       200 if abs(side) > 20 else 110]
            center = [(1-amount)**2*a+2*(1-amount)*amount*c+amount**2*b
                      for a, c, b in zip(p['origin'], control, detached[i])]
            angle = p['start']
        else:
            rotation = min(1, progress/.25)
            translation = min(1, max(0, (progress-.25)/.75*3-i))
            if phase == 'straight_angle': rotation = translation = 1
            center = [a+(b-a)*translation for a, b in zip(detached[i], joined)]
            delta = (p['joined_start']-p['start']+180) % 360-180
            angle = p['start']+delta*rotation
        # Canonicalize equivalent 0/360 orientations for exact handoff records.
        result.append({'id': p['id'], 'center': center, 'start': angle % 360,
                       'sweep': p['sweep'], 'radius': radius})
    return result


def compile_sequence(plan):
    """Select only an explicit identify → detach → arrange → result sequence.

    Original normalized triangle vertices are interpreted in equal x/y units,
    then uniformly scaled to the panel. This avoids anisotropic stretching of
    an intended acute triangle into an obtuse one. The changed geometry is
    recorded, not claimed pixel-identical to the original renderer.
    """
    result = copy.deepcopy(plan)
    scenes = result.get('scenes', [])
    unsupported = {'status': 'unsupported', 'version': VERSION}
    if len(scenes) != 6:
        return result, unsupported
    words = [s.get('narration', '').lower() for s in scenes]
    if not (re.search(r'\b(label|labeled|labelled)\b', words[1]) and
            re.search(r'\b(detach|cutting|cut)\b', words[2]) and
            'side by side' in words[3] and 'straight line' in words[4]):
        return result, unsupported
    if all(x in words[1] for x in ('alpha', 'beta', 'gamma')):
        labels = ['α', 'β', 'γ']
    elif re.search(r'\ba,?\s+b,?\s+and\s+c\b', words[1]):
        labels = ['A', 'B', 'C']
    else:
        return result, unsupported
    primitives = scenes[1].get('primitives', [])
    polygons = [p for p in primitives if p.get('type') == 'polyline' and p.get('closed') and len(p.get('points', [])) == 3]
    if len(polygons) != 1:
        return result, unsupported
    vertices = polygons[0]['points']
    ordered = []
    for label in labels:
        text = [p for p in primitives if p.get('type') == 'text' and p.get('text') == label]
        if len(text) != 1: return result, unsupported
        distances = [math.dist([text[0]['x'], text[0]['y']], p) for p in vertices]
        ordered.append(distances.index(min(distances)))
    if len(set(ordered)) != 3: return result, unsupported
    vertices = [vertices[i] for i in ordered]
    sectors(vertices, labels)  # fail explicitly on degenerate geometry
    lo = [min(p[i] for p in vertices) for i in (0, 1)]
    hi = [max(p[i] for p in vertices) for i in (0, 1)]
    scale = min(410/(hi[0]-lo[0]), 260/(hi[1]-lo[1]))
    points = [[512+(x-(lo[0]+hi[0])/2)*scale, 265+(y-(lo[1]+hi[1])/2)*scale] for x, y in vertices]
    compiled = sectors(points, labels)
    if any(p['sweep'] < 25 or p['sweep'] > 130 for p in compiled):
        return result, {**unsupported, 'reason': 'angles outside the supported legibility range'}
    radius = min(72, min(math.dist(a, b) for a, b in zip(points, points[1:]+points[:1]))*.4)
    state = {'kind': 'triangle_cut', 'version': VERSION, 'vertices': points, 'labels': labels, 'radius': radius}
    from .teaching_cues import POLICY
    for i, phase in enumerate(PHASES, 1):
        scenes[i]['state_visual'] = {'state': state, 'phase': phase}
        scenes[i]['teaching_cues'] = dict(POLICY)
        scenes[i]['primitives'] = [{'type': 'text', 'x': .1, 'y': .1, 'text': phase}]
    motion_findings = audit_motion(result)
    if motion_findings:
        return copy.deepcopy(plan), {**unsupported, 'reason': 'compiled motion fails geometry checks',
                                    'motion_findings': motion_findings}
    return result, {'status': 'compiled', 'version': VERSION, 'scene_indices': [1, 2, 3, 4],
                    'labels': labels, 'source_vertices_normalized': vertices,
                    'compiled_vertices': points, 'sectors': compiled,
                    'motion_findings': motion_findings,
                    'scope': 'Uniform geometric remapping plus rigid-sector animation; original narration, timing, opening and recap retained.'}


def bind(plan, case):
    from .state import derive_state
    state = derive_state(case)
    if not state or state['kind'] != 'triangle_sum':
        return copy.deepcopy(plan), {'status': 'unsupported', 'version': VERSION}
    result, receipt = compile_sequence(plan)
    if receipt['status'] == 'compiled':
        from .triangle_examples import compile_examples
        result, opening = compile_examples(result)
        receipt['opening_examples'] = opening
        if opening['status'] == 'compiled':
            receipt['scene_indices'] = [0, 1, 2, 3, 4]
            receipt['scope'] += ' Opening replaced with three geometry-classified examples; recap retained.'
    return result, receipt


def audit_motion(plan, fps=12):
    """Check the executed sector masks at every frame on the renderer's clock.

    Interior intersection is an occlusion; a one-pixel shared edge after
    joining is allowed. This checks sector geometry, not all visual quality.
    """
    import numpy as np
    from PIL import Image
    from .teaching_cues import state_at
    findings = []
    for i, scene in enumerate(plan['scenes']):
        if scene.get('state_visual', {}).get('state', {}).get('kind') != 'triangle_cut': continue
        count = max(2, round(scene['duration_s']*fps))
        for n in range(count):
            spec, t = state_at(scene, n/(count-1))
            masks = []
            for p in snapshot(spec['state'], spec['phase'], t):
                image = Image.new('1', (1024, 576)); draw = ImageDraw.Draw(image)
                x, y = p['center']; r = p['radius']; a = p['start']
                draw.pieslice((x-r,y-r,x+r,y+r), a, a+p['sweep'], fill=1)
                box = image.getbbox()
                if box and (box[0] < 48 or box[1] < 107 or box[2] > 976 or box[3] > 437):
                    findings.append({'kind':'sector_outside_safe_panel','scene':i,'frame':n,'id':p['id'],'bbox':list(box)})
                m = np.asarray(image)
                masks.append(m[1:-1,1:-1]&m[:-2,1:-1]&m[2:,1:-1]&m[1:-1,:-2]&m[1:-1,2:])
            overlap = sum(int((a&b).sum()) for j,a in enumerate(masks) for b in masks[j+1:])
            if overlap:
                findings.append({'kind':'sector_overlap','scene':i,'frame':n,'interior_pixels':overlap})
    return findings


def draw_triangle(image, spec, progress):
    from .scene import font
    state, phase = spec['state'], spec['phase']
    parts = snapshot(state, phase, progress)
    draw = ImageDraw.Draw(image)
    colors = ['#1769aa', '#aa5311', '#18826b']
    boxes = []
    def label(x, y, text, color='#183550', size=25):
        face = font(size)
        boxes.append({'text': text, 'bbox': list(draw.textbbox((x, y), text, font=face, anchor='mm'))})
        draw.text((x, y), text, fill=color, font=face, anchor='mm')
    if phase == 'identify' or (phase == 'detach' and progress < 1):
        shade = int(80+175*progress) if phase == 'detach' else 80
        draw.polygon([tuple(p) for p in state['vertices']], outline=(shade, shade, shade), width=3)
    complete = phase == 'straight_angle' or (phase == 'rearrange' and progress == 1)
    for p, color in zip(parts, colors):
        x, y = p['center']; r = p['radius']; angle = p['start']
        draw.pieslice((x-r, y-r, x+r, y+r), angle, angle+p['sweep'], fill=color, outline=color)
        theta = math.radians(angle+p['sweep']/2)
        label(x+.67*r*math.cos(theta), y+.67*r*math.sin(theta), p['id'], color='white', size=23)
    if complete:
        draw.line((360, 375, 664, 375), fill='#183550', width=3)
        label(512, 419, ' + '.join(state['labels'])+' = 180°', size=27)
    return boxes
