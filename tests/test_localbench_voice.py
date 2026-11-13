import copy

import pytest
from PIL import Image

from localbench.scene import validate_plan,render_frame
from localbench.voice import compile_voice,from_public_case,bind,COLORS


def task(actor='The cat',verb='chased',patient='the mouse'):
    return {'id':'voice','target_duration_s':60,
            'prompt_text':f"Use '{actor} {verb} {patient}' (active) and '{patient.capitalize()} was {verb} by {actor.lower()}' (passive)."}


def plan():
    s={'title':'Visualizing the Swap','duration_s':15,'caption':'Original caption.',
       'narration':'The participants stay the same while their grammatical roles change.',
       'primitives':[{'type':'text','x':.5,'y':.5,'text':'Original diagram'}]}
    return {'case_id':'voice','scenes':[copy.deepcopy(s) for _ in range(4)]}


@pytest.mark.parametrize('actor,verb,patient',[('The cat','chased','the mouse'),('The tutor','helped','the child')])
def test_correspondence_preserves_participants_instead_of_reversing_entities(actor,verb,patient):
    case=task(actor,verb,patient);spec=from_public_case(case);compiled=compile_voice(spec)
    by_id={n['id']:n for n in compiled['nodes']}
    for link in compiled['links']:
        a,b=by_id[link['source']],by_id[link['target']]
        assert a['entity']==b['entity'] and a['stage']=='active' and b['stage']=='passive'
    assert by_id['passive.patient']['role']=='subject'
    assert by_id['passive.agent']['role']=='by_agent'
    assert compiled['active_verb']==verb
    # The receiving node is attached to the arrow tip in the rendered pixels.
    p,_=bind(plan(),case);validate_plan(p,case)
    im,issues=render_frame(p['scenes'][0],.5)
    assert issues==[]
    from PIL import ImageColor
    for link in compiled['links']:
        x,y=link['points'][-1]
        assert im.getpixel((int(x),int(y)))==ImageColor.getrgb(COLORS[link['entity']])


def test_rejects_wrong_role_mapping_or_fabricated_public_sentence():
    case=task();spec=from_public_case(case)
    bad={**spec,'passive_sentence':'The cat was chased by the mouse'}
    with pytest.raises(ValueError,match='do not match'):compile_voice(bad)
    with pytest.raises(ValueError,match='endpoints'):compile_voice({**spec,'links':[]})
    p,_=bind(plan(),case)
    with pytest.raises(ValueError,match='public task'):validate_plan(p,{**case,'prompt_text':'Unrelated task'})
    assert from_public_case({'id':'x','prompt_text':'Explain voice','expected_answer':case['prompt_text']}) is None


def test_rewrite_keeps_non_conversion_scenes_and_full_audio_content():
    original=plan();original['scenes'][0]['title']='Introduction'
    before=copy.deepcopy(original)
    candidate,receipt=bind(original,task())
    assert original==before and candidate['scenes'][0]==original['scenes'][0]
    assert receipt['scene_indices']==[1,2,3]
    for old,new in zip(original['scenes'],candidate['scenes']):
        assert new['narration']==old['narration'] and new['duration_s']==old['duration_s']
    unsupported={'id':'x','prompt_text':"Use 'She ate rice' (active) and 'Rice was eaten by her' (passive)."}
    assert bind(original,unsupported)[1]['status']=='unsupported_public_sentence_pair'
