"""Shared semantic routes compiled from existing object bounds, without new text.

Models select objects and named anchors; code derives arrows and carrier motion
from the same endpoints. This checks execution consistency, not whether the
selected objects, sources, or direction correctly explain the lesson.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from .common import digest, public_case, write_json

VERSION = 'shared-object-anchored-routes-v1'
INDEXED_PROPOSAL_VERSION = 'shared-object-indexed-proposal-v2'
AUTO_REPLACE_VERSION = 'shared-object-auto-replacement-v2'
LABEL_GUARD_VERSION = 'shared-object-owner-border-labels-v3'
CONFIGURED_PROPOSAL_VERSION = 'shared-object-configured-proposal-v3'
ANCHORS = {'top': (.5, 0), 'bottom': (.5, 1), 'left': (0, .5), 'right': (1, .5),
           'inner_top_center': (.5, .18), 'inner_bottom_center': (.5, .82),
           'inner_top_left': (.18, .18), 'inner_bottom_left': (.18, .82),
           'inner_top_right': (.82, .18), 'inner_bottom_right': (.82, .82)}
PROTECTED = {'state_visual', 'source_visual', 'spoken_units', 'teaching_cues',
             'nephron_path', 'contact_pair', 'bond_cashflows'}


def _index(value, length):
    if type(value) is not int or not 0 <= value < length:
        raise ValueError('source index outside existing plan')
    return value


def _source(plan, pointer):
    if not isinstance(pointer, dict) or set(pointer) != {'scene', 'primitive'}:
        raise ValueError('source pointer requires scene and primitive')
    scene = plan['scenes'][_index(pointer['scene'], len(plan['scenes']))]
    if PROTECTED.intersection(scene):
        raise ValueError('protected source backend')
    return scene['primitives'][_index(pointer['primitive'], len(scene['primitives']))]


def bounds(primitive):
    """Pixel bounds of static source circles, rectangles or polylines."""
    if any(primitive.get(k, 0) != 0 for k in ('dx', 'dy', 'appear')):
        raise ValueError('route anchors must be static and present for the whole scene')
    x, y = 64 + 896 * primitive['x'], 112 + 302 * primitive['y']
    kind = primitive['type']
    if kind == 'circle':
        r = primitive.get('r', .08) * 302
        box = [x-r, y-r, x+r, y+r]
    elif kind == 'rect':
        box = [x, y, x+primitive.get('w', .12)*896, y+primitive.get('h', .2)*302]
    elif kind == 'polyline':
        points = primitive['points']
        box = [64+min(p[0] for p in points)*896, 112+min(p[1] for p in points)*302,
               64+max(p[0] for p in points)*896, 112+max(p[1] for p in points)*302]
    else:
        raise ValueError('anchor owner must be an existing circle, rect or polyline')
    if any(not math.isfinite(v) for v in box) or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('nondegenerate finite anchor owner required')
    return box


def _point(box, anchor):
    if anchor not in ANCHORS:
        raise ValueError('unknown named object anchor')
    x, y = ANCHORS[anchor]
    return [box[0] + x*(box[2]-box[0]), box[1] + y*(box[3]-box[1])]


def label_position(x, y, text, align, direction, owner_boxes):
    """Keep newly generated labels wholly inside or outside each anchor owner."""
    from PIL import Image, ImageDraw
    from .scene import font
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    anchor = {'left': 'lt', 'right': 'rt', 'center': 'mm'}[align]
    for _ in range(len(owner_boxes)+1):
        changed = False
        for box in owner_boxes:
            a, b, c, d = draw.textbbox((x, y), text, font=font(24), anchor=anchor)
            intersects = max(a, box[0]) < min(c, box[2]) and max(b, box[1]) < min(d, box[3])
            inside = box[0] <= a and c <= box[2] and box[1] <= b and d <= box[3]
            if intersects and not inside:
                dx, dy = direction
                if abs(dy) > abs(dx):
                    x += (box[2]+12-a) if dy > 0 else (box[0]-12-c)
                else:
                    y += (box[1]-12-d) if dx > 0 else (box[3]+12-b)
                changed = True
        if not changed: return x, y
    raise ValueError('new label cannot avoid owner borders without conflicting placements')


def compile_program(raw, plan, case, target_scenes, *, auto_replace=False, avoid_owner_borders=False):
    if isinstance(raw, dict) and set(raw) == {'unsupported'} and isinstance(raw['unsupported'], str) and raw['unsupported'].strip():
        return None, {'version': VERSION, 'status': 'not_applicable', 'reason': raw['unsupported']}
    if not isinstance(raw, dict) or set(raw) != {'entities', 'routes', 'scenes'}:
        raise ValueError('exact entities, routes and scenes fields required')
    entities = {}
    if not isinstance(raw['entities'], list) or not 2 <= len(raw['entities']) <= 8:
        raise ValueError('two to eight entity records required')
    for row in raw['entities']:
        if not isinstance(row, dict) or set(row) != {'id', 'shape_source', 'label_source'}:
            raise ValueError('entity requires id, shape_source, label_source')
        name = row['id']
        if not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9_]{0,23}', name) or name in entities:
            raise ValueError('distinct short entity IDs required')
        shape = _source(plan, row['shape_source'])
        if shape['type'] not in {'circle', 'rect', 'polyline'}:
            raise ValueError(f'entity {name}.shape_source={row["shape_source"]} points to {shape["type"]}; '
                             'select an existing circle, rect or polyline using its explicit source index')
        label = _source(plan, row['label_source']) if row['label_source'] is not None else None
        if label is not None and label['type'] != 'text':
            raise ValueError(f'entity {name}.label_source={row["label_source"]} points to {label["type"]}; '
                             'label source must be existing text or null')
        entities[name] = {'shape': shape, 'label': label, 'source': row}
    routes = {}
    if not isinstance(raw['routes'], list) or not 1 <= len(raw['routes']) <= 3:
        raise ValueError('one to three shared routes required')
    for route in raw['routes']:
        if not isinstance(route, dict) or set(route) != {'id', 'waypoints', 'closed', 'markers', 'witnesses'}:
            raise ValueError('route requires id, waypoints, closed, markers, witnesses')
        rid = route['id']
        if not isinstance(rid, str) or not re.fullmatch('[a-z][a-z0-9_]{0,23}', rid) or rid in routes:
            raise ValueError('distinct short route IDs required')
        points = route['waypoints']
        if not isinstance(points, list) or not 2 <= len(points) <= 6:
            raise ValueError('two to six named waypoints required')
        for point in points:
            if not isinstance(point, dict) or set(point) != {'entity', 'anchor'} or point['entity'] not in entities or point['anchor'] not in ANCHORS:
                raise ValueError('waypoint must name an existing entity and supported anchor')
        if type(route['closed']) is not bool or route['closed'] != (points[0] == points[-1]):
            raise ValueError('closed flag must match exact endpoint identity: for closed=true, '
                             'the final waypoint must be '+json.dumps(points[0])+'; do not omit the return edge')
        markers = route['markers']
        if not isinstance(markers, list) or not 1 <= len(markers) <= 3:
            raise ValueError('one to three moving entities required')
        seen = set()
        for marker in markers:
            if not isinstance(marker, dict) or set(marker) != {'entity', 'edge'} or marker['entity'] not in entities:
                raise ValueError('marker requires known entity and edge')
            _index(marker['edge'], len(points)-1)
            name = marker['entity']
            if name in seen or entities[name]['shape']['type'] != 'circle':
                raise ValueError('each moving entity is one source circle, used once per route')
            seen.add(name)
        witnesses = route['witnesses']
        if not isinstance(witnesses, list) or not 1 <= len(witnesses) <= 4:
            raise ValueError('one to four exact public-task or existing-narration witnesses required')
        for witness in witnesses:
            if not isinstance(witness, dict) or set(witness) != {'scene', 'quote'}:
                raise ValueError('witness requires scene (null for public task) and quote')
            source = public_case(case)['prompt_text'] if witness['scene'] is None else plan['scenes'][_index(witness['scene'], len(plan['scenes']))]['narration']
            if not isinstance(witness['quote'], str) or not witness['quote'].strip() or witness['quote'] not in source:
                raise ValueError('witness must be an exact span of its stated source')
        routes[rid] = route
    if not isinstance(raw['scenes'], list) or len(raw['scenes']) != len(target_scenes):
        raise ValueError('every selected scene needs exactly one binding')
    if any(type(row.get('index')) is not int for row in raw['scenes']) or sorted(row['index'] for row in raw['scenes']) != sorted(target_scenes):
        raise ValueError('scene bindings must cover exactly the frozen target scenes')
    output = copy.deepcopy(plan); receipts = []
    for row in raw['scenes']:
        if set(row) != {'index', 'bindings', 'remove_indices', 'routes'}:
            raise ValueError('scene binding requires index, bindings, remove_indices and routes')
        index = _index(row['index'], len(plan['scenes'])); scene = plan['scenes'][index]
        if PROTECTED.intersection(scene):
            raise ValueError('cannot overwrite a protected scene backend')
        removed = copy.deepcopy(row['remove_indices']); original = scene['primitives']
        if not isinstance(removed, list) or len(removed) != len(set(removed)):
            raise ValueError('distinct replacement primitive indices required')
        for k in removed: _index(k, len(original))
        if not isinstance(row['routes'], list) or not row['routes'] or len(set(row['routes'])) != len(row['routes']) or any(k not in routes for k in row['routes']):
            raise ValueError('scene must select existing distinct shared routes')
        needed = {p['entity'] for rid in row['routes'] for p in routes[rid]['waypoints']}
        carriers = {m['entity'] for rid in row['routes'] for m in routes[rid]['markers']}
        allowed = needed | carriers if auto_replace else needed
        if not isinstance(row['bindings'], dict) or not needed <= set(row['bindings']) <= allowed:
            if auto_replace:
                raise ValueError(f'scene {index}: bind every static anchor owner {sorted(needed)}; '
                                 f'optional extra bindings may name only route carriers {sorted(carriers)}, '
                                 'with an existing circle index or -1 for an absent carrier')
            raise ValueError(f'scene {index}: bind exactly the path anchor owners {sorted(needed)}; '
                             f'received {row["bindings"]}. Moving markers are not anchor owners unless a waypoint names them. '
                             'Markers and their dedicated labels are regenerated: include old versions in remove_indices; never use -1 placeholders.')
        auto_removed = []
        if auto_replace:
            for name in carriers:
                if name in needed:
                    raise ValueError('an entity cannot be both static anchor owner and regenerated carrier')
                if name in row['bindings']:
                    k = row['bindings'][name]
                    if type(k) is not int or k < -1:
                        raise ValueError('optional carrier binding must be an existing circle index or -1 for absent')
                    if k != -1:
                        _index(k, len(original))
                        if original[k]['type'] != 'circle':
                            raise ValueError('declared old carrier must be a circle')
                        auto_removed.append(k)
                for pointer in (entities[name]['source']['shape_source'], entities[name]['source']['label_source']):
                    if pointer is not None and pointer['scene'] == index:
                        auto_removed.append(pointer['primitive'])
            removed = sorted(set(removed + auto_removed))
        boxes = {}
        for name in sorted(needed):
            k = row['bindings'][name]
            _index(k, len(original))
            if k in removed:
                raise ValueError('anchor owners must remain visible, not be removed')
            boxes[name] = bounds(original[k])
        kept = [copy.deepcopy(p) for k, p in enumerate(original) if k not in removed]
        added = []; executed = []
        for rid in row['routes']:
            route = routes[rid]
            points = [_point(boxes[p['entity']], p['anchor']) for p in route['waypoints']]
            for a, b in zip(points, points[1:]):
                if math.dist(a, b) < 24:
                    raise ValueError('path segment too short for a legible arrow')
                added.append({'type': 'arrow', 'x': (a[0]-64)/896, 'y': (a[1]-112)/302,
                              'x2': (b[0]-64)/896, 'y2': (b[1]-112)/302, 'color': '#1868ae'})
            for marker in route['markers']:
                entity = entities[marker['entity']]; shape = entity['shape']
                a, b = points[marker['edge']:marker['edge']+2]
                for pointer in (entity['source']['shape_source'], entity['source']['label_source']):
                    if pointer is not None and pointer['scene'] == index and pointer['primitive'] not in removed:
                        raise ValueError('canonical moving object and its label must not be duplicated in their source scene')
                added.append({'type': 'circle', 'x': (a[0]-64)/896, 'y': (a[1]-112)/302,
                              'dx': (b[0]-a[0])/896, 'dy': (b[1]-a[1])/302,
                              'r': shape.get('r', .08), 'color': shape.get('color', '#1868ae'),
                              'fill': shape.get('fill', '#e6f0fa')})
                if entity['label'] is not None:
                    dx, dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx, dy)
                    pad = shape.get('r', .08)*302 + 16
                    x, y = (a[0]+b[0])/2 + dy/length*pad, (a[1]+b[1])/2 - dx/length*pad
                    align = 'center' if abs(dx) >= abs(dy) else 'right' if dy < 0 else 'left'
                    # rt/lt labels are top-anchored; center their glyph height on the edge midpoint.
                    if align != 'center': y -= 12
                    if avoid_owner_borders:
                        x, y = label_position(x, y, entity['label']['text'], align, (dx, dy), list(boxes.values()))
                    added.append({'type': 'text', 'x': (x-64)/896, 'y': (y-112)/302,
                                  'text': entity['label']['text'], 'font_size': 24,
                                  'color': '#14283e', 'align': align})
            executed.append({'id': rid, 'points_px': points, 'markers': copy.deepcopy(route['markers']),
                             'bindings': copy.deepcopy(row['bindings']), 'closed': route['closed']})
        output['scenes'][index]['primitives'] = kept + added
        receipts.append({'scene': index, 'removed_indices': removed,
                         'automatically_replaced_carrier_indices': sorted(set(auto_removed)),
                         'preserved_primitives_hash': digest(kept),
                         'added_primitives_hash': digest(added), 'routes': executed})
    return output, {'version': LABEL_GUARD_VERSION if avoid_owner_borders else AUTO_REPLACE_VERSION if auto_replace else VERSION,
                    'status': 'compiled', 'source_plan_hash': digest(plan),
                    'program_hash': digest(raw), 'output_plan_hash': digest(output), 'scenes': receipts,
                    'semantic_acceptance': 'unverified',
                    'scope': 'Shared identities, named-anchor geometry, arrow/motion agreement and exact witness existence only. No scientific truth or final-video quality certification.'}


def inspect_edit_layout(original, candidate, target_scenes):
    from .rerender import diagram_only_plan
    from .scene import inspect_layout
    _, changed = diagram_only_plan(original, candidate)
    if set(changed) - set(target_scenes):
        raise ValueError('route edit changed an unselected scene')
    source_errors = inspect_layout(original)
    candidate_errors = inspect_layout(candidate)
    untouched = [r for r in candidate_errors if r['scene'] not in target_scenes]
    if untouched != [r for r in source_errors if r['scene'] not in target_scenes]:
        raise ValueError('layout findings changed outside selected scenes')
    return {'blocking_target_errors': [r for r in candidate_errors if r['scene'] in target_scenes],
            'inherited_untouched_errors': untouched, 'all_candidate_errors': candidate_errors,
            'scope': 'Partial diagram edit acceptance only; inherited errors stay in the final-video evaluation.'}


def propose(client, plan, case, target_scenes, out, *, indexed=False,
            auto_replace=False, avoid_owner_borders=False):
    """Propose under the selected compiler rules; all new behavior is opt-in."""
    out = Path(out)
    data = {'public_task': public_case(case), 'target_scenes': target_scenes, 'anchors': ANCHORS}
    if indexed:
        data['indexed_source_scenes'] = [
            {'scene_index': i, 'title': s['title'], 'narration': s['narration'], 'caption': s['caption'],
             'primitives': [{'primitive_index': j, **p} for j, p in enumerate(s['primitives'])]}
            for i, s in enumerate(plan['scenes'])]
        data['proposal_protocol'] = INDEXED_PROPOSAL_VERSION
    else:
        data['source_plan'] = plan
    if auto_replace or avoid_owner_borders:
        data['proposal_protocol'] = CONFIGURED_PROPOSAL_VERSION
        data['compiler_options'] = {'auto_replace': auto_replace,
                                    'avoid_owner_borders': avoid_owner_borders}
    write_json(out/'input.json', data)
    system = '''Repair inconsistent schematic motion using a shared object-anchored route program.
Return only JSON {entities:[{id,shape_source:{scene,primitive},label_source:{scene,primitive}|null}],
routes:[{id,waypoints:[{entity,anchor}],closed:boolean,markers:[{entity,edge}],
witnesses:[{scene:integer|null,quote:"exact existing narration or public-task span"}]}],
scenes:[{index,bindings:{anchor_entity_id:existing_primitive_index},remove_indices:[integers],routes:[route_id]}]}.
Return {"unsupported":"reason"} if no faithful repair fits. Use source indices exactly.
Entities are persistent semantic objects/categories, not freely invented shapes. A marker
must use an existing circle and optional existing text label; no new labels or narration.
Anchor owners may be static circles, rectangles or polylines. Bind each route owner to the
corresponding existing shape in each target scene. The compiler preserves that shape.
Anchors top/bottom/left/right are boundary midpoints; inner_* positions are relative to
the owner's bounds. Code derives both directed arrows and linear marker motion from the
same waypoint sequence. closed=true requires the last waypoint to equal the first.
Each marker moves along its selected zero-based edge for the scene. This is a qualitative
diagram, not a continuous physical simulation; do not invent force laws or material states.
Use one shared route across target scenes when the same circulation is shown. Respect
the public task's center/side and transfer-direction requirements. Remove only the old
paths, moving markers and their dedicated labels that the new program replaces. Preserve
context shapes, unrelated reasoning diagrams, all source facts, narration, captions and
timing. The moving entity and its old label must be removed in their source scene, so no
duplicate is left behind. Include exactly all target scenes. Cite exact public text for
the intended direction/relationship, not a prediction about scores. Do not output coordinates,
styles, scores, teacher/student responses, or any hidden-answer material.'''
    if indexed and auto_replace:
        system += '''\nSource scenes and every primitive have explicit zero-based scene_index/primitive_index.
Read those fields instead of counting list positions. In pointers use {scene:scene_index,
primitive:primitive_index}.
For a closed rectangular path, list five waypoints: the four corners in order and
the first corner again. Use witnesses with scene:null only for exact public prompt
text; use a scene index for narration from that source scene.'''
    elif indexed:
        system += '''\nSource scenes and every primitive have explicit zero-based scene_index/primitive_index.
Read those fields instead of counting list positions. In pointers use {scene:scene_index,
primitive:primitive_index}. bindings contains ONLY entities named in route.waypoints,
not every entity in the registry. Marker entities are copied from their canonical
shape_source/label_source; remove their old versions and old dedicated arrows from
each target scene to avoid duplication. For scenes without an old marker, simply
add the route; never invent an index or use -1. For a closed rectangular path,
list five waypoints: the four corners in order and the first corner again.
Use witnesses with scene:null only for exact public prompt text; use a scene index
for narration from that source scene. These rules do not authorize deleting context.'''
    if auto_replace:
        system += '''\nAutomatic carrier replacement is enabled. bindings MUST contain all static
anchor owners named in the selected routes' waypoints. It MAY additionally contain
moving marker entities from those routes: use the existing circle index, or -1
only if that carrier is absent in this scene. Never use -1 for an anchor owner.
Code removes these declared old carrier circles, and a carrier's canonical
shape_source and label_source when they belong to this scene. Explicitly list old
arrows and any other dedicated old carrier labels in remove_indices; labels in
other scenes are not automatically inferred. Do not list preserved owners or
unrelated context for removal. A carrier cannot also be a static anchor owner.'''
    if avoid_owner_borders:
        system += '''\nCode measures newly generated labels and moves any label crossing an anchor
owner's bounding box outward along the existing path normal with a margin.
This rule does not reposition old unrelated labels or certify readability.
Do not add coordinates or manual label offsets; impossible layouts may still fail.'''
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps(data)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'anchored_routes:{case["id"]}:{attempt}', max_tokens=3800)
        write_json(out/f'raw_{attempt}.json', raw)
        try:
            result, receipt = compile_program(raw, plan, case, target_scenes,
                auto_replace=auto_replace, avoid_owner_borders=avoid_owner_borders)
            if auto_replace or avoid_owner_borders:
                receipt['proposal_protocol'] = CONFIGURED_PROPOSAL_VERSION
                receipt['compiler_options'] = copy.deepcopy(data['compiler_options'])
            if result is not None:
                from .scene import validate_plan
                validate_plan(copy.deepcopy(result), case)
                receipt['layout_scope'] = inspect_edit_layout(plan, result, target_scenes)
                errors = receipt['layout_scope']['blocking_target_errors']
                if errors:
                    raise ValueError('layout errors: '+json.dumps(errors[:5]))
            write_json(out/'program.json', raw)
            return result, receipt
        except (ValueError, KeyError, TypeError) as exc:
            write_json(out/f'error_{attempt}.json', {'error': str(exc)})
            if attempt: raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct this source-binding/geometry/schema error, preserving semantics and context. Unsupported remains valid: '+str(exc)}])
