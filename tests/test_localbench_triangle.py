import copy
import math

import pytest

from localbench.scene import render_frame
from localbench.teaching_cues import caption, state_at
from localbench.triangle import VERSION, audit_motion, bind, compile_sequence, sectors, snapshot


def fixture(labels=('A', 'B', 'C')):
    phrases = ['Here are three different triangle shapes.',
               'The angles are labeled '+', '.join(labels[:2])+', and '+labels[2]+'.',
               'We detach each corner and keep all pieces unchanged.',
               'Now place the pieces side by side at one vertex.',
               'The outer rays form a straight line.',
               'This is a visual demonstration of the angle sum.']
    if labels[0] == 'α': phrases[1] = 'We label the angles Alpha, Beta, and Gamma.'
    vertices = [[.3,.7], [.7,.7], [.5,.3]]
    plan = {'case_id': 'triangle', 'scenes': [dict(title='Angle demonstration', caption='Three angles.',
            duration_s=10, narration=p, primitives=[{'type':'text','x':.2,'y':.2,'text':'Start'}]) for p in phrases]}
    plan['scenes'][1]['primitives'] = [{'type':'polyline','closed':True,'x':0,'y':0,'points':vertices}]+[
        {'type':'text','x':p[0],'y':p[1],'text':label} for p,label in zip(vertices,labels)]
    return plan


def test_angle_geometry_and_rigid_transforms_for_both_orientations():
    for vertices in ([[1,2],[8,3],[4,9]], [[4,9],[8,3],[1,2]]):
        state = {'version':VERSION, 'vertices':vertices, 'labels':['P','Q','R'],'radius':60}
        originals = sectors(vertices, state['labels'])
        assert sum(p['sweep'] for p in originals) == pytest.approx(180)
        for phase in ('identify','detach','rearrange','straight_angle'):
            for i in range(51):
                parts = snapshot(state, phase, i/50)
                for original,part in zip(originals, parts):
                    assert part['id'] == original['id']
                    assert part['radius'] == 60
                    assert part['sweep'] == original['sweep']
                    # Chord lengths provide a separate geometric invariant.
                    a = math.radians(part['start']); b = a+math.radians(part['sweep'])
                    assert math.dist([60*math.cos(a),60*math.sin(a)], [60*math.cos(b),60*math.sin(b)]) == pytest.approx(120*math.sin(math.radians(original['sweep']/2)))
        joined = sorted(snapshot(state, 'straight_angle', 1), key=lambda p:p['start'])
        for a,b in zip(joined, joined[1:]):
            assert (a['start']+a['sweep']) % 360 == pytest.approx(b['start'])
        assert (joined[-1]['start']+joined[-1]['sweep']+180) % 360-180 == pytest.approx(0, abs=1e-7)


@pytest.mark.parametrize('labels', [('A','B','C'), ('α','β','γ')])
def test_identity_and_exact_handoff_are_visible_across_scene_boundaries(labels):
    source = fixture(labels); before = copy.deepcopy(source)
    plan, receipt = compile_sequence(source)
    assert receipt['status'] == 'compiled'
    assert source == before
    assert plan['scenes'][0] == before['scenes'][0] and plan['scenes'][5] == before['scenes'][5]
    assert [(s['narration'],s['duration_s']) for s in plan['scenes']] == [(s['narration'],s['duration_s']) for s in source['scenes']]
    for left,right in [(1,2),(2,3),(3,4)]:
        a,b = plan['scenes'][left],plan['scenes'][right]
        sa,pa=state_at(a,1);sb,pb=state_at(b,0)
        assert snapshot(sa['state'],sa['phase'],pa)==snapshot(sb['state'],sb['phase'],pb)
        ia,_=render_frame(a,1);ib,_=render_frame(b,0)
        assert ia.crop((28,87,996,447)).tobytes()==ib.crop((28,87,996,447)).tobytes()
    for i in range(121):
        for s in plan['scenes'][1:5]:
            _,issues = render_frame(s,i/120)
            assert not issues
    assert 'now meet' not in caption(plan['scenes'][3],.5)
    assert 'now meet' in caption(plan['scenes'][3],.8)


def test_compiler_fails_closed_for_wrong_topic_or_ambiguous_sequence():
    plan=fixture()
    assert bind(plan, {'prompt_text':'Explain passive voice.'})[1]['status']=='unsupported'
    plan['scenes'][2]['narration']='Highlight the angles without moving them.'
    assert compile_sequence(plan)[1]['status']=='unsupported'
    with pytest.raises(ValueError): sectors([[0,0],[1,1],[2,2]], ['A','B','C'])


def test_motion_audit_detects_actual_mask_overlap_and_panel_escape():
    plan,_ = compile_sequence(fixture())
    assert audit_motion(plan) == []
    # Packing the original vertices too tightly makes their sectors overlap;
    # this is a geometric defect, independent of text-box overlap.
    bad=copy.deepcopy(plan)
    state=bad['scenes'][1]['state_visual']['state']
    state['vertices']=[[512+(x-512)*.25,265+(y-265)*.25] for x,y in state['vertices']]
    assert any(x['kind']=='sector_overlap' for x in audit_motion(bad))
    bad=copy.deepcopy(plan)
    for s in bad['scenes'][1:5]: s['state_visual']['state']['vertices'][2][1]=80
    assert any(x['kind']=='sector_outside_safe_panel' for x in audit_motion(bad))
