import copy
import json

import pytest

from localbench.anchored_routes import bounds, compile_program, inspect_edit_layout, label_position, propose
from localbench.scene import render_frame


def fixture():
    first = {'title': 'Transfer', 'caption': 'A particle moves from donor to receiver.',
             'narration': 'The donor transfers a particle to the receiver.', 'duration_s': 10,
             'primitives': [
                 {'type': 'circle', 'x': .25, 'y': .5, 'r': .15},
                 {'type': 'circle', 'x': .75, 'y': .5, 'r': .15},
                 {'type': 'circle', 'x': .5, 'y': .35, 'r': .02, 'fill': '#9b4422'},
                 {'type': 'text', 'x': .5, 'y': .2, 'text': 'e-'}]}
    second = copy.deepcopy(first)
    second['primitives'][0]['x'] = .3
    second['primitives'][1]['x'] = .7
    plan = {'case_id': 'test', 'scenes': [first, second]}
    raw = {'entities': [
        {'id': 'donor', 'shape_source': {'scene': 0, 'primitive': 0}, 'label_source': None},
        {'id': 'receiver', 'shape_source': {'scene': 0, 'primitive': 1}, 'label_source': None},
        {'id': 'particle', 'shape_source': {'scene': 0, 'primitive': 2}, 'label_source': {'scene': 0, 'primitive': 3}}],
        'routes': [{'id': 'transfer', 'waypoints': [{'entity': 'donor', 'anchor': 'top'},
                    {'entity': 'receiver', 'anchor': 'top'}], 'closed': False,
                    'markers': [{'entity': 'particle', 'edge': 0}],
                    'witnesses': [{'scene': 0, 'quote': first['narration']}]}],
        'scenes': [{'index': i, 'bindings': {'donor': 0, 'receiver': 1},
                    'remove_indices': [2, 3], 'routes': ['transfer']} for i in range(2)]}
    return plan, raw, {'id': 'test', 'prompt_text': first['narration']}


def test_source_anchored_route_preserves_context_and_updates_per_scene_bounds():
    plan, raw, case = fixture(); old = copy.deepcopy(plan)
    out, receipt = compile_program(raw, plan, case, [0, 1])
    assert plan == old and receipt['semantic_acceptance'] == 'unverified'
    for i, scene in enumerate(out['scenes']):
        assert scene['primitives'][:2] == old['scenes'][i]['primitives'][:2]
        assert {k:v for k,v in scene.items() if k != 'primitives'} == {
            k:v for k,v in old['scenes'][i].items() if k != 'primitives'}
        arrow = next(p for p in scene['primitives'] if p['type'] == 'arrow')
        carrier = next(p for p in scene['primitives'] if 'dx' in p)
        assert arrow['x'] == carrier['x'] == old['scenes'][i]['primitives'][0]['x']
        assert carrier['x'] + carrier['dx'] == pytest.approx(arrow['x2'])
        assert arrow['x2'] == old['scenes'][i]['primitives'][1]['x']
        assert carrier['fill'] == '#9b4422'
        assert not render_frame(scene, .5)[1]
    assert receipt['scenes'][0]['routes'][0]['points_px'] != receipt['scenes'][1]['routes'][0]['points_px']


@pytest.mark.parametrize('mutation,pattern', [
    ('delete_owner', 'anchor owners'), ('wrong_quote', 'exact span'),
    ('unknown_anchor', 'waypoint'), ('duplicate_marker', 'once per route'),
    ('missing_scene', 'every selected scene'), ('duplicate_entity', 'distinct short entity'),
    ('retained_marker', 'duplicated'), ('invalid_closed', 'closed flag'),
    ('protected', 'protected source'), ('moving_owner', 'static')])
