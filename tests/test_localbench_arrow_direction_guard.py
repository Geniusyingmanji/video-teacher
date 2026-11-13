import copy

import pytest

from localbench.arrow_direction_guard import bind, check, relation_measure, propose


def source():
    return {'scenes': [{'primitives': [
        {'type': 'arrow', 'x': .2, 'y': .45, 'x2': .35, 'y2': .45, 'color': 'red'},
        {'type': 'arrow', 'x': .8, 'y': .65, 'x2': .65, 'y2': .65, 'color': 'red'},
        {'type': 'text', 'text': 'Second object'}]}]}


def contract(plan):
    return bind({'constraints': [{'scene': 0, 'arrows': [0, 1], 'relation': 'toward_each_other',
        'prompt_quote': 'move toward each other', 'reason': 'Arrows denote the two requested object motions.'}]},
        plan, {'id': 'fixture', 'prompt_text': 'Show two objects that move toward each other.'})


def reverse(p):
    p['x'], p['x2'] = p['x2'], p['x']
    p['y'], p['y2'] = p['y2'], p['y']


def test_wrong_right_arrow_reversal_is_blocked_with_original_retained():
    before = source(); after = copy.deepcopy(before)
    reverse(after['scenes'][0]['primitives'][1])
    receipt = check(contract(before), before, after)
    assert receipt['status'] == 'reject_reversal'
    assert receipt['records'][0]['source_measure']['satisfied']
    assert not receipt['records'][0]['candidate_measure']['satisfied']
    assert before == source()


def test_correct_direction_does_not_trigger_and_unrelated_scene_edit_is_allowed():
    before = source(); before['scenes'].append({'primitives': [{'type': 'text', 'text': 'Summary'}]})
    after = copy.deepcopy(before); after['scenes'][1]['primitives'][0]['text'] = 'New summary'
    receipt = check(contract(before), before, after)
    assert receipt['records'][0]['status'] == 'preserved'


@pytest.mark.parametrize('change', ['label', 'arrow_position', 'arrow_style'])
def test_changed_binding_is_unassessed_not_certified(change):
    before = source(); after = copy.deepcopy(before)
    row = after['scenes'][0]['primitives']
    if change == 'label':
        row[2]['text'] = 'Different object'
    elif change == 'arrow_position':
        row[1]['y'] = .3
    else:
        row[1]['color'] = 'green'
    receipt = check(contract(before), before, after)
    assert 'unassessed' in receipt['records'][0]['status']


def test_incorrect_source_is_not_mistaken_for_a_valid_reference():
    before = source(); reverse(before['scenes'][0]['primitives'][1])
    receipt = check(contract(before), before, before)
    assert receipt['records'][0]['status'] == 'source_relation_unsatisfied'


def test_diagonal_and_role_order_are_supported_without_assuming_left_to_right():
    a, b = source()['scenes'][0]['primitives'][:2]
    # Rotate all positions90degrees: the relation is invariant to this rotation.
    for p in (a, b):
        p['x'], p['y'] = 1-p['y'], p['x']
        p['x2'], p['y2'] = 1-p['y2'], p['x2']
    assert relation_measure(a, b, 'toward_each_other')['satisfied']
    assert relation_measure(b, a, 'toward_each_other')['satisfied']
    reverse(a); reverse(b)
    assert relation_measure(a, b, 'away_from_each_other')['satisfied']
    assert relation_measure(a, b, 'opposite_parallel')['satisfied']


def test_zero_length_and_moving_arrow_geometries_are_rejected():
    a, b = source()['scenes'][0]['primitives'][:2]
    a['x2'] = a['x']
    with pytest.raises(ValueError, match='zero-length'):
        relation_measure(a, b, 'toward_each_other')
    a['dx'] = .1
    with pytest.raises(ValueError, match='stationary'):
        relation_measure(a, b, 'toward_each_other')


def test_stale_source_and_non_task_witness_cannot_bind():
    before = source(); c = contract(before)
    before['scenes'][0]['primitives'][2]['text'] = 'Changed'
    with pytest.raises(ValueError, match='stale'):
        check(c, before, before)
    with pytest.raises(ValueError, match='public-task'):
        bind({'constraints': [{k: v for k, v in c['constraints'][0].items() if k != 'source_measure'}]},
             before, {'id': 'other', 'prompt_text': 'A different task'})


