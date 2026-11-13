import copy
import json
import pytest

from localbench.connection_instances import inventory,compile_decisions,propose
from localbench.object_connections import compile_connections


def setup():
    ps=[{'type':'line','x':.1,'y':.3,'x2':.3,'y2':.3},
        {'type':'circle','x':.7,'y':.5,'r':.1},
        {'type':'line','x':.3,'y':.3,'x2':.5,'y2':.4}]
    scene={'title':'Link A and B','caption':'Same two objects','narration':'Connect A to B.','duration_s':10,'primitives':ps}
    plan={'case_id':'x','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    # Index order is deliberately different in one repeated scene.
    plan['scenes'][2]['primitives']=list(reversed(ps))
    case={'id':'x','prompt_text':'Connect A to B.'}
    seed={'scene':0,'connector':2,'source_shape':0,'target_shape':1,'label':None,
          'prompt_quote':'Connect A to B.','reason':'Publicly requested link'}
    return plan,case,[seed]


def test_repeated_geometry_inventory_matches_objects_not_primitive_indices():
    plan,case,seeds=setup();groups=inventory(plan,case,seeds)
    assert len(groups)==1 and [x['scene'] for x in groups[0]['instances']]==[0,1,2,3]
    assert groups[0]['instances'][2]['connector']==0
    assert groups[0]['instances'][2]['source_shape']==2
    plan['scenes'][3]['primitives'].append(copy.deepcopy(plan['scenes'][3]['primitives'][0]))
    assert [x['scene'] for x in inventory(plan,case,seeds)[0]['instances']]==[0,1,2]


def test_coverage_is_explicit_and_disconnected_counterexample_can_be_excluded():
    plan,case,seeds=setup();groups=inventory(plan,case,seeds)
    raw={'groups':[{'id':'G0','include':[0,1,2],'exclude':[{'scene':3,'reason':'Intentional disconnected comparison'}],'reason':'Same requested attached relation'}]}
    candidate,receipt=compile_decisions(raw,groups,plan,case)
    assert [x['scene'] for x in receipt['connections']]==[0,1,2]
    assert all(max(x['on_support_error_px'])<1e-6 for x in receipt['connections'])
    assert candidate['scenes'][3]==plan['scenes'][3]
    raw['groups'][0]['exclude']=[]
    with pytest.raises(ValueError,match='every supplied occurrence'):compile_decisions(raw,groups,plan,case)
    raw['groups'][0]['include']=[0,1,2,3,3]
    with pytest.raises(ValueError,match='exactly once'):compile_decisions(raw,groups,plan,case)


def test_all_occurrences_may_be_rejected_without_inventing_changes():
    plan,case,seeds=setup();groups=inventory(plan,case,seeds)
    raw={'groups':[{'id':'G0','include':[],'exclude':[{'scene':i,'reason':'Relation remains ambiguous'} for i in range(4)],'reason':'No supported attachment'}]}
    candidate,receipt=compile_decisions(raw,groups,plan,case)
    assert candidate==plan and receipt['status']=='no_change'


def test_repeated_proposal_sends_public_context_but_no_private_reference(tmp_path):
    plan,case,seeds=setup();_,receipt=compile_connections({'connections':seeds},plan,case)
    case['expected_concepts']=['SECRET_REF']
    class Client:
        def chat(self,msg,**kw):
            assert 'SECRET_REF' not in json.dumps(msg)
            return {'groups':[{'id':'G0','include':[0,1,2,3],'exclude':[],'reason':'Repeated attached relation, including recap'}]}
    candidate,compiled=propose(Client(),plan,case,receipt,[],tmp_path)
    assert len(compiled['connections'])==4
    assert candidate!=plan
