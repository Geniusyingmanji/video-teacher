"""Scoped person-wall interaction compiler with a shared physical contact region."""
from __future__ import annotations

import copy
import math

from .common import public_case

VERSION = 'contact-force-pair-v1'
INK = '#203b55'
RED = '#b3342d'
GREEN = '#226c42'


def interaction():
    # Diagram length is a common arbitrary scale, not a claim of measured newtons.
    return {'bodies': ['person', 'wall'], 'contact_x': 630,
            'wall_bounds': [630, 154, 880, 404],
            'hands': [[630, 234], [630, 286]],
            'forces': [{'actor': 'person', 'recipient': 'wall', 'origin': [630, 260], 'vector': [150, 0]},
                       {'actor': 'wall', 'recipient': 'person', 'origin': [630, 260], 'vector': [-150, 0]}]}


def validate_interaction(state):
    if state.get('bodies') != ['person', 'wall']:
        raise ValueError('this diagram supports one person and one wall')
    x = state['contact_x']; left, top, right, bottom = state['wall_bounds']
    if x != left or not left < right or not top < bottom:
        raise ValueError('contact must be on the wall surface')
    hands = state['hands']
    if len(hands) != 2 or any(h[0] != x or not top < h[1] < bottom for h in hands):
        raise ValueError('both hands must touch the wall')
    a, b = state['forces']
    if (a['actor'], a['recipient'], b['actor'], b['recipient']) != ('person', 'wall', 'wall', 'person'):
        raise ValueError('interaction partners must swap actor and recipient')
    if a['origin'] != b['origin'] or a['origin'][0] != x or not min(h[1] for h in hands) < a['origin'][1] < max(h[1] for h in hands):
        raise ValueError('force origins must share the hand-wall contact region')
    av, bv = a['vector'], b['vector']
    if (len(av) != 2 or len(bv) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in av+bv) or
            not av[0] > 0 or av[1] != 0 or any(u != -v for u, v in zip(av, bv))):
        raise ValueError('the pair must be nonzero, equal and opposite, normal to the wall')
    return state


def diagram(*, show_forces=True, summarize=False, state=None):
    state = validate_interaction(interaction() if state is None else state)
    parts = []
    def xy(x, y):
        return {'x': (x-64)/896, 'y': (y-112)/302}
    def line(a, b, color=INK, width=4, kind='line'):
        return {'type': kind, **xy(*a), 'x2': (b[0]-64)/896,
                'y2': (b[1]-112)/302, 'color': color, 'stroke': width}
    def label(x, y, text, color=INK, size=23):
        return {'type': 'text', **xy(x,y), 'text': text, 'align': 'center', 'font_size': size, 'color': color}

    left,top,right,bottom = state['wall_bounds']
    parts.append({'type':'rect', **xy(left,top), 'w':(right-left)/896,
                  'h':(bottom-top)/302, 'color':'#67798b', 'fill':'#edf1f5'})
    parts.append({'type':'circle', **xy(350,176), 'r':22/302, 'color':INK, 'fill':'#e7f0f8'})
    parts.extend([line((350,198),(328,320),width=6),
                  line((328,320),(286,395),width=6), line((328,320),(386,395),width=6)])
    # Two arms terminate at actual palms on the wall; force arrows are separate.
    for elbow,hand in zip([(475,232),(484,280)],state['hands']):
        parts.append({'type':'polyline', **xy(64,112),
                      'points':[[(x-64)/896,(y-112)/302] for x,y in [(348,217),elbow,hand]],
                      'closed':False, 'color':INK, 'stroke':5})
        parts.append(line((hand[0],hand[1]-7),(hand[0],hand[1]+7),width=6))
    parts.extend([label(324,132,'Person'),label(768,185,'Wall')])
    if show_forces:
        for force,color in zip(state['forces'],[RED,GREEN]):
            start = force['origin']; end = [a+b for a,b in zip(start,force['vector'])]
            parts.append(line(start,end,color,width=5,kind='arrow'))
        parts.extend([label(750,314,'Person on wall',RED),label(490,340,'Wall on person',GREEN)])
    if summarize:
        parts.append(label(638,128,'Equal lengths; opposite directions',size=22))
    return parts


def validate_scene(scene):
    spec = scene['contact_pair']
    if (spec.get('version') != VERSION or type(spec.get('forces_visible')) is not bool or
            type(spec.get('summarize')) is not bool):
        raise ValueError('invalid contact-pair scene binding')
    expected = diagram(state=spec['state'],show_forces=spec['forces_visible'],summarize=spec['summarize'])
    if scene['primitives'] != expected:
        raise ValueError('contact-pair primitives differ from the verified interaction')


def bind(plan, case):
    unsupported = {'status':'unsupported','version':VERSION}
    result = copy.deepcopy(plan); scenes = result.get('scenes',[])
    text = public_case(case).get('prompt_text','').lower()
    if not (all(w in text for w in ('person','wall','force','equal','opposite')) and
            ('third law' in text or 'third-law' in text) and len(scenes)==6):
        return result, unsupported
    if any(s.get('state_visual') or s.get('source_visual') or s.get('contact_pair') for s in scenes):
        return result, unsupported
    words = [s.get('narration','').lower() for s in scenes]
    phases = [('hands','wall'),('person','push','wall'),('simultaneously','person'),
              ('length','opposite'),('different objects','wall','person'),('equal','opposite')]
    if any(not all(w in narration for w in required) for narration,required in zip(words,phases)):
        return result, unsupported
    state = validate_interaction(interaction())
    for i,scene in enumerate(scenes):
        scene['primitives'] = diagram(show_forces=i>0,summarize=i>=3)
        scene['contact_pair'] = {'version':VERSION,'state':copy.deepcopy(state),'forces_visible':i>0,'summarize':i>=3}
    return result, {'status':'compiled','version':VERSION,'scene_indices':list(range(6)),
        'state':state,'preserves_narration':True,
        'scope':'One compatible six-scene person-wall lesson. Shared hand-wall contact; paired vectors appear together and act on distinct bodies. No net-force or motion simulation.'}