def test_bad_bindings_and_deleting_context_are_rejected(mutation, pattern):
    plan, raw, case = fixture()
    if mutation == 'delete_owner': raw['scenes'][0]['remove_indices'].append(0)
    if mutation == 'wrong_quote': raw['routes'][0]['witnesses'][0]['quote'] = 'Not in source'
    if mutation == 'unknown_anchor': raw['routes'][0]['waypoints'][0]['anchor'] = 'random'
    if mutation == 'duplicate_marker': raw['routes'][0]['markers'] *= 2
    if mutation == 'missing_scene': raw['scenes'].pop()
    if mutation == 'duplicate_entity': raw['entities'].append(copy.deepcopy(raw['entities'][0]))
    if mutation == 'retained_marker': raw['scenes'][0]['remove_indices'] = [3]
    if mutation == 'invalid_closed': raw['routes'][0]['closed'] = True
    if mutation == 'protected': plan['scenes'][0]['state_visual'] = {}
    if mutation == 'moving_owner': plan['scenes'][0]['primitives'][0]['dx'] = .1
    with pytest.raises(ValueError, match=pattern):
        compile_program(raw, plan, case, [0, 1])


def test_circle_anchors_use_isotropic_pixel_radius():
    b = bounds({'type': 'circle', 'x': .5, 'y': .5, 'r': .1})
    assert b[2]-b[0] == pytest.approx(b[3]-b[1])


def test_symbolic_closed_route_has_matching_executed_endpoint():
    plan, raw, case = fixture()
    r = raw['routes'][0]
    r['closed'] = True
    r['waypoints'] += [{'entity': 'receiver', 'anchor': 'bottom'},
                      {'entity': 'donor', 'anchor': 'bottom'}, copy.deepcopy(r['waypoints'][0])]
    out, receipt = compile_program(raw, plan, case, [0, 1])
    for record in receipt['scenes']:
        points = record['routes'][0]['points_px']
        assert points[0] == points[-1]
        assert len(points) == 5


def test_refusal_leaves_no_plan_and_wrong_semantic_roles_are_not_certified():
    plan, raw, case = fixture()
    out, receipt = compile_program({'unsupported': 'No matching path.'}, plan, case, [0, 1])
    assert out is None and receipt['status'] == 'not_applicable'
    raw['routes'][0]['waypoints'].reverse()
    _, receipt = compile_program(raw, plan, case, [0, 1])
    assert receipt['semantic_acceptance'] == 'unverified'


def test_opt_in_replacement_derives_carrier_deletions_and_retains_owners():
    plan, raw, case = fixture()
    for row in raw['scenes']:
        row['bindings']['particle'] = 2
        row['remove_indices'] = [3]
    out, receipt = compile_program(raw, plan, case, [0, 1], auto_replace=True)
    for i in range(2):
        assert out['scenes'][i]['primitives'][:2] == plan['scenes'][i]['primitives'][:2]
        assert len([p for p in out['scenes'][i]['primitives'] if p['type'] == 'circle']) == 3
        assert receipt['scenes'][i]['removed_indices'] == [2, 3]
    assert receipt['version'] == 'shared-object-auto-replacement-v2'
    with pytest.raises(ValueError, match='bind exactly'):
        compile_program(raw, plan, case, [0, 1])


def test_optional_absent_carrier_does_not_delete_an_unrelated_object():
    plan, raw, case = fixture()
    plan['scenes'][1]['primitives'] = plan['scenes'][1]['primitives'][:2]
    raw['scenes'][1].update(bindings={'donor': 0, 'receiver': 1, 'particle': -1}, remove_indices=[])
    out, receipt = compile_program(raw, plan, case, [0, 1], auto_replace=True)
    assert out['scenes'][1]['primitives'][:2] == plan['scenes'][1]['primitives']
    assert receipt['scenes'][1]['removed_indices'] == []


def test_auto_replacement_cannot_delete_an_anchor_owner():
    plan, raw, case = fixture()
    raw['scenes'][0]['bindings']['particle'] = 0
    with pytest.raises(ValueError, match='anchor owners'):
        compile_program(raw, plan, case, [0, 1], auto_replace=True)


