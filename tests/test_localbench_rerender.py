import copy
import pytest
from localbench.rerender import diagram_only_plan


def fixture():
    return {'case_id':'x','scenes':[{'title':'A','caption':'B','narration':'Teach this concept.',
       'duration_s':10.25,'primitives':[{'type':'line','x':0,'y':0,'x2':1,'y2':1}]}]}


def test_diagram_comparison_keeps_exact_timing_and_all_nonvisual_fields():
    original=fixture();proposed=copy.deepcopy(original)
    proposed['scenes'][0]['primitives'][0]['y2']=0
    out,changed=diagram_only_plan(original,proposed)
    assert changed==[0]
    assert out['scenes'][0]['duration_s']==10.25
    assert original['scenes'][0]['primitives'][0]['y2']==1
    for key,value in [('narration','A different explanation'),('duration_s',10.5),('caption','Changed')]:
        bad=copy.deepcopy(proposed);bad['scenes'][0][key]=value
        with pytest.raises(ValueError,match='cannot change'):diagram_only_plan(original,bad)
