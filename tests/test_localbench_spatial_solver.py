import copy

import numpy as np
import pytest
from PIL import Image

from localbench.spatial_graph import draw_graph
from localbench.spatial_solver import construct_graph
from test_localbench_spatial_graph import TASK, graph


def symbolic():
    g = graph()
    g.pop('camera')
    for n in g['nodes']:
        n.pop('xyz')
    return g


def test_symbolic_relations_construct_exact_geometry_and_readable_depth_view():
    spec = symbolic()
    before = copy.deepcopy(spec)
    result = construct_graph(spec, TASK)
    assert spec == before
    assert all(c['satisfied'] for c in result['checks'])
    assert result['checks'][0]['cosines'] == pytest.approx([-1 / 3] * 6)
    assert result['selected_view']['clearance_px'] > 4
    receipt = draw_graph(Image.new('RGB', (1024, 576), 'white'), result['graph'])
    assert {'solid_wedge', 'hashed_wedge'} <= {r['style'] for r in receipt['strokes']}
    assert result['semantic_binding_status'] == 'model_proposed_unverified'


def test_constructor_is_independent_of_subject_specific_ids_and_node_order():
    spec = symbolic()
    first = construct_graph(spec, TASK)
    renames = {n['id']: 'P' + str(i) for i, n in enumerate(spec['nodes'])}
    for n in spec['nodes']:
        n['id'] = renames[n['id']]
    for e in spec['links']:
        e.update(source=renames[e['source']], target=renames[e['target']])
    for c in spec['constraints']:
        c['nodes'] = [renames[i] for i in c['nodes']]
    spec['nodes'].reverse()
    second = construct_graph(spec, TASK)
    first_xyz = {renames[n['id']]: n['xyz'] for n in first['graph']['nodes']}
    assert {n['id']: n['xyz'] for n in second['graph']['nodes']} == first_xyz


def test_contradictory_or_incomplete_relations_are_rejected_not_repaired():
    bad = symbolic()
    bad['constraints'].append({'kind': 'opposite_sides', 'nodes': ['C', 'R1', 'Nu'], 'prompt_quote': 'opposite side'})
    with pytest.raises(ValueError, match='unsatisfied.*opposite_sides'):
        construct_graph(bad, TASK)
    bad = symbolic()
    bad['constraints'] = [c for c in bad['constraints'] if c['kind'] != 'opposite_sides']
    with pytest.raises(ValueError, match='unconstructed nodes'):
        construct_graph(bad, TASK)
    bad = symbolic()
    bad['links'][-1].update(source='C', target='Nu')
    with pytest.raises(ValueError, match='directed_link'):
        construct_graph(bad, TASK)


def test_no_coordinate_backdoor_or_private_quote():
    bad = symbolic()
    bad['nodes'][0]['xyz'] = [0, 0, 0]
    with pytest.raises(ValueError, match='no coordinates'):
        construct_graph(bad, TASK)
    bad = symbolic()
    bad['constraints'][0]['prompt_quote'] = 'private answer'
    with pytest.raises(ValueError, match='public-task quote'):
        construct_graph(bad, TASK)


def test_long_labels_reject_when_no_camera_avoids_clutter():
    bad = symbolic()
    for n in bad['nodes']:
        n['label'] = 'WWWWWWWWWWWW'
    with pytest.raises(ValueError, match='no readable view'):
        construct_graph(bad, TASK)
