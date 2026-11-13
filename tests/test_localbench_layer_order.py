import copy
import json
import pytest

from localbench.layer_order import compile_order, inspect_plan, inspect_scene


def scene():
    return {'title':'Runoff', 'caption':'A river leads to the sea.',
        'narration':'Follow the river as it reaches the sea.', 'duration_s':10,
        'primitives':[
            {'type':'arrow','x':.2,'y':.65,'x2':.8,'y2':.65,'color':'#1868ae'},
            {'type':'rect','x':.1,'y':.5,'w':.8,'h':.3,'fill':'#ba9c77','color':'#775533'},
            {'type':'text','x':.5,'y':.3,'text':'River','align':'center'}]}


def setup():
    plan = {'case_id':'river', 'scenes':[scene()]}
    case = {'id':'river','prompt_text':'Show a river flowing to the sea.'}
    raw = {'orders':[{'scene':0,'background':1,'foreground':[0],
        'reason':'The land obscures the requested river direction.', 'witness':case['prompt_text']}]}
    return plan, case, raw


def test_fully_hidden_stroke_is_detected_with_specific_occluder():
    findings = inspect_scene(scene())
    assert len(findings) == 1
    row = findings[0]
    assert row['primitive'] == 0 and row['visible_support_pixels'] == 0
    assert row['hidden_fraction'] == 1 and row['authored_support_pixels'] > 100
    assert row['occluders'] == [{'primitive':1, 'revealed_support_pixels':row['authored_support_pixels']}]


def test_layer_dependency_reveals_actual_stroke_without_rewriting_primitives():
    plan, case, raw = setup(); original = copy.deepcopy(plan)
    result, receipt = compile_order(raw, plan, case, [0])
    assert plan == original
    assert receipt['semantic_acceptance'] == 'unverified'
    assert receipt['permutations'][0]['original_indices_in_new_order'] == [1,0,2]
    before, after = original['scenes'][0], result['scenes'][0]
    assert {k:v for k,v in before.items() if k!='primitives'} == {k:v for k,v in after.items() if k!='primitives'}
    assert after['primitives'] == [before['primitives'][i] for i in (1,0,2)]
    assert inspect_scene(after) == []


def test_decision_to_keep_intentional_occlusion_is_preserved():
    plan, case, _ = setup()
    result, receipt = compile_order({'orders':[]}, plan, case, [0])
    assert result == plan and receipt['status'] == 'unchanged'
    assert receipt['inventory']


@pytest.mark.parametrize('change,error', [('not_occluder','detected'), ('invented_witness','exact'),
    ('outside','outside'), ('new_fields','requires'), ('duplicate','distinct')])
def test_invalid_or_unrelated_layer_requests_rejected(change,error):
    plan, case, raw = setup(); order = raw['orders'][0]
    if change == 'not_occluder': order['background'] = 2
    if change == 'invented_witness': order['witness'] = 'This is not the public task.'
    if change == 'outside': order['scene'] = 1
    if change == 'new_fields': order['new_text'] = 'A different river'
    if change == 'duplicate': order['foreground'] = [0,0]
    with pytest.raises(ValueError, match=error): compile_order(raw, plan, case, [0])


def test_moving_and_protected_scenes_are_not_automatically_reordered():
    plan, case, raw = setup()
    plan['scenes'][0]['primitives'][0]['dx'] = .1
    assert inspect_plan(plan,[0]) == []
    with pytest.raises(ValueError, match='detected'): compile_order(raw,plan,case,[0])
    plan['scenes'][0]['primitives'][0].pop('dx')
    plan['scenes'][0]['state_visual'] = {}
    assert inspect_plan(plan,[0]) == []


def test_visible_stroke_and_small_intentional_intersection_do_not_trigger():
    s = scene(); s['primitives'][1]['y'] = .8
    assert inspect_scene(s) == []
    s['primitives'][1].update(x=.45,y=.5,w=.1)
    assert inspect_scene(s) == []


def test_opt_in_method_keeps_layer_repair_if_later_critic_fails(monkeypatch, tmp_path):
    import localbench.pipeline as pipeline
    import localbench.rerender as rerender
    import localbench.visual_agent as agent
    import localbench.label_repair as labels
    import localbench.stroke_visibility as strokes
    from localbench.run import improve
    from localbench.scene import validate_plan
    plan, case, raw = setup()
    plan['scenes'] = [copy.deepcopy(plan['scenes'][0]) for _ in range(4)]
    case['target_duration_s'] = 40
    validate_plan(plan, case)
    original = tmp_path/'original'; original.mkdir()
    (original/'plan.json').write_text(json.dumps(plan))
    before = {'mode':'code','video_path':str(original/'code.mp4'),'sha256':'before'}
    after = {'mode':'code','video_path':str(tmp_path/'new/code.mp4'),'sha256':'after'}
    for module in (labels, strokes):
        monkeypatch.setattr(module,'repair',lambda p:(copy.deepcopy(p),{'status':'unchanged'}))
    monkeypatch.setattr(pipeline,'encode',lambda *args,**kwargs:after)
    monkeypatch.setattr(rerender,'decoded_audio_hash',lambda *args:'same')
    monkeypatch.setattr(agent,'evidence',lambda *args,**kwargs:[])
    def fail(*args,**kwargs): raise ValueError('critic failed')
    monkeypatch.setattr(agent,'review',fail)
    class Client:
        calls = 0
        def chat(self, messages, **kwargs):
            self.calls += 1
            return {'orders':[{**raw['orders'][0],'scene':i} for i in range(4)]}
    client = Client()
    result = improve(case,{'artifacts':[before]},tmp_path/'repair',client,layer_order=True)
    assert client.calls == 1
    assert result['artifacts'] == [after] and result['original_artifacts'] == [before]
    assert result['layer_order_repair']['decoded_audio_identical']
    assert result['visual_repair']['retained_stage'].startswith('rendered_layer_order_repair')
    assert json.loads((original/'plan.json').read_text()) == plan
    compiled = json.loads((tmp_path/'repair/layer_order_repair/plan.json').read_text())
    assert inspect_plan(compiled,[0,1,2,3]) == []


def test_method_layer_flag_requires_a_boolean_before_services_or_calls(tmp_path):
    from types import SimpleNamespace
    from localbench.run import execute
    cfg = tmp_path/'services.json'
    cfg.write_text(json.dumps({'method_layer_order':'true'}))
    with pytest.raises(ValueError,match='method_layer_order must be a boolean'):
        execute(SimpleNamespace(command='method',config=cfg))