def test_no_eligible_pair_skips_model_without_fabricating_relation(tmp_path):
    class NoClient:
        def chat(self, *args, **kwargs):
            raise AssertionError('Do not call a model when no paired arrows exist')
    plan = {'scenes': [{'title': 'One arrow', 'narration': 'Direction', 'primitives': [
        {'type': 'arrow', 'x': .1, 'y': .2, 'x2': .8, 'y2': .2},
        {'type': 'line', 'x': .8, 'y': .2, 'x2': .9, 'y2': .2}]}]}
    result = propose(NoClient(), plan, {'id': 'x', 'prompt_text': 'Show one arrow and a bond.'}, [], tmp_path)
    assert result['constraints'] == []
    assert result['binding_status'] == 'no_eligible_arrow_pairs'


def test_patch_reversal_is_retained_without_render_or_retry(monkeypatch, tmp_path):
    import json
    from localbench import visual_agent
    before = source(); before['case_id'] = 'fixture'
    after = copy.deepcopy(before); reverse(after['scenes'][0]['primitives'][1])
    class Client:
        calls = 0
        def chat(self, *args, **kwargs):
            self.calls += 1
            assert self.calls == 1
            return json.dumps({'replacements': [{'scene': 0, 'primitives': after['scenes'][0]['primitives']}]})
    monkeypatch.setattr(visual_agent, 'validate_plan', lambda *args: None)
    client = Client()
    result, errors = visual_agent.patch(client, {'id': 'fixture'}, before, {'issues': []},
        {'rules': []}, [], tmp_path, 'test', direction_contract=contract(before))
    assert result == before and errors == [] and client.calls == 1
    assert json.loads((tmp_path/'direction_rejected_plan_0.json').read_text()) == after
    rejection = json.loads((tmp_path/'direction_rejection.json').read_text())
    assert rejection['receipt']['status'] == 'reject_reversal'
    assert rejection['quality_acceptance'] is False


def test_method_binds_source_before_critic_and_forwards_contract(monkeypatch, tmp_path):
    import json
    import localbench.arrow_direction_guard as guard
    import localbench.visual_agent as agent
    import localbench.label_repair as labels
    import localbench.stroke_visibility as strokes
    from localbench.run import improve
    plan = source(); plan['case_id'] = 'fixture'
    original = tmp_path/'original'; original.mkdir()
    (original/'plan.json').write_text(json.dumps(plan))
    artifact = {'mode': 'code', 'video_path': str(original/'code.mp4'), 'sha256': 'fixture'}
    events = []
    for module in (labels, strokes):
        monkeypatch.setattr(module, 'repair', lambda p: (copy.deepcopy(p), {'status': 'unchanged'}))
    monkeypatch.setattr(agent, 'evidence', lambda *args, **kwargs: [])
    def propose(*args):
        events.append('bind'); return contract(plan)
    def review(*args):
        events.append('critic'); return {'issues': [{'visual_edit_sufficient': True}]}
    def run_variant(*args, **kwargs):
        events.append('patch')
        assert kwargs['direction_contract']['source_plan_hash'] == contract(plan)['source_plan_hash']
        return {'artifact': artifact, 'status': 'no_change'}
    monkeypatch.setattr(guard, 'propose', propose)
    monkeypatch.setattr(agent, 'review', review)
    monkeypatch.setattr(agent, 'run_variant', run_variant)
    result = improve({'id': 'fixture', 'prompt_text': 'Two objects move toward each other.'},
                     {'artifacts': [artifact]}, tmp_path/'repair', None, direction_guard=True)
    assert events == ['bind', 'critic', 'patch']
    assert result['artifacts'] == [artifact] and result['direction_binding']['constraints']


def test_method_direction_flag_validated_before_service_calls(tmp_path):
    import json
    from types import SimpleNamespace
    from localbench.run import execute
    config = tmp_path/'services.json'
    config.write_text(json.dumps({'method_direction_guard': 'true'}))
    with pytest.raises(ValueError, match='method_direction_guard must be a boolean'):
        execute(SimpleNamespace(command='method', config=config))
