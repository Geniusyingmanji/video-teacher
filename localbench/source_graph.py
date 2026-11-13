"""Recover straight unweighted graph edges from public pixels, solve, and recolor ink."""
from __future__ import annotations

import copy
import json
import math
import re
from collections import deque
from functools import lru_cache
from itertools import combinations

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import least_squares

VERSION = 'localbench-source-graph-dev1'
EXTRACT_SYSTEM = '''Read the PUBLIC question and original graph. Return exactly one JSON
object {nodes:[{label,bbox:[x0,y0,x1,y1]}],edges:[[u,v],...],start,goal,directed,weighted}.
List every visible node and every directly drawn edge; do not solve the shortest path.
bbox tightly encloses each node's circular or elliptical OUTER BORDER in the ORIGINAL
whole image, normalized to width and height. Include the letter inside each node.
Read start and goal from the question. Mark directed and weighted as JSON booleans.
Trace lines to their actual endpoints: proximity does not imply an edge. List each
undirected edge only once. No private answer or reference solution is supplied.'''

PLAN_SYSTEM = '''Write a complete English-narrated shortest-path lesson from the PUBLIC
question, original image and CODE-COMPUTED facts. Return one JSON object {case_id,scenes}.
Exactly SIX scenes: (0) givens and goal; (1) BFS explores by number of edges, not drawn
length; (2) explain computed BFS layers through the target; (3) demonstrate the computed
path as its edges turn red in order; (4) verify that no earlier layer reached the goal;
(5) recap the path and edge count. The original graph stays fixed in the upper viewport.
Only solution edges change color, first in scene 3, and remain red in scenes 4 and 5.
The lower panel may show layer sets and path strings; do not claim layers change the
original node colors. Explain why this works for an unweighted graph.
Each scene: title (<=65 chars),duration_s,narration,caption (<=120 chars),slide_text
(<=140 chars),teaching_lines (1 or 2 lines <=65 chars),primitives:[{type:"text",x:0.5,
y:0.5,text:"graph"}]. Six durations sum to target. For a 60-second lesson, narration
should total 120..135 words (about 18..23 words per scene). Speak paths as "A, then B"
or "A to B" rather than hyphens/arrows, and use spoken words for numbers.
Use the supplied path and layers accurately; no new edges or unsupported uniqueness
claims. Facts come from source-pixel recovery and BFS, not an expert answer key.
Do not output source_edits, node coordinates or an alternative solution.'''


def validate_spec(spec):
    fields = {'nodes', 'edges', 'start', 'goal', 'directed', 'weighted'}
    if not isinstance(spec, dict) or set(spec) != fields:
        raise ValueError('exact source-graph fields required')
    if spec['directed'] is not False or spec['weighted'] is not False:
        raise ValueError('this backend supports only undirected unweighted graphs')
    if not isinstance(spec['nodes'], list) or not 2 <= len(spec['nodes']) <= 24:
        raise ValueError('graph needs 2..24 nodes')
    labels = set()
    for node in spec['nodes']:
        label = node.get('label')
        if not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9]{1,4}', label) or label in labels:
            raise ValueError('node labels must be unique short alphanumeric strings')
        labels.add(label)
        box = node.get('bbox')
        if not isinstance(box, list) or len(box) != 4 or any(
                type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in box):
            raise ValueError('node bbox requires four normalized coordinates')
        x0, y0, x1, y1 = box
        if not .015 <= x1-x0 <= .4 or not .015 <= y1-y0 <= .4:
            raise ValueError('node bbox is empty or outside supported size')
    if spec['start'] not in labels or spec['goal'] not in labels or spec['start'] == spec['goal']:
        raise ValueError('distinct existing start and goal required')
    if not isinstance(spec['edges'], list) or len(spec['edges']) > 100:
        raise ValueError('bounded edge list required')
    seen = set()
    for edge in spec['edges']:
        if not isinstance(edge, list) or len(edge) != 2 or any(n not in labels for n in edge) or edge[0] == edge[1]:
            raise ValueError('edges must connect two existing distinct nodes')
        key = tuple(sorted(edge))
        if key in seen:
            raise ValueError('duplicate graph edge')
        seen.add(key)


def ellipse(node, size):
    w, h = size
    x0, y0, x1, y1 = np.array(node['bbox']) * [w, h, w, h]
    return np.array([(x0+x1)/2, (y0+y1)/2, (x1-x0)/2, (y1-y0)/2])


