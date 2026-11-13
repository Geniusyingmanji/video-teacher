import copy
import json
from types import SimpleNamespace

import pytest

from localbench.spatial_contract import bind_plan, validate_proposal
from test_localbench_spatial_plan import case, lesson
from test_localbench_spatial_solver import symbolic


def proposal():
    return {'decision': 'use', 'reason': 'The task requests a tetrahedral arrangement.',
            'scope_quote': case()['prompt_text'], 'spec': symbolic()}


def reference_plan(contract):
    plan=lesson()
    plan['scenes'][1]['primitives']=[{'type':'spatial_contract_ref','contract_id':contract['contract_id']}]
    return plan


def test_generation_extracts_resource_before_planning_and_preserves_raw_refs(tmp_path,monkeypatch):
    import localbench.pipeline as pipeline
    contract=validate_proposal(proposal(),case());calls=[]
    class Client:
        def chat(self,messages,**kwargs):
            calls.append(kwargs['purpose'])
            if kwargs['purpose'].startswith('spatial_contract:'):
                return proposal()
            assert contract['contract_id'] in messages[0]['content']
            return reference_plan(contract)
    monkeypatch.setattr(pipeline,'synthesize',lambda *a,**k:('unused.wav',[]))
    monkeypatch.setattr(pipeline,'encode',lambda *a,**k:{'complete':True,'mode':'code'})
    result=pipeline.generate_one(case(),tmp_path,Client(),['code'],spatial_contracts=True)
    assert result['status']=='rendered' and result['spatial_contract']['status']=='compiled'
    assert calls==['spatial_contract:spatial:0','plan:spatial:0']
    raw=json.loads((tmp_path/'spatial/plan_raw_0.json').read_text())
    compiled=json.loads((tmp_path/'spatial/plan.json').read_text())
    assert raw['scenes'][1]['primitives'][0]['type']=='spatial_contract_ref'
    assert compiled['scenes'][1]['primitives'][0]['type']=='spatial_graph'
    assert json.loads((tmp_path/'spatial/spatial_contract_binding_0.json').read_text())['scenes']==[1]


def test_planner_cannot_silently_omit_a_compiled_resource(tmp_path,monkeypatch):
    import localbench.pipeline as pipeline
    plain=lesson();plain['scenes'][1]=copy.deepcopy(plain['scenes'][0]);calls=[]
    class Client:
        def chat(self,messages,**kwargs):
            calls.append(kwargs['purpose'])
            return proposal() if kwargs['purpose'].startswith('spatial_contract:') else copy.deepcopy(plain)
    monkeypatch.setattr(pipeline,'synthesize',lambda *a,**k:pytest.fail('invalid plan must not synthesize'))
    result=pipeline.generate_one(case(),tmp_path,Client(),['code'],spatial_contracts=True)
    assert result['status']=='planning_failed'
    assert len([c for c in calls if c.startswith('plan:')])==3
    assert all('must be referenced' in r['error'] for r in result['attempts'])


def test_unsupported_task_has_explicit_skip_and_ordinary_plan(tmp_path,monkeypatch):
    import localbench.pipeline as pipeline
    plain=lesson();plain['scenes'][1]=copy.deepcopy(plain['scenes'][0])
    class Client:
        def chat(self,messages,**kwargs):
            if kwargs['purpose'].startswith('spatial_contract:'):
                return {'decision':'skip','reason':'No supported geometry.','scope_quote':None,'spec':None}
            assert 'SPATIAL RESOURCE' not in messages[0]['content']
            return copy.deepcopy(plain)
    monkeypatch.setattr(pipeline,'synthesize',lambda *a,**k:('unused.wav',[]))
    monkeypatch.setattr(pipeline,'encode',lambda *a,**k:{'complete':True,'mode':'code'})
    result=pipeline.generate_one(case(),tmp_path,Client(),['code'],spatial_contracts=True)
    assert result['status']=='rendered' and result['spatial_contract']['status']=='skipped'


def test_spatial_modes_are_mutually_exclusive_and_boolean_before_calls(tmp_path):
    from localbench.run import execute
    for config,match in [({'method_spatial_contracts':'yes'},'must be a boolean'),
                         ({'method_spatial_contracts':True,'method_spatial_graphs':True},'not both')]:
        path=tmp_path/'config.json';path.write_text(json.dumps(config))
        with pytest.raises(ValueError,match=match):
            execute(SimpleNamespace(command='method',config=path))
