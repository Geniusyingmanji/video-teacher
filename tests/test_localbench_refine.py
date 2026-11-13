import copy

import pytest

from localbench.refine import apply_diagrams
from localbench.rerender import diagram_only_plan
from localbench.scene import render_frame,validate_plan


def fixture():
    return {'case_id':'x','timing_compilation':{'version':'measured'},'scenes':[
        {'title':'Flow','narration':'Air moves around this center.', 'caption':'Inward flow.',
         'slide_text':'Keep this baseline unchanged.', 'duration_s':15,
         'primitives':[{'type':'text','x':.5,'y':.5,'text':'Spiral'}]}]}


def replacement():
    return {'replacements':[{'scene':0,'primitives':[
        {'type':'flow_path','x':.5,'y':.5,'radius_start':.4,'radius_end':.09}]}]}


def test_diagram_refinement_preserves_full_nonvisual_contract_and_original():
    before=fixture();snapshot=copy.deepcopy(before);proposal=replacement()
    after=apply_diagrams(before,proposal)
    result,changed=diagram_only_plan(before,after)
    assert result==after and changed==[0] and before==snapshot
    assert after['timing_compilation']==before['timing_compilation']
    proposal['replacements'][0]['primitives'][0]['x']=0
    assert after['scenes'][0]['primitives'][0]['x']==.5


def test_diagram_refinement_rejects_hidden_narration_changes_and_backend_overrides():
    for extra in ({'narration':'Changed'},{'duration_s':1}):
        proposal=replacement();proposal['replacements'][0].update(extra)
        with pytest.raises(ValueError):apply_diagrams(fixture(),proposal)
    for field in ('source_visual','state_visual'):
        plan=fixture();plan['scenes'][0][field]={'kind':'trusted'}
        with pytest.raises(ValueError,match='backends'):apply_diagrams(plan,replacement())
    proposal=replacement();proposal['replacements']*=2
    with pytest.raises(ValueError):apply_diagrams(fixture(),proposal)


def test_right_aligned_text_uses_its_right_edge_and_invalid_alignment_is_rejected():
    scene=fixture()['scenes'][0]
    # Right-edge anchor near the panel edge must keep the whole label inside it.
    scene['primitives']=[{'type':'text','x':.98,'y':.4,'text':'Right aligned label','align':'right'}]
    _,issues=render_frame(scene,0)
    assert not issues
    scene['primitives'][0]['align']='left'
    _,issues=render_frame(scene,0)
    assert any(x['kind']=='text_outside_panel' for x in issues)
    scene['primitives'][0]['align']='unknown'
    with pytest.raises(ValueError,match='text align'):
        validate_plan({'case_id':'x','scenes':[scene]*4},{'id':'x','target_duration_s':60})