def refine_nodes(image, spec):
    """Fit ellipse borders locally, without changing labels or semantic endpoints."""
    validate_spec(spec)
    refined = copy.deepcopy(spec)
    dark = np.asarray(image.convert('RGB')).max(axis=2) < 160
    distance = ndimage.distance_transform_edt(~dark)
    angles = np.linspace(0, 2*np.pi, 192, endpoint=False)
    records = []
    for node in refined['nodes']:
        initial = ellipse(node, image.size)
        margin = np.array([12., 12., initial[2]*.18, initial[3]*.18])
        def residual(p):
            cx, cy, rx, ry = p
            return ndimage.map_coordinates(distance, [cy+ry*np.sin(angles), cx+rx*np.cos(angles)], order=1)
        fit = least_squares(residual, initial, bounds=(initial-margin, initial+margin),
                            loss='soft_l1', f_scale=1., max_nfev=180, diff_step=.002)
        final_residual = residual(fit.x)
        p90 = float(np.percentile(final_residual, 90))
        # Stopping at max_nfev is harmless when the actual border already fits.
        # Acceptance uses geometric residuals, not the optimizer's stop category.
        if p90 > 2.5 or float(np.percentile(final_residual, 99)) > 4.5:
            raise ValueError(f'node {node["label"]}: proposed ellipse does not fit source border (p90={p90:.2f}px)')
        cx, cy, rx, ry = fit.x
        w, h = image.size
        node['bbox'] = [float(v) for v in ((cx-rx)/w, (cy-ry)/h, (cx+rx)/w, (cy+ry)/h)]
        records.append({'label': node['label'], 'p90_border_distance_px': p90,
                        'optimizer_success': bool(fit.success), 'evaluations': fit.nfev,
                        'initial_ellipse_px': initial.tolist(), 'fitted_ellipse_px': fit.x.tolist()})
    validate_spec(refined)
    return refined, records


def recover_segments(image, spec):
    """Remove node disks, then require each remaining ink component to be one edge."""
    validate_spec(spec)
    w, h = image.size
    yy, xx = np.ogrid[:h, :w]
    ellipses = {n['label']: ellipse(n, image.size) for n in spec['nodes']}
    node_mask = np.zeros((h, w), bool)
    for cx, cy, rx, ry in ellipses.values():
        # Lines may join just outside the ellipse; exclude this junction as well.
        disk = ((xx-cx)/(rx+12))**2 + ((yy-cy)/(ry+12))**2 <= 1
        if np.any(node_mask & disk):
            raise ValueError('overlapping node disks are unsupported')
        node_mask |= disk
    dark = np.asarray(image.convert('RGB')).max(axis=2) < 160
    components, count = ndimage.label(dark & ~node_mask, structure=np.ones((3, 3)))
    objects = ndimage.find_objects(components)
    segments = []
    seen = set()
    for i in range(1, count+1):
        bounds = objects[i-1]
        ys, xs = np.nonzero(components[bounds] == i)
        if len(xs) < 10:
            continue  # JPEG speckles, not a supported edge.
        points = np.c_[xs+bounds[1].start, ys+bounds[0].start].astype(float)
        center = points.mean(axis=0)
        _, _, vh = np.linalg.svd(points-center, full_matrices=False)
        direction = vh[0]
        along = (points-center) @ direction
        cross = (points-center) @ vh[1]
        p95 = float(np.percentile(abs(cross), 95))
        if p95 > 3.5 or np.ptp(along) < 12:
            raise ValueError('unresolved source ink: crossing/curved edge, incomplete node mask, or unsupported annotation')
        endpoints = [center+direction*along.min(), center+direction*along.max()]
        names = []
        for point in endpoints:
            distances = []
            for label, (cx, cy, rx, ry) in ellipses.items():
                radial = math.sqrt(((point[0]-cx)/rx)**2 + ((point[1]-cy)/ry)**2)
                distances.append((abs(radial-1)*min(rx, ry), label))
            distances.sort()
            if distances[0][0] > 25 or distances[1][0]-distances[0][0] < 8:
                raise ValueError('edge endpoint does not have a unique nearby node border')
            names.append(distances[0][1])
        key = tuple(sorted(names))
        if key[0] == key[1] or key in seen:
            raise ValueError('loop, duplicate or fragmented edge is unsupported')
        seen.add(key)
        segments.append({'edge': list(key), 'endpoints_px': [p.tolist() for p in endpoints],
                         'ink_pixels': len(points), 'p95_line_residual_px': p95})
    if not segments:
        raise ValueError('no source edges recovered')
    return sorted(segments, key=lambda s: s['edge'])


