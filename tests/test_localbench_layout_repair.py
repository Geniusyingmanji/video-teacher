import copy

import pytest

from localbench.layout_repair import apply_layout_edits,feedback


def plan():
    return {'case_id':'a','scenes':[{'narration':'Frozen teaching content','duration_s':10,
        'primitives':[{'type':'rect','x':.85,'y':.4,'w':.2,'h':.3},
                      {'type':'text','x':.95,'y':.55,'text':'HR','align':'center'}]}]}


def test_coordinate_repair_preserves_text_and_original_plan():
    old=plan();snapshot=copy.deepcopy(old)
    patch={'edits':[{'scene':0,'primitive':0,'set':{'x':.7}},
                    {'scene':0,'primitive':1,'set':{'x':.8}}]}
    fixed=apply_layout_edits(old,patch)
    assert old==snapshot and fixed['scenes'][0]['narration']==snapshot['scenes'][0]['narration']
    assert fixed['scenes'][0]['primitives'][1]['text']=='HR'
    assert fixed['scenes'][0]['primitives'][0]['x']+.2==pytest.approx(.9)


def test_geometry_patch_cannot_rewrite_or_hide_content():
    for values in ({'text':'Different answer'},{'appear':.9},{'type':'circle'},{'font_size':8}):
        with pytest.raises(ValueError):apply_layout_edits(plan(),{'edits':[{'scene':0,'primitive':1,'set':values}]})
    edit={'scene':0,'primitive':1,'set':{'x':.8}}
    with pytest.raises(ValueError,match='repeated'):apply_layout_edits(plan(),{'edits':[edit,edit]})
    original=plan();original['scenes'][0]['source_visual']={'path':'source.png'}
    with pytest.raises(ValueError,match='cannot be patched'):apply_layout_edits(original,{'edits':[edit]})


def test_layout_feedback_expresses_pixel_overflow_in_authored_coordinates():
    row={'bbox':[825.6,232.8,1004.8,323.4]}
    assert feedback([row])[0]['normalized_bbox']==[.85,.4,1.05,.7]
    assert 'normalized_bbox' not in row
