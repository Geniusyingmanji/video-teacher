import copy

import pytest

from localbench.program_consistency import direction_claims, inspect_plan, validate


def plan(rotation='ccw', text='Air spirals inward and counterclockwise.'):
    return {'scenes': [{'title': 'Spiral airflow', 'caption': '', 'narration': text,
                        'primitives': [{'type': 'flow_path', 'x': .5, 'y': .5,
                                        'radius_start': .4, 'radius_end': .1,
                                        'rotation': rotation, 'turns': 1.5}]}]}


def test_correct_and_inverted_paths_checked_against_words_not_old_state():
    p = plan(); assert all(r['status'] == 'consistent' for r in validate(p)['records'])
    with pytest.raises(ValueError, match='computed path is cw'):
        validate(plan('cw'))
    assert validate(plan('cw', 'Air spirals inward and clockwise.'))
    p['scenes'][0]['primitives'][0].update(radius_start=.1,radius_end=.4)
    with pytest.raises(ValueError, match='computed path is outward'): validate(p)


@pytest.mark.parametrize('text', ['Air flows counter-clockwise.', 'Air flows counter clockwise.',
                                 'Air flows anticlockwise.', 'Air flows anti-clockwise.'])
def test_counterclockwise_spellings_do_not_create_clockwise_conflicts(text):
    claims, _ = direction_claims(plan(text=text)['scenes'][0])
    assert claims['rotation']['expected'] == 'ccw'


def test_mixed_negated_conditional_or_multi_flow_scenes_are_not_overclaimed():
    for text in ('Air flows clockwise and counterclockwise.',
                 'Air does not flow clockwise.', 'If reversed, air would flow clockwise.'):
        r=inspect_plan(plan(text=text))
        assert not any(x['status']=='conflict' for x in r['records'])
        assert not any(x.get('field')=='rotation' for x in r['records'])
    p=plan();p['scenes'][0]['primitives'].append(copy.deepcopy(p['scenes'][0]['primitives'][0]))
    assert inspect_plan(p)['records'][0]['status']=='unverified'


def test_checker_reports_consistency_not_geophysical_truth_or_hidden_answers():
    # Southern versus northern science is not inferred by this bounded checker.
    p=plan('cw','Air flows clockwise in the Northern Hemisphere.')
    before=copy.deepcopy(p)
    assert all(x['status']=='consistent' for x in validate(p)['records'])
    assert p==before


def test_rejected_direction_patch_never_enters_retry_state(monkeypatch, tmp_path):
    import json
    import localbench.visual_agent as agent
    original=plan(); original['case_id']='flow'
    original['scenes']*=4
    original=copy.deepcopy(original)
    for s in original['scenes']:
        s.update(caption='Air spirals inward.',duration_s=10)
    inputs=[]
    class Client:
        def chat(self,messages,**kwargs):
            body=json.loads(messages[1]['content'][0]['text']);inputs.append(body)
            if len(inputs)>1:return json.dumps({'replacements':[]})
            wrong=copy.deepcopy(original['scenes'][0]['primitives']);wrong[0]['rotation']='cw'
            return json.dumps({'replacements':[{'scene':0,'primitives':wrong}]})
    result,errors=agent.patch(Client(),{'id':'flow','target_duration_s':40},original,
                             {'issues':[]},{'rules':[]},[],tmp_path,'regression')
    assert result==original and len(errors)==1
    assert 'program-language conflict' in errors[0]['error']
    assert inputs[1]['current_plan']==original
    assert json.loads((tmp_path/'program_consistency_0.json').read_text())['records'][0]['status']=='conflict'


def test_replacing_the_only_flow_with_an_unchecked_representation_cannot_bypass_guard():
    original=plan();changed=copy.deepcopy(original)
    changed['scenes'][0]['primitives']=[]
    with pytest.raises(ValueError,match='cannot verify'):
        validate(changed,reference=original)
