"""Geometry-derived opening examples for an already compiled angle lesson."""
from __future__ import annotations

import copy
import math

from .triangle import sectors

VERSION = 'triangle-examples-v1'


def classify(points):
    angles = [p['sweep'] for p in sectors(points, ['A', 'B', 'C'])]
    largest = max(angles)
    return ('Right' if math.isclose(largest, 90, abs_tol=1e-7) else
            'Obtuse' if largest > 90 else 'Acute'), angles


def compile_examples(plan):
    """Retain narration/timing; show an actual acute/right/obtuse trio.

    The acute example is a similarity copy of the following focus triangle,
    so the lesson really selects one of its opening examples. A non-acute
    focus or a different opening narration remains unsupported.
    """
    result = copy.deepcopy(plan)
    unsupported = {'status': 'unsupported', 'version': VERSION}
    scenes = result.get('scenes', [])
    if len(scenes) != 6:
        return result, unsupported
    spec = scenes[1].get('state_visual', {})
    if spec.get('state', {}).get('kind') != 'triangle_cut' or spec.get('phase') != 'identify':
        return result, unsupported
    opening = scenes[0]
    words = opening.get('narration', '').lower()
    # Do not preserve narration that explicitly assigns a different count/order.
    if ('triangle' not in words or any(w in words for w in ('two triangles', 'equilateral', 'isosceles')) or
            ('obtuse' in words and not ('acute' in words and 'right' in words and words.index('acute') < words.index('right') < words.index('obtuse')))):
        return result, unsupported
    focus = spec['state']['vertices']
    focus_type, focus_angles = classify(focus)
    if focus_type != 'Acute':
        return result, {**unsupported, 'reason': 'opening sequence currently requires an acute focus'}
    lo = [min(p[k] for p in focus) for k in (0, 1)]
    hi = [max(p[k] for p in focus) for k in (0, 1)]
    scale = min(190/(hi[0]-lo[0]), 180/(hi[1]-lo[1]))
    acute = [[210+(x-(lo[0]+hi[0])/2)*scale, 270+(y-(lo[1]+hi[1])/2)*scale] for x,y in focus]
    shapes = [acute, [[422,360],[602,360],[422,180]], [[702,350],[922,350],[785,280]]]
    labels = ['Acute', 'Right', 'Obtuse']; colors = ['#1769aa', '#18826b', '#aa5311']
    primitives = []; examples = []
    def xy(x, y): return {'x': (x-64)/896, 'y': (y-112)/302}
    for index, (points, expected, color, center) in enumerate(zip(shapes, labels, colors, [210,512,812])):
        actual, angles = classify(points)
        if actual != expected:
            raise ValueError('opening geometry does not match its computed type')
        primitives.append({'type':'polyline','x':0,'y':0,'closed':True,
                           'points':[[(x-64)/896,(y-112)/302] for x,y in points],
                           'color':color,'fill':'#edf4fb','stroke':3})
        if actual == 'Right':
            # Mark the perpendicular sides at their actual shared vertex.
            primitives.append({'type':'polyline','x':0,'y':0,
                               'points':[[(x-64)/896,(y-112)/302] for x,y in [(422,341),(441,341),(441,360)]],
                               'color':color,'stroke':3})
        primitives.append({'type':'text',**xy(center,400),'text':actual,'align':'center','font_size':27,'color':color})
        examples.append({'type':actual,'vertices_pixels':points,'angles_degrees':angles,
                         'same_shape_as_focus':index==0})
    opening.pop('state_visual', None); opening.pop('teaching_cues', None)
    opening['primitives'] = primitives
    opening['caption'] = 'Three different triangles. Next, examine the acute triangle.'
    opening['slide_text'] = 'Acute, right, and obtuse triangles.\nNext: the acute triangle.'
    return result, {'status':'compiled','version':VERSION,'scene_indices':[0],
                    'examples':examples,'focus_angles_degrees':focus_angles,
                    'scope':'Three classified examples in rendered pixel coordinates; first is a similarity copy of the following focus. Narration and duration retained.'}
