import copy

import numpy as np
import pytest

from localbench.scene import arithmetic, inspect_layout, render_frame, validate_plan


@pytest.mark.parametrize('kind',['line','polyline'])
def test_rigid_translation_moves_all_visible_geometry_without_stretching(kind):
    p={'type':kind,'x':.1,'y':.1,'x2':.3,'y2':.3,
       'points':[[.1,.1],[.3,.3],[.4,.1]],'dx':.125,'dy':.5,'color':'#00aa00'}
    scene={'title':'Movement','caption':'A translated shape.','primitives':[p]}
    a,_=render_frame(scene,0);b,_=render_frame(scene,1)
    def pixels(im):
        y,x=np.nonzero(np.all(np.asarray(im)==[0,170,0],axis=2))
        return set(zip(x,y))
    before,after=pixels(a),pixels(b)
    assert before and after=={(x+112,y+151) for x,y in before}


def test_full_plan_rejects_nonfinite_polyline_before_rendering():
    scene={'title':'Finite shape','caption':'One shape','narration':'This is a short spoken explanation.',
           'duration_s':15,'primitives':[{'type':'polyline','x':0,'y':0,'points':[[0,0],[float('nan'),1]]}]}
    with pytest.raises(ValueError,match='finite normalized'):
        validate_plan({'case_id':'x','scenes':[copy.deepcopy(scene) for _ in range(4)]},
                      {'id':'x','target_duration_s':60})


def test_geometry_and_static_baseline_truncation_are_reported():
    scene={'title':'One scene','caption':'Short caption','slide_text':'A long explanation '*90,
           'primitives':[{'type':'rect','x':.8,'y':.1,'w':.5,'h':.2}]}
    issues=inspect_layout({'scenes':[scene]})
    assert any(i['kind']=='geometry_outside_panel' and i['mode']=='code' for i in issues)
    assert any(i['kind']=='slide_text_truncated' and i['mode']=='slides' for i in issues)


def test_bond_discounting_fits_bounded_arithmetic_contract():
    assert arithmetic('50*((1-1.05**(-10))/.05)+1000/(1.05**10)')==pytest.approx(1000)
    with pytest.raises(ValueError,match='power too large'):arithmetic('2**1000')


def test_rounded_assertions_require_explicit_precision_and_correct_values():
    scene={'title':'Present value','caption':'Rounded to cents','narration':'Discount the final payment back to today.',
           'duration_s':15,'primitives':[{'type':'text','x':.1,'y':.1,'text':'PV'}],
           'arithmetic_checks':[{'expression':'1000/(1.05**10)','equals':613.91}]}
    plan={'case_id':'x','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    with pytest.raises(ValueError,match='Declare round_digits'):
        validate_plan(plan,{'id':'x','target_duration_s':60})
    for s in plan['scenes']:s['arithmetic_checks'][0]['round_digits']=2
    validate_plan(plan,{'id':'x','target_duration_s':60})
    plan['scenes'][0]['arithmetic_checks'][0]['equals']=613.92
    with pytest.raises(ValueError,match='arithmetic check failed'):
        validate_plan(plan,{'id':'x','target_duration_s':60})


def test_null_optional_checks_and_transparent_shapes_are_renderable():
    scene={'title':'An outline','caption':'A circle outline','narration':'The outline marks one region in this diagram.',
           'duration_s':15,'primitives':[{'type':'circle','x':.5,'y':.5,'r':.1,'fill':'none'}],
           'arithmetic_checks':None}
    plan={'case_id':'x','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    validate_plan(plan,{'id':'x','target_duration_s':60})
    assert all(s['arithmetic_checks']==[] for s in plan['scenes'])
    assert inspect_layout(plan)==[]
    plan['scenes'][0]['primitives'][0]['fill']=False
    with pytest.raises(ValueError,match='CSS color string'):
        validate_plan(plan,{'id':'x','target_duration_s':60})
