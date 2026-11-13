import copy

import pytest

from localbench.contact_pair import bind, interaction, validate_interaction, diagram
from localbench.scene import render_frame, validate_plan


def fixture():
    case={'id':'contact','target_duration_s':70,'prompt_text':"Explain Newton's third law with a person pushing a wall; force arrows must have equal magnitude and opposite directions."}
    words=['The person presses both hands against the wall.',
           'The person applies a push to the wall here.',
           'The wall simultaneously pushes back on the person.',
           'Notice the equal length and opposite directions here.',
           'These forces act on different objects, wall and person.',
           'Each interaction has equal and opposite forces on its partners.']
    return {'case_id':'contact','scenes':[{'title':'Interaction pair','caption':'Observe the person and wall.',
            'narration':w,'duration_s':70/6,'primitives':[{'type':'text','x':.2,'y':.2,'text':'Old'}]} for w in words]},case


def test_pair_rejects_lost_contact_wrong_recipients_and_unequal_vectors():
    state=interaction();validate_interaction(state)
    a,b=state['forces']
    assert a['origin']==b['origin']
    assert [a['origin'][i]+a['vector'][i] for i in range(2)][0]>state['contact_x']
    assert b['origin'][0]+b['vector'][0]<state['contact_x']
    for change,expected in [('hand','touch'),('recipient','recipient'),('magnitude','equal'),('origin','contact')]:
        broken=copy.deepcopy(state)
        if change=='hand':broken['hands'][0][0]-=30
        elif change=='recipient':broken['forces'][1]['recipient']='wall'
        elif change=='magnitude':broken['forces'][1]['vector'][0]=-160
        else:broken['forces'][1]['origin'][1]+=10
        with pytest.raises(ValueError,match=expected):validate_interaction(broken)


def test_lesson_preserves_text_timing_and_keeps_visible_contact_without_overdraw():
    plan,case=fixture();before=copy.deepcopy(plan)
    candidate,receipt=bind(plan,case)
    assert receipt['status']=='compiled' and plan==before
    validate_plan(candidate,case)
    for i,(old,new) in enumerate(zip(before['scenes'],candidate['scenes'])):
        assert all(new[k]==old[k] for k in ('title','caption','narration','duration_s'))
        arrows=[p for p in new['primitives'] if p['type']=='arrow']
        assert len(arrows)==(2 if i else 0)
        frame,issues=render_frame(new,.5,index=i,total=6)
        assert not issues
        # Physical arms reach the palms/wall even when no force arrows are drawn.
        for y in (234,286):
            assert frame.getpixel((626,y))==frame.getpixel((630,y))
        if i:
            assert frame.getpixel((540,260))==(34,108,66)
            assert frame.getpixel((720,260))==(179,52,45)


def test_compiler_does_not_rewrite_unrelated_or_incompatible_lesson():
    plan,case=fixture()
    assert bind(plan,{**case,'prompt_text':'Explain third law of thermodynamics.'})[1]['status']=='unsupported'
    plan['scenes'][2]['narration']='Then the person moves away from the wall.'
    assert bind(plan,case)[1]['status']=='unsupported'


def test_corrupted_render_geometry_cannot_keep_a_valid_contact_receipt():
    plan,case=fixture();candidate,_=bind(plan,case)
    candidate['scenes'][2]['primitives'][0]['x']+=.05
    with pytest.raises(ValueError,match='differ'):validate_plan(candidate,case)
