import copy
import numpy as np
import pytest
from localbench.chart import PLOT, compile_chart
from localbench.scene import arithmetic, render_frame, validate_plan, inspect_layout


def coupon_chart():
    return {'type':'chart','x':0,'y':0,'x_values':list(range(1,11)),
            'x_label':'Payment time','x_unit':'year','y_label':'Present value','y_unit':'USD',
            'y_range':[0,50], 'series':[{'label':'Each $50 coupon',
              'expression':'coupon/(1+rate)**x','parameters':{'coupon':50,'rate':.05},'color':'#1868ae'}]}


def test_computed_coupon_data_and_decoded_pixels_have_same_decreasing_trend():
    spec=coupon_chart(); c=compile_chart(spec); s=c['series'][0]
    assert s['y_values'][0]==pytest.approx(50/1.05)
    assert s['y_values'][-1]==pytest.approx(50/1.05**10)
    assert sum(s['y_values'])==pytest.approx(386.086746459)
    assert all(a>b for a,b in zip(s['y_values'],s['y_values'][1:]))
    assert all(a[1]<b[1] for a,b in zip(s['pixel_points'],s['pixel_points'][1:]))
    image,issues=render_frame({'title':'Coupons','caption':'Later coupons are worth less today.',
                             'primitives':[spec]},1)
    assert not issues
    pixels=np.asarray(image)
    for x,y in s['pixel_points']:
        assert np.array_equal(pixels[int(y),int(x)],[24,104,174])


def test_axis_mapping_handles_negative_constant_and_multiple_series():
    p=coupon_chart();p['x_values']=[-2,0,2];p.pop('y_range')
    p['series']=[{'label':'Increasing','y_values':[-1,0,1]}, {'label':'Constant','expression':'3'}]
    c=compile_chart(p)
    assert c['y_range']==[-1,3]
    assert c['series'][0]['pixel_points'][0][1]==PLOT[3]
    assert all(pt[1]==PLOT[1] for pt in c['series'][1]['pixel_points'])
    p['series']=p['series'][1:]
    c=compile_chart(p)
    assert c['y_range'][0]<3<c['y_range'][1]


@pytest.mark.parametrize('change',[
    {'x_values':[1,1,3]}, {'x_values':[1,float('nan')]}, {'y_range':[0,20]},
    {'dx':.1}, {'series':[{'label':'bad','expression':'__import__("os").system("true")'}]},
    {'series':[{'label':'bad','expression':'x','parameters':{'x':4}}]},
    {'series':[{'label':'bad','y_values':[2,3]}]},
    {'series':[{'label':'bad','expression':'2**100'}]},
    {'series':[{'label':'bad','expression':'x>0'}]},
])
def test_invalid_numeric_charts_rejected_before_render(change):
    p=coupon_chart();p.update(change)
    with pytest.raises((ValueError,ZeroDivisionError)):compile_chart(p)


def test_expression_names_are_explicit_and_numeric():
    assert arithmetic('a/(1+r)**x',{'a':50,'r':.05,'x':10})==pytest.approx(30.695662677)
    with pytest.raises(ValueError):arithmetic('a+1')
    with pytest.raises(ValueError):arithmetic('a+1',{'a':True})
    with pytest.raises(ValueError):arithmetic('a.__class__',{'a':1})


def test_chart_plan_owns_panel_and_reports_real_label_overflow():
    s={'title':'Coupons','caption':'Caption','narration':'Discount every future coupon to today.',
       'slide_text':'Discount every coupon.', 'duration_s':15,'primitives':[coupon_chart()]}
    plan={'case_id':'x','scenes':[copy.deepcopy(s) for _ in range(4)]}
    validate_plan(plan,{'id':'x','target_duration_s':60})
    assert not inspect_layout(plan)
    plan['scenes'][0]['primitives'].append({'type':'text','x':.1,'y':.1,'text':'over chart'})
    with pytest.raises(ValueError,match='whole diagram panel'):validate_plan(plan,{'id':'x','target_duration_s':60})


def test_ticks_do_not_invent_fractional_cashflow_times():
    from localbench.chart import axis_ticks
    c=compile_chart(coupon_chart())
    assert axis_ticks(c,'x')==list(range(1,11))
    assert axis_ticks(c,'y')==[0,20,40]
    assert all(isinstance(x,int) for x in axis_ticks(c,'x'))
    c['x_values']=list(range(100))
    assert axis_ticks(c,'x')[0]==0 and axis_ticks(c,'x')[-1]==99
    assert len(axis_ticks(c,'x'))==5
