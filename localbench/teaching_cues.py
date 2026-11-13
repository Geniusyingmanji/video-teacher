"""Bind explanatory captions and action completion to executed scene state."""
from __future__ import annotations

import copy
import math

VERSION = 'executed-teaching-cues-v1'
POLICY = {'version': VERSION, 'motion_start': .10, 'motion_end': .72}


def bind(plan, *, countable_particles=False, clear_particle_labels=False):
    result = copy.deepcopy(plan)
    for scene in result['scenes']:
        if scene.get('state_visual'):
            scene['teaching_cues'] = dict(POLICY)
            if countable_particles:
                scene['teaching_cues']['particle_layout'] = 'countable-v2' if clear_particle_labels else 'countable-v1'
    return result


def validate(policy):
    if not isinstance(policy, dict) or set(policy)-{'particle_layout'} != set(POLICY) or policy['version'] != VERSION:
        raise ValueError('invalid teaching cue policy')
    if 'particle_layout' in policy and policy['particle_layout'] not in {'countable-v1','countable-v2'}:
        raise ValueError('invalid particle layout')
    a, b = policy['motion_start'], policy['motion_end']
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in (a, b)) or not 0 <= a < b <= 1:
        raise ValueError('teaching cue motion window must be ordered within 0..1')


def state_at(scene, progress):
    """One clock drives BOTH moving geometry and completion language."""
    spec = scene.get('state_visual')
    if not spec or not scene.get('teaching_cues'):
        return spec, progress
    policy = scene['teaching_cues']
    validate(policy)
    motion = spec['phase'] in {'detach', 'rearrange', 'transfer', 'refraction', 'compare'}
    executed = min(1, max(0, (progress-policy['motion_start']) /
                             (policy['motion_end']-policy['motion_start']))) if motion else progress
    return {**spec, 'teaching_cues': policy}, executed


def caption(scene, progress):
    if not scene.get('teaching_cues') or not scene.get('state_visual'):
        return scene['caption']
    spec, executed = state_at(scene, progress)
    kind, phase, state = spec['state']['kind'], spec['phase'], spec['state']
    if kind == 'triangle_cut':
        return {'identify': 'Each colored sector shows the angle inside one corner.',
                'detach': ('The three separate pieces keep their original angles.' if executed == 1 else
                           'Cut out each corner; keep its angle and its label unchanged.'),
                'rearrange': ('The three angles now meet at one vertex, without gaps.' if executed == 1 else
                              'Translate and rotate each piece; its angle stays fixed.'),
                'straight_angle': 'The outer rays form a straight angle: 180 degrees.'}[phase]
    if kind == 'triangle_sum':
        return {'examples': 'Compare the shapes; each triangle has three interior angles.',
                'identify': 'Each colored sector marks the angle inside a corner.',
                'highlight': 'Keep each angle fixed in size as its corner piece is moved.',
                'rearrange': ('The three unchanged angles now meet at one vertex.' if executed == 1 else
                              'Moving and rotating the pieces; their angle sizes stay fixed.'),
                'straight_angle': 'The three angles fill a straight angle: 180 degrees.',
                'recap': 'Rearrangement preserves each angle, so their sum is 180 degrees.'}.get(phase, scene['caption'])
    if kind == 'linear_equation':
        a, b, c = state['a'], state['b'], state['c']
        return {'balance': 'An equal change on both sides keeps the two values equal.',
                'subtract': f'Subtract ({b}) on BOTH sides: the constant cancels, leaving {a}x = {c-b}.',
                'divide': f'Divide BOTH sides by {a}: the coefficient cancels, leaving x = {state["solution"]}.',
                'check': 'Substitute into the ORIGINAL equation; check that both sides agree.'}.get(phase, scene['caption'])
    if kind == 'electron_transfer':
        return {'neutral': 'Neutral atoms: sodium has 11 electrons; chlorine has 17.',
                'valence': 'Outer shells: Na has one electron to lose; Cl needs one more.',
                'transfer': ('Transfer complete: Na has 10 electrons and Cl has 18.' if executed == 1 else
                             'One electron moves from Na to Cl; the protons stay fixed.'),
                'ions': 'Losing a negative electron makes Na positive; gaining it makes Cl negative.',
                'check': 'Count all electrons: 10 + 18 = 28. The total charge remains zero.'}.get(phase, scene['caption'])
    if kind == 'binary_search':
        row = state['trace'][min(len(state['trace'])-1, int(executed*len(state['trace'])))] if phase == 'compare' else state['trace'][-1]
        if phase == 'compare':
            if row['decision'] == 'found':
                return f'Compare VALUE {row["value"]} with target {state["target"]}: equal, so return INDEX {row["mid"]}.'
            direction = 'right' if row['decision'] == 'right' else 'left'
            return f'The comparison selects the {direction} half; sorted order rules out the other half.'
        if phase == 'result' and row['decision'] == 'found':
            return f'Index {row["mid"]} identifies the location; value {row["value"]} is the requested target.'
    return scene['caption']
