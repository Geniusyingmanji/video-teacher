import copy

import pytest

from localbench.keyboard import bind,diagram,geometry
from localbench.scene import render_frame,validate_plan


def fixture():
    case={'id':'piano','target_duration_s':55,'prompt_text':'On one piano octave, highlight C,D,E,F,G,A,B and upper C. Mark only E–F and B–C semitone gaps.'}
    words=['We examine a C major scale on a piano keyboard.',
           'Most adjacent notes in this scale are separated by whole steps.',
           'The first semitone occurs between E and F on the keyboard.',
           'The second semitone occurs between B and the upper C.',
           'Here is the complete pattern with two semitones marked.']
    plan={'case_id':'piano','scenes':[{'title':'C major','caption':'Read the highlighted natural keys.',
          'narration':w,'duration_s':11,'primitives':[{'type':'text','x':.2,'y':.2,'text':'C D E F G A B C'}]} for w in words]}
    return plan,case


def test_keyboard_physical_layout_and_exact_semitones():
    white,black,pairs=geometry()
    assert [w['name'] for w in white]==['C','D','E','F','G','A','B','C′']
    assert [b['pitch'] for b in black]==[61,63,66,68,70]
    assert pairs==[(2,3),(6,7)]
    for i,(a,b) in enumerate(zip(white,white[1:])):
        boundary=b['x'];cover=[k for k in black if k['x']<boundary<k['x']+k['width']]
        assert len(cover)==(0 if (i,i+1) in pairs else 1)
    with pytest.raises(ValueError,match='actual'):diagram([(3,4)])


def test_keyboard_binding_preserves_spoken_lesson_and_renders_readable():
    original,case=fixture();before=copy.deepcopy(original)
    plan,receipt=bind(original,case)
    assert receipt['status']=='compiled' and original==before
    validate_plan(plan,case)
    for i,(a,b) in enumerate(zip(before['scenes'],plan['scenes'])):
        assert {k:v for k,v in a.items() if k!='primitives'}=={k:v for k,v in b.items() if k not in {'primitives','arithmetic_checks'}}
        im,issues=render_frame(b,.5,index=i,total=5)
        assert not issues
        marked=[p for p in b['primitives'] if p.get('type')=='text' and 'semitone' in p['text']]
        assert len(marked)==[0,0,1,2,2][i]
        assert im.getpixel((324,240))!=(217,237,247) # D/E has an intervening black key.
    assert len(plan['scenes'][-1]['primitives'])<=36


def test_keyboard_rejects_other_tasks_and_incompatible_narration():
    plan,case=fixture()
    assert bind(plan,{**case,'prompt_text':'Explain musical rhythm.'})[1]['status']=='unsupported'
    plan['scenes'][2]['narration']='Now mark F and G as a semitone gap.'
    assert bind(plan,case)[1]['status']=='unsupported'