def shortest_path_facts(spec):
    validate_spec(spec)
    adjacency = {n['label']: [] for n in spec['nodes']}
    for a, b in spec['edges']:
        adjacency[a].append(b)
        adjacency[b].append(a)
    for neighbors in adjacency.values():
        neighbors.sort()
    start, goal = spec['start'], spec['goal']
    distance, parent, ways = {start: 0}, {}, {start: 1}
    queue = deque([start])
    while queue:
        a = queue.popleft()
        for b in adjacency[a]:
            if b not in distance:
                distance[b], parent[b], ways[b] = distance[a]+1, a, ways[a]
                queue.append(b)
            elif distance[b] == distance[a]+1:
                ways[b] += ways[a]
    if goal not in distance:
        raise ValueError('goal is unreachable; no path recoloring can satisfy this task')
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return {'version': VERSION, 'start': start, 'goal': goal, 'adjacency': adjacency,
            'layers': [sorted(n for n in distance if distance[n] == d) for d in range(max(distance.values())+1)],
            'distances': distance, 'path': path, 'path_edges': [list(e) for e in zip(path, path[1:])],
            'edge_count': distance[goal], 'number_of_shortest_paths': ways[goal],
            'proof': 'BFS first reaches the goal in this layer. Every edge has unit cost; all earlier layers are exhausted.',
            'scope': 'Correct for the recovered undirected unweighted graph; labels and task endpoints remain model-extracted.'}


def prepare_graph(image, spec):
    refined, nodes = refine_nodes(image, spec)
    segments = recover_segments(image, refined)
    proposed = {tuple(sorted(e)) for e in spec['edges']}
    recovered = {tuple(s['edge']) for s in segments}
    refined['edges'] = [list(e) for e in sorted(recovered)]
    facts = shortest_path_facts(refined)
    receipt = {'version': VERSION, 'node_fits': nodes, 'segments': segments,
               'model_only_edges': [list(e) for e in sorted(proposed-recovered)],
               'pixel_only_edges': [list(e) for e in sorted(recovered-proposed)],
               'policy': 'Use source-pixel recovered edges after geometric checks; preserve model labels/start/goal.',
               'limitations': 'Single straight edge per connected component; no arrows, weights, crossed edges or curved edges.'}
    return refined, facts, receipt


@lru_cache(maxsize=8)
def _edge_masks(source_bytes, size, spec_json):
    spec = json.loads(spec_json)
    original = Image.frombytes('RGB', size, source_bytes)
    pixels = np.asarray(original)
    w, h = size
    yy, xx = np.ogrid[:h, :w]
    protect = np.zeros((h, w), bool)
    for node in spec['nodes']:
        cx, cy, rx, ry = ellipse(node, size)
        protect |= ((xx-cx)/(rx+3))**2 + ((yy-cy)/(ry+3))**2 <= 1
    masks = {}
    for segment in recover_segments(original, spec):
        a, b = np.array(segment['endpoints_px'])
        vector = b-a
        length = np.linalg.norm(vector)
        unit = vector/length
        along = (xx-a[0])*unit[0] + (yy-a[1])*unit[1]
        cross = abs((xx-a[0])*unit[1] - (yy-a[1])*unit[0])
        # Recolor only existing dark ink in this bounded edge corridor.
        mask = (cross <= 4) & (along >= -18) & (along <= length+18) & ~protect & (pixels.max(axis=2) < 210)
        masks[tuple(segment['edge'])] = mask
    memberships = np.sum(list(masks.values()), axis=0)
    # Shared junction ink is ambiguous and must not recolor an unrelated edge.
    masks = {key: mask & (memberships == 1) for key, mask in masks.items()}
    return masks


def apply_path(image, spec, path_edges, progress=1.):
    if not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError('bounded path reveal progress required')
    # The render state cannot silently introduce a path that code did not solve.
    if path_edges != shortest_path_facts(spec)['path_edges']:
        raise ValueError('requested marks differ from the code-computed shortest path')
    original = image.convert('RGB')
    pixels = np.array(original)
    masks = _edge_masks(original.tobytes(), original.size, json.dumps(spec, sort_keys=True))
    count = min(len(path_edges), math.ceil(progress*len(path_edges)))
    for edge in path_edges[:count]:
        pixels[masks[tuple(sorted(edge))]] = [213, 38, 44]
    return Image.fromarray(pixels)


def bind_graph(plan, attachment, spec):
    from .source_scene import bind_source
    out = copy.deepcopy(plan)
    if len(out.get('scenes', [])) != 6:
        raise ValueError('graph lesson requires six phases')
    words = sum(len(s.get('narration', '').split()) for s in out['scenes'])
    budget = int(sum(s['duration_s'] for s in out['scenes'])*2.4)
    if words > budget:
        raise ValueError(f'graph narration is too long: {words} words, maximum {budget}')
    facts = shortest_path_facts(spec)
    out['source_edits'] = [{'id': 'shortest_path', 'kind': 'highlight_path', 'spec': spec,
                            'path_edges': facts['path_edges'], 'from_scene': 3}]
    return bind_source(out, attachment, allow_graphs=True)
