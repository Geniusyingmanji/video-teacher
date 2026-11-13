"""Construct bounded geometry from declared relations; never infer subject roles.

This solver supports one regular tetrahedron and antipodal extensions. It is a
schematic construction, with equal arbitrary radii, not a molecular simulation.
Unsupported or contradictory relations are rejected by the original checker.
"""
from __future__ import annotations

import copy
import math

import numpy as np
from PIL import Image, ImageDraw

from .spatial_graph import compile_graph, draw_graph, projection

VERSION = 'symbolic-spatial-construction-v1'


def _clearance(graph):
    """Minimum node/node and nonincident node/segment clearance, in pixels."""
    from .scene import font
    points, _ = projection(graph)
    draw = ImageDraw.Draw(Image.new('RGB', (1024, 576), 'white'))
    radii = {}
    for node in graph['nodes']:
        box = draw.textbbox((0, 0), node['label'], font=font(22))
        radii[node['id']] = max(18, (box[2] - box[0]) / 2 + 8)
    ids = list(points)
    margins = []
    for i, a in enumerate(ids):
        p = np.array(points[a][:2])
        for b in ids[i + 1:]:
            margins.append(float(np.linalg.norm(p - points[b][:2])) - radii[a] - radii[b])
    for edge in graph['links']:
        a, b = edge['source'], edge['target']
        p, q = np.array(points[a][:2]), np.array(points[b][:2])
        delta = q - p
        for node in ids:
            if node in (a, b):
                continue
            point = np.array(points[node][:2])
            t = float(np.clip(np.dot(point - p, delta) / np.dot(delta, delta), 0, 1))
            # Allow the widest wedge, not just a one-pixel center line.
            margins.append(float(np.linalg.norm(point - (p + t * delta))) - radii[node] - 7)
    return min(margins)


def construct_graph(spec, public_task):
    if not isinstance(spec, dict) or set(spec) != {'nodes', 'links', 'constraints'}:
        raise ValueError('symbolic graph requires exactly nodes, links, constraints')
    if not isinstance(spec['nodes'], list) or not 5 <= len(spec['nodes']) <= 12:
        raise ValueError('symbolic construction requires 5..12 nodes')
    ids = []
    for node in spec['nodes']:
        if not isinstance(node, dict) or set(node) - {'id', 'label', 'color'} or not {'id', 'label'} <= set(node):
            raise ValueError('symbolic nodes require id/label and optional color, no coordinates')
        if not isinstance(node['id'], str):
            raise ValueError('string node IDs required')
        ids.append(node['id'])
    if len(set(ids)) != len(ids):
        raise ValueError('distinct node IDs required')
    constraints = spec['constraints']
    if not isinstance(constraints, list) or len(constraints) > 12:
        raise ValueError('at most 12 constraints required')
    arities = {'tetrahedral': 5, 'opposite_sides': 3, 'perpendicular': 3, 'directed_link': 2}
    for row in constraints:
        if not isinstance(row, dict) or set(row) != {'kind', 'nodes', 'prompt_quote'}:
            raise ValueError('constraint requires kind, nodes and prompt_quote')
        kind, refs = row['kind'], row['nodes']
        if not isinstance(kind, str) or kind not in arities or not isinstance(refs, list):
            raise ValueError('unsupported relation or invalid node references')
        if len(refs) != arities[kind] or any(not isinstance(i, str) or i not in ids for i in refs) or len(set(refs)) != len(refs):
            raise ValueError('correct number of distinct existing node IDs required')
        quote = row['prompt_quote']
        if not isinstance(quote, str) or not quote.strip() or quote not in public_task:
            raise ValueError('exact nonempty public-task quote required')
    seeds = [c for c in constraints if c['kind'] == 'tetrahedral']
    if len(seeds) != 1:
        raise ValueError('construction supports exactly one declared tetrahedron')
    center, *neighbors = seeds[0]['nodes']
    unit_tetrahedron = [
        [1, 0, 0], [-1 / 3, math.sqrt(8) / 3, 0],
        [-1 / 3, -math.sqrt(2) / 3, math.sqrt(6) / 3],
        [-1 / 3, -math.sqrt(2) / 3, -math.sqrt(6) / 3],
    ]
    positions = {center: np.zeros(3)}
    positions.update({i: 2 * np.array(p) for i, p in zip(neighbors, unit_tetrahedron)})
    # Fill only previously unconstructed nodes; final validation detects all
    # conflicting relations. Never project a bad answer into a valid one.
    for _ in range(len(ids)):
        changed = False
        for relation in constraints:
            if relation['kind'] != 'opposite_sides':
                continue
            c, a, b = relation['nodes']
            if c not in positions:
                continue
            if a in positions and b not in positions:
                positions[b] = 2 * positions[c] - positions[a]
                changed = True
            elif b in positions and a not in positions:
                positions[a] = 2 * positions[c] - positions[b]
                changed = True
        if not changed:
            break
    if missing := set(ids) - set(positions):
        raise ValueError('unconstructed nodes: ' + ','.join(sorted(missing)))
    graph = copy.deepcopy(spec)
    for node in graph['nodes']:
        node['xyz'] = positions[node['id']].tolist()
    graph['camera'] = {'azimuth_deg': 0, 'elevation_deg': 0}
    compile_graph(graph, public_task)
    views = []
    for azimuth in range(-75, 76, 15):
        for elevation in (-30, -15, 0, 15, 30):
            camera = {'azimuth_deg': azimuth, 'elevation_deg': elevation}
            graph['camera'] = camera
            try:
                draw_graph(Image.new('RGB', (1024, 576), 'white'), graph)
                margin = _clearance(graph)
                if margin <= 4:
                    raise ValueError('node intersects a nonincident stroke or insufficient clearance')
                views.append({'camera': camera, 'status': 'valid', 'clearance_px': margin})
            except ValueError as exc:
                views.append({'camera': camera, 'status': 'rejected', 'reason': str(exc)})
    valid = [v for v in views if v['status'] == 'valid']
    if not valid:
        raise ValueError('no readable view in the fixed camera search')
    chosen = max(valid, key=lambda v: v['clearance_px'])
    graph['camera'] = chosen['camera']
    compiled = compile_graph(graph, public_task)
    return {**compiled, 'construction_version': VERSION, 'view_search': views,
            'selected_view': chosen, 'construction': 'regular tetrahedron plus declared antipodal extensions',
            'scope': 'Model-declared relations constructed and checked with code. Arbitrary equal radii; no chemical valence, reaction, stereochemical identity, or learning certification.'}
