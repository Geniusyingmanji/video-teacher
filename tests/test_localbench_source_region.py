import copy

import numpy as np
import pytest
from PIL import Image,ImageDraw

from localbench.source_region import (apply_region,check_curve_fit,expression_values,
                                     region_arrays,region_facts,refine_mapping)


def spec():
    return {'lower_expression':'0.25*x','upper_expression':'sin(x)',
            'origin':[.4,.6],'unit_x':.08,'unit_y':.08,
            'lower_color':'#a34cf0','upper_color':'#d57d39'}


def source_plot():
    image=Image.new('RGB',(500,400),'white');draw=ImageDraw.Draw(image);s=spec()
    draw.line((0,240,499,240),fill='#333333',width=2)
    draw.line((200,0,200,399),fill='#333333',width=2)
    for x in range(0,500,40):draw.line((x,0,x,399),fill='#dddddd')
    xs,lo,hi,_=region_arrays(s,image.size)
    for key,ys in (('lower_color',lo),('upper_color',hi)):
        draw.line([(i,(.6-y*.08)*400) for i,y in enumerate(ys)],fill=s[key],width=3)
    return image


def test_disconnected_negative_region_is_included_in_full_domain():
    facts=region_facts(spec(),(500,400))
    intervals=facts['sampled_solution_intervals']
    assert len(intervals)==2 and intervals[0][0]==-5
    assert intervals[0][1]<-2.4 and 0<intervals[1][0]<.1 and 2.4<intervals[1][1]<2.5
    assert next(x for x in facts['sample_checks'] if x['x']==-3)['nonempty_vertical_interval']
    assert not next(x for x in facts['sample_checks'] if x['x']==-1)['nonempty_vertical_interval']
    roots=facts['estimated_open_intervals']
    assert len(roots)==2 and roots[0]['clipped_left']
    assert abs(roots[0]['end']+2.47457678737)<1e-7
    assert abs(roots[1]['start'])<1e-8 and abs(roots[1]['end']-2.47457678737)<1e-7


def test_source_ink_and_pixels_outside_mathematical_region_are_unchanged():
    source=source_plot();before=np.array(source);after=np.array(apply_region(source,spec()))
    _,_,_,mask=region_arrays(spec(),source.size)
    protected=(before.min(axis=2)<248)|~mask
    assert np.array_equal(before[protected],after[protected])
    assert np.any(before[~protected]!=after[~protected])
    assert np.array_equal(before,np.array(source))
    assert np.array_equal(before,np.array(apply_region(source,spec(),progress=0)))


def test_omission_control_changes_only_negative_region_not_positive_solution():
    source=source_plot();full=np.array(apply_region(source,spec()))
    control=np.array(apply_region(source,spec(),restriction='positive_only'))
    xs,_,_,_=region_arrays(spec(),source.size)
    assert np.array_equal(full[:,xs>=0],control[:,xs>=0])
    assert np.any(full[:,xs<0]!=control[:,xs<0])
    assert np.array_equal(control[:,xs<0],np.array(source)[:,xs<0])


def test_curve_fit_rejects_misaligned_calibration():
    source=source_plot();assert check_curve_fit(source,spec())['passed']
    wrong=copy.deepcopy(spec());wrong['origin'][1]+=.1
    assert not check_curve_fit(source,wrong)['passed']


def test_pixel_calibration_recovers_axes_without_changing_expressions():
    source=source_plot();wrong=spec();wrong['unit_x']=.074;wrong['origin'][1]+=.015
    assert not check_curve_fit(source,wrong)['passed']
    refined,receipt=refine_mapping(source,wrong)
    assert abs(refined['unit_x']-.08)<.001
    assert abs(refined['origin'][1]-.6)<.004
    assert refined['lower_expression']==wrong['lower_expression']
    assert refined['upper_expression']==wrong['upper_expression']
    assert receipt['identifiable_four_parameters'] and receipt['final_curve_fit']['passed']


def test_region_verification_uses_public_task_not_generator_state():
    from localbench.verification import checks_for
    case={'prompt_text':'Shade the region g(x) < y < f(x) on this plot.',
          'source':{'source_image_path':'before.png'}}
    checks=checks_for(case)
    assert {c['id'] for c in checks}=={'source_curve_preservation','source_inequality_region_coverage'}
    coverage=checks[1]
    assert coverage['review_last_frame'] and 'ENTIRE visible x-domain' in coverage['question']
    case['prompt_text']='Replace the label with the correct number.'
    assert checks_for(case)[0]['id']=='source_preservation_and_target_edit'


def test_control_keeps_teaching_content_and_only_changes_rendered_region_restriction():
    from localbench.region_controls import omit_negative
    plan={'scenes':[{'narration':'Explain both intervals.', 'duration_s':10,'caption':'Both intervals',
                     'source_visual':{'edits':[{'kind':'fill_between','spec':spec()}]}}]}
    control,changed=omit_negative(plan)
    assert changed==[0]
    for key in ('narration','caption','duration_s'):assert control['scenes'][0][key]==plan['scenes'][0][key]
    assert 'restriction' not in plan['scenes'][0]['source_visual']['edits'][0]
    assert control['scenes'][0]['source_visual']['edits'][0]['restriction']=='positive_only'


@pytest.mark.parametrize('expr',["__import__('os').system('echo x')",'x.__class__','sin(x, 3)','x**99','1/(x-x)'])
def test_region_expressions_reject_executable_or_unbounded_inputs(expr):
    with pytest.raises((ValueError,ArithmeticError)):
        expression_values(expr,np.array([1.,2.]))
