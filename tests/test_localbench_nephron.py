import copy

import pytest

from localbench.nephron import bind, diagram, rounded, topology, validate_topology
from localbench.scene import inspect_layout, render_frame, validate_plan


def fixture():
    case = {'id': 'nephron', 'target_duration_s': 75,
            'prompt_text': 'Show the human nephron: glomerulus, proximal tubule, loop of Henle, distal tubule, collecting duct.'}
    words = ['The nephron is the functional unit of the kidney.',
             "The glomerulus lies inside Bowman's capsule.",
             'The proximal tubule supports reabsorption.',
             'The descending and ascending limbs have different functions.',
             'The distal tubule leads to the collecting duct.',
             'Trace the flow from filtration onward.']
    plan = {'case_id': 'nephron', 'scenes': [
        {'title': 'Nephron', 'caption': 'Follow the fluid route.', 'narration': word,
         'duration_s': 12.5, 'primitives': [{'type': 'text', 'x': .3, 'y': .3, 'text': 'Old'}]}
        for word in words]}
    return plan, case


def test_connected_route_rejects_disconnection_reversal_and_invalid_junction():
    good = topology()
    validate_topology(good)
    for change in ('outlet', 'loop', 'distal', 'junction', 'reversed_loop', 'duct', 'short_path'):
        state = copy.deepcopy(good)
        if change == 'outlet': state['capsule_outlet'][0] += 10
        elif change == 'loop': state['loop'][0][0] += 10
        elif change == 'distal': state['distal'][0][0] += 10
        elif change == 'junction': state['collecting_join_index'] = 0
        elif change == 'reversed_loop': state['loop'][2][1] = 150
        elif change == 'duct': state['collecting'][2][1] = 180
        else: state['proximal'] = state['proximal'][:2]
        with pytest.raises(ValueError): validate_topology(state)


def test_corner_rounding_preserves_component_junctions():
    state = topology()
    for name in ('proximal', 'loop', 'distal', 'collecting'):
        path = state[name]
        smooth = rounded(path)
        assert smooth[0] == path[0] and smooth[-1] == path[-1]
    assert rounded(state['proximal'])[-1] == rounded(state['loop'])[0]
    assert rounded(state['loop'])[-1] == rounded(state['distal'])[0]
    # The straight duct includes its exact junction after rounding.
    assert state['distal'][-1] in rounded(state['collecting'])


def test_blood_and_filtrate_have_distinct_connected_render_paths():
    parts = diagram(0)
    blood = parts[1]
    afferent, efferent = parts[2:4]
    assert blood['points'][0] == [afferent['x2'], afferent['y2']]
    assert blood['points'][-1] == [efferent['x'], efferent['y']]
    proximal, loop, distal, collecting = parts[4:8]
    assert blood['color'] not in {p['color'] for p in parts[4:8]}
    assert proximal['points'][-1] == loop['points'][0]
    assert loop['points'][-1] == distal['points'][0]
    assert distal['points'][-1] in collecting['points']


def test_lesson_preserves_narration_timing_and_has_legible_nonoverlapping_labels():
    plan, case = fixture(); before = copy.deepcopy(plan)
    candidate, receipt = bind(plan, case)
    assert receipt['status'] == 'compiled' and plan == before
    validate_plan(candidate, case)
    assert not inspect_layout(candidate, include_warnings=True)
    for i, (old, new) in enumerate(zip(before['scenes'], candidate['scenes'])):
        assert all(new[k] == old[k] for k in ('title', 'caption', 'narration', 'duration_s'))
        frame, issues = render_frame(new, .5, index=i, total=6)
        assert not issues and frame.size == (1024, 576)
        labels = {p.get('text') for p in new['primitives']}
        assert {'Glomerulus', 'Proximal tubule', 'Loop of Henle', 'Distal tubule', 'Collecting duct'} <= labels


def test_compiler_scope_and_render_state_mismatch():
    plan, case = fixture()
    assert bind(plan, {**case, 'prompt_text': 'Explain fluid flow in a pipe.'})[1]['status'] == 'unsupported'
    candidate, _ = bind(plan, case)
    candidate['scenes'][2]['primitives'][4]['points'][-1][0] += .05
    with pytest.raises(ValueError, match='differ'): validate_plan(candidate, case)
    plan['scenes'][3]['narration'] = 'An unrelated process.'
    assert bind(plan, case)[1]['status'] == 'unsupported'