def test_edit_scope_retains_untouched_errors_and_blocks_target_errors():
    plan, raw, case = fixture()
    plan['scenes'][1]['primitives'].append(copy.deepcopy(plan['scenes'][1]['primitives'][3]))
    raw['scenes'] = raw['scenes'][:1]
    out, _ = compile_program(raw, plan, case, [0])
    scoped = inspect_edit_layout(plan, out, [0])
    assert scoped['inherited_untouched_errors']
    assert not scoped['blocking_target_errors']
    out['scenes'][0]['primitives'].append(copy.deepcopy(out['scenes'][0]['primitives'][-1]))
    assert inspect_edit_layout(plan, out, [0])['blocking_target_errors']


def test_new_label_does_not_straddle_owner_border_or_move_clear_labels():
    box = [380, 170, 646, 354]
    assert label_position(625, 251, 'Cool', 'left', (0, 120), [box]) == (658, 251)
    assert label_position(485, 251, 'Warm', 'right', (0, -120), [box]) == (485, 251)


@pytest.mark.parametrize('indexed', [False, True])
@pytest.mark.parametrize('guard', [False, True])
def test_proposal_exposes_opt_in_compiler_rules_without_conflicting_instructions(tmp_path, indexed, guard):
    plan, raw, case = fixture()
    plan['scenes'] += copy.deepcopy(plan['scenes'])
    case['target_duration_s'] = 40
    for row in raw['scenes']:
        row['bindings']['particle'] = 2
        row['remove_indices'] = [3]
    original = copy.deepcopy(plan)

    class Client:
        def chat(self, messages, **kwargs):
            self.messages = copy.deepcopy(messages)
            return copy.deepcopy(raw)

    client = Client()
    result, receipt = propose(client, plan, case, [0, 1], tmp_path,
                              indexed=indexed, auto_replace=True, avoid_owner_borders=guard)
    assert plan == original
    assert receipt['compiler_options'] == {'auto_replace': True, 'avoid_owner_borders': guard}
    assert receipt['version'] == ('shared-object-owner-border-labels-v3' if guard
                                  else 'shared-object-auto-replacement-v2')
    assert receipt['proposal_protocol'] == 'shared-object-configured-proposal-v3'
    prompt = client.messages[0]['content']
    assert 'Automatic carrier replacement is enabled' in prompt
    assert 'bindings contains ONLY' not in prompt and 'never invent an index or use -1' not in prompt
    assert ('Code measures newly generated labels' in prompt) == guard
    assert json.loads((tmp_path/'input.json').read_text())['compiler_options'] == receipt['compiler_options']
    for index in (0, 1):
        assert receipt['scenes'][index]['removed_indices'] == [2, 3]
        assert len([p for p in result['scenes'][index]['primitives'] if p['type'] == 'circle']) == 3
    assert result['scenes'][2:] == original['scenes'][2:]


def test_proposal_default_still_rejects_optional_carrier_binding_and_records_attempts(tmp_path):
    plan, raw, case = fixture()
    raw['scenes'][0]['bindings']['particle'] = 2
    responses = iter([raw, {'unsupported': 'Cannot identify a faithful route.'}])

    class Client:
        def chat(self, messages, **kwargs):
            self.messages = copy.deepcopy(messages)
            return next(responses)

    client = Client()
    result, receipt = propose(client, plan, case, [0, 1], tmp_path, indexed=True)
    assert result is None and receipt['status'] == 'not_applicable'
    assert 'bind exactly' in json.loads((tmp_path/'error_0.json').read_text())['error']
    assert json.loads((tmp_path/'raw_0.json').read_text()) == raw
    assert 'compiler_options' not in json.loads((tmp_path/'input.json').read_text())
    assert 'bindings contains ONLY' in client.messages[0]['content']
    assert 'Automatic carrier replacement is enabled' not in client.messages[0]['content']
