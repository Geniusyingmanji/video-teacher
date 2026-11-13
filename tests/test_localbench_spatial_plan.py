import copy
import json
from types import SimpleNamespace

import pytest

from localbench.spatial_plan import compile_plan
from test_localbench_spatial_graph import TASK
from test_localbench_spatial_solver import symbolic


def lesson():
    scene = {'title': 'Spatial approach', 'caption': 'Read the approach direction.',
             'slide_text': 'The approach is opposite the leaving group.', 'duration_s': 10,
             'narration': 'The nucleophile approaches from the opposite side of the leaving group.',
             'primitives': [{'type': 'text', 'x': .2, 'y': .3, 'text': 'Approach'}]}
    plan = {'case_id': 'spatial', 'scenes': [copy.deepcopy(scene) for _ in range(4)]}
    plan['scenes'][1]['primitives'] = [{'type': 'symbolic_spatial_graph', 'spec': symbolic()}]
    return plan


def case():
    return {'id': 'spatial', 'prompt_text': TASK, 'target_duration_s': 40,
            'pedagogical_target_audience': 'graduate chemistry'}


def test_plan_compiles_only_selected_scene_without_mutating_model_input():
    p = lesson();before = copy.deepcopy(p)
    result, receipt = compile_plan(p, case())
    assert p == before
    assert receipt['status'] == 'compiled' and len(receipt['constructions']) == 1
    assert result['scenes'][1]['primitives'][0]['type'] == 'spatial_graph'
    for i in [0, 2, 3]:
        assert result['scenes'][i] == p['scenes'][i]
    from localbench.scene import validate_plan, inspect_layout
    validate_plan(result, case())
    assert not inspect_layout(result)


def test_plan_rejects_overlay_and_protected_source():
    p = lesson();p['scenes'][1]['primitives'].append({'type': 'text'})
    with pytest.raises(ValueError, match='owns its panel'):
        compile_plan(p, case())
    p = lesson();p['scenes'][1]['source_visual'] = {'path': 'protected'}
    with pytest.raises(ValueError, match='protected state/source'):
        compile_plan(p, case())


def test_ordinary_plan_is_explicit_no_selection():
    p = lesson();p['scenes'][1] = copy.deepcopy(p['scenes'][0])
    result, receipt = compile_plan(p, case())
    assert p == result and receipt['status'] == 'not_selected'


def test_generation_path_keeps_raw_and_compiled_graph_receipts(tmp_path, monkeypatch):
    import localbench.pipeline as pipeline
    class Client:
        def chat(self, messages, **kwargs):
            assert 'symbolic_spatial_graph' in messages[0]['content']
            return lesson()
    monkeypatch.setattr(pipeline, 'synthesize', lambda *a, **k: ('unused.wav', []))
    monkeypatch.setattr(pipeline, 'encode', lambda *a, **k: {'complete': True, 'mode': 'code'})
    result = pipeline.generate_one(case(), tmp_path, Client(), ['code'], spatial_graphs=True)
    assert result['status'] == 'rendered'
    raw = json.loads((tmp_path/'spatial/plan_raw_0.json').read_text())
    compiled = json.loads((tmp_path/'spatial/plan.json').read_text())
    assert raw['scenes'][1]['primitives'][0]['type'] == 'symbolic_spatial_graph'
    assert compiled['scenes'][1]['primitives'][0]['type'] == 'spatial_graph'
    assert (tmp_path/'spatial/spatial_constructions_0.json').exists()


def test_method_flag_validated_before_any_service_call(tmp_path):
    from localbench.run import execute
    config = tmp_path/'config.json';config.write_text(json.dumps({'method_spatial_graphs': 'true'}))
    with pytest.raises(ValueError, match='method_spatial_graphs must be a boolean'):
        execute(SimpleNamespace(command='method', config=config))


def test_ordinary_repair_cannot_erase_checked_spatial_graph(tmp_path):
    from localbench.run import improve
    plan, _ = compile_plan(lesson(), case())
    (tmp_path/'plan.json').write_text(json.dumps(plan))
    artifact = {'mode': 'code', 'video_path': str(tmp_path/'video.mp4')}
    result = improve(case(), {'artifacts': [artifact]}, tmp_path/'repair', None)
    assert result['artifacts'] == [artifact]
    assert result['visual_repair']['status'] == 'protected_spatial_graph_backend'
