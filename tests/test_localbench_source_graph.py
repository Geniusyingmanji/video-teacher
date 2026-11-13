import copy

import numpy as np
import pytest
from PIL import Image, ImageDraw

from localbench.source_graph import (apply_path, bind_graph, ellipse, prepare_graph,
                                     shortest_path_facts, validate_spec)


def fixture_graph():
    spec = {'nodes': [{'label': label, 'bbox': [x-.065, y-.065, x+.065, y+.065]}
                      for label, x, y in [('S', .15, .3), ('T', .85, .3), ('U', .5, .3), ('V', .5, .75)]],
            'edges': [['S', 'U'], ['U', 'T'], ['U', 'V']],
            'start': 'S', 'goal': 'T', 'directed': False, 'weighted': False}
    image = Image.new('RGB', (600, 400), 'white')
    draw = ImageDraw.Draw(image)
    centers = {n['label']: tuple(ellipse(n, image.size)[:2]) for n in spec['nodes']}
    for a, b in spec['edges']:
        draw.line([centers[a], centers[b]], fill='black', width=4)
    for node in spec['nodes']:
        draw.ellipse(tuple(v*s for v, s in zip(node['bbox'], (600, 400, 600, 400))), fill='white', outline='black', width=4)
        draw.text(centers[node['label']], node['label'], fill='black', anchor='mm')
    return image, spec


def test_pixel_edges_override_hallucinated_and_missing_model_edges():
    image, spec = fixture_graph()
    spec['edges'] = [['S', 'T'], ['U', 'T'], ['U', 'V']]
    recovered, facts, receipt = prepare_graph(image, spec)
    assert facts['path'] == ['S', 'U', 'T']
    assert facts['edge_count'] == 2
    assert facts['number_of_shortest_paths'] == 1
    assert receipt['model_only_edges'] == [['S', 'T']]
    assert receipt['pixel_only_edges'] == [['S', 'U']]


def test_recolor_changes_only_path_ink_preserves_nodes_and_nonpath_edge():
    image, spec = fixture_graph()
    recovered, facts, _ = prepare_graph(image, spec)
    before = np.array(image)
    after = np.array(apply_path(image, recovered, facts['path_edges']))
    changed = np.any(after != before, axis=2)
    assert changed.any()
    assert not changed[before.min(axis=2) > 210].any()
    # Entire lower branch and node V remain pixel-identical.
    assert np.array_equal(before[155:], after[155:])
    yy, xx = np.ogrid[:400, :600]
    for node in spec['nodes']:
        cx, cy, rx, ry = ellipse(node, image.size)
        disk = ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 1
        assert np.array_equal(before[disk], after[disk])
    assert np.array_equal(before, np.array(apply_path(image, recovered, facts['path_edges'], 0)))
    partial = np.array(apply_path(image, recovered, facts['path_edges'], .25))
    assert np.count_nonzero(np.any(partial != before, axis=2)) < np.count_nonzero(changed)
    with pytest.raises(ValueError, match='computed shortest path'):
        apply_path(image, recovered, [['S', 'T']])


def test_bfs_counts_tied_shortest_paths_and_rejects_unreachable_goal():
    _, spec = fixture_graph()
    spec['edges'] = [['S', 'U'], ['U', 'T'], ['S', 'V'], ['V', 'T']]
    facts = shortest_path_facts(spec)
    assert facts['edge_count'] == 2 and facts['number_of_shortest_paths'] == 2
    assert facts['layers'] == [['S'], ['U', 'V'], ['T']]
    spec['edges'] = [['S', 'U']]
    with pytest.raises(ValueError, match='unreachable'):
        shortest_path_facts(spec)


@pytest.mark.parametrize('field,value', [('directed', True), ('weighted', True), ('start', 'Z')])
def test_unsupported_graph_semantics_fail_explicitly(field, value):
    _, spec = fixture_graph()
    spec[field] = value
    with pytest.raises(ValueError):
        validate_spec(spec)


def test_binding_holds_original_until_demonstration_and_keeps_bound_source(tmp_path):
    from localbench.source_scene import edited_reference
    image, spec = fixture_graph()
    path = tmp_path/'graph.png'
    image.save(path)
    spec, _, _ = prepare_graph(image, spec)
    scene = {'duration_s': 10, 'narration': 'Find the path using breadth first search.',
             'teaching_lines': ['Explore one edge at a time.']}
    plan = bind_graph({'scenes': [copy.deepcopy(scene) for _ in range(6)]}, {'local_path': str(path)}, spec)
    for s in plan['scenes'][:3]:
        assert not s['source_visual']['edits']
    assert plan['scenes'][3]['source_visual']['edits'][0]['reveal']
    assert not plan['scenes'][4]['source_visual']['edits'][0]['reveal']
    slides, issues = edited_reference(plan['scenes'][5]['source_visual'], apply_edits=False)
    assert not issues and np.array_equal(np.array(slides), np.array(image))
