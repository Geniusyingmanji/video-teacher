import copy
import json
from pathlib import Path

import pytest

from localbench.scientific_audit import audit_case, check_chain, expression, validate_public
from localbench.finding_consistency import contradiction
from localbench.reference_contract import validate_requirement_findings
from localbench.linear_algebra import compile_state


def test_snell_reference_error_blocked_but_correct_law_and_counterexample_allowed():
    bad={'id':'a','prompt_text':"Derive Snell's law: v1 * sin(θ1) = v2 * sin(θ2). Substitute v=c/n to obtain the law."}
    assert audit_case(bad)['status']=='conflict'
    with pytest.raises(ValueError,match='scientific conflict'):validate_public(bad)
    for text in ["Derive Snell: sin(theta1)/v1 = sin(theta2)/v2.",
                 "Snell misconception: v1*sin(theta1)=v2*sin(theta2) is not the correct derivation."]:
        assert not audit_case({'prompt_text':text})['issues']
    private={**bad,'prompt_text':'Explain refraction.','expected_concepts':[bad['prompt_text']]}
    assert not audit_case(private,public_only=True)['issues']
    assert audit_case(private)['issues']
    contract={'reference_items':[{'field':'expected_concepts','quote':bad['prompt_text'],'role':'conflicting_reference'}]}
    assert not audit_case(private,contract=contract)['issues']


def test_generic_chain_proves_equivalence_without_accepting_spurious_roots_or_poles():
    assert check_chain({'equations':['2*x+5=17','2*x=12','x=6']})['status']=='proven_equivalent'
    assert check_chain({'equations':['x*x=4','x=2']})['status']=='unverified'
    assert check_chain({'equations':['x/x=1','1=1']})['status']=='unverified'
    assert check_chain({'equations':['x/x=1','1=1'],'nonzero':['x']})['status']=='proven_equivalent'
    correct={'equations':['sin(theta1)/v1=sin(theta2)/v2','n1*sin(theta1)=n2*sin(theta2)'],
             'nonzero':['c','n1','n2'],'substitutions':{'v1':'c/n1','v2':'c/n2'}}
    assert check_chain(correct)['status']=='proven_equivalent'
    wrong=copy.deepcopy(correct);wrong['equations'][0]='v1*sin(theta1)=v2*sin(theta2)'
    assert check_chain(wrong)['status']=='unverified'
    with pytest.raises(ValueError):check_chain({'equations':['x/x=1','1=1'],'nonzero':['x'],'substitutions':{'x':'0'}})


@pytest.mark.parametrize('text',["__import__('os').system('id')","x.__class__","[x for x in range(4)]","2**1000000","1/0"])
def test_equation_parser_never_executes_model_code(text):
    with pytest.raises((ValueError,SyntaxError)):expression(text,{})


@pytest.mark.parametrize('field,text',[
    ('finding','partial'),('observed','No visual check is shown.'),
    ('reason','The requested example is absent.'),('reason','Narration unverified; obligation incomplete.')])
def test_old_scorecard_partial_or_missing_cannot_be_met(field,text):
    raw={'requirement_findings':[{'requirement_id':'R1','verdict':'met','reason':'Complete.',
                                 'evidence_ids':['F00'],field:text}]}
    with pytest.raises(ValueError,match='fulfillment/decision conflict'):
        validate_requirement_findings(raw,{'requirements':[{'id':'R1'}]},{'F00'})


def test_explicit_fulfillment_and_negation_are_not_confused_with_defects():
    assert contradiction({'verdict':'met','fulfillment':'partial','reason':'Looks fine.'})
    assert not contradiction({'verdict':'met','fulfillment':'complete','reason':'No missing steps and no overlap.'})
    assert not contradiction({'verdict':'met','reason':'The example is not missing.'})
    assert not contradiction({'verdict':'missing','fulfillment':'absent','reason':'No narration.'})


def test_dot_numeric_readout_changes_with_the_actual_vector():
    p={'type':'linear_algebra','operation':'dot','u':[1,0],'v':[0,1],'v_end':[1,1]}
    start=compile_state(p,0);end=compile_state(p,1)
    assert start['dot']==0 and end['dot']==1
    assert end['vectors']['projection']==[1,0]
    assert '1' in end['readout'] and end['readout']!=start['readout']
    with pytest.raises(ValueError):compile_state({**p,'dot':0},1)


def test_matrix_composition_and_basis_share_computed_world_coordinates():
    p={'type':'linear_algebra','operation':'composition','first':[[2,0],[0,1]],'second':[[1,1],[0,1]],'v':[1,1]}
    end=compile_state(p)
    assert end['vectors']['B(Av)']==end['vectors']['(BA)v']==end['vectors']['current']==[3,1]
    assert end['grid_matrix']==end['matrix']==[[2,1],[0,1]]
    b=compile_state({'type':'linear_algebra','operation':'basis','basis':[[1,1],[0,1]],'v':[3,2]})
    assert b['coordinates']==[1,2] and b['reconstructed']==b['vectors']['same v']==[3,2]
    with pytest.raises(ValueError):compile_state({'type':'linear_algebra','operation':'basis','basis':[[1,2],[2,4]],'v':[3,2]})


def test_computed_renderer_is_wired_without_separate_hand_authored_readouts(tmp_path):
    from localbench.scene import render_frame, validate_plan
    primitive={'type':'linear_algebra','operation':'dot','u':[1,0],'v':[0,1],'v_end':[1,1]}
    scene={'title':'Dot product','caption':'The readout follows the same vectors.',
           'narration':'Observe the vector projection and compare the changing computed dot product.',
           'duration_s':4,'primitives':[primitive]}
    p={'case_id':'a','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    validate_plan(p,{'id':'a','target_duration_s':16,'prompt_text':'Explain dot product.'})
    before,_=render_frame(scene,0);after,issues=render_frame(scene,1)
    assert before.tobytes()!=after.tobytes()
    after.save(tmp_path/'computed_dot.png')
    assert not [i for i in issues if i.get('kind') in {'text_overlap','text_outside_panel'}]


def test_versioned_snell_correction_is_algebraically_consistent_without_rewriting_old_results():
    from localbench.common import ROOT
    reference=json.loads((ROOT/'data/reference_corrections/snell_wavefront_v1.json').read_text())
    assert audit_case(reference['public_task'])['status']=='no_known_conflict'
    assert check_chain(reference['algebraic_check'])['status']=='proven_equivalent'
    assert 'not a replacement of historical scores' in reference['scope']


def test_partial_derivatives_and_partial_fractions_are_not_partial_fulfillment():
    for text in ['The partial derivative is computed and displayed correctly.',
                 'Partial fractions are decomposed and verified.']:
        assert not contradiction({'verdict':'met','reason':text})


@pytest.mark.parametrize('formula',[
    'v1Δt*sin(θ1)=v2Δt*sin(θ2)',
    r'v_{1}\cdot\Delta t\sin(\theta_{1})=v_{2}\cdot\Delta t\sin(\theta_{2})'])
def test_snell_error_with_shared_time_factor_is_not_hidden_by_notation(formula):
    assert audit_case({'prompt_text':'Derive Snell: '+formula})['issues']


def test_editorial_label_cannot_freeze_an_unresolved_reference_concern():
    from localbench.reference_contract import validate_contract
    case={'id':'a','prompt_text':'Explain.'}
    contract={'case_id':'a','requirements':[{'id':'R1','kind':'explicit','text':'Explain.','reason':'Public request.',
              'prompt_quotes':['Explain.']}],'reference_items':[],'concerns':['The factual premise is unresolved.']}
    with pytest.raises(ValueError,match='unresolved reference concerns'):
        validate_contract(contract,case,frozen=True)


def test_content_reviewer_can_cite_computed_diagram_inputs_as_read_only_fields():
    from localbench.content_review import review_input
    primitive={'type':'linear_algebra','operation':'map','matrix':[[2,0],[0,1]],'v':[1,1]}
    s={'title':'Map','caption':'Map both coordinates.','narration':'Follow the computed vector.',
       'primitives':[primitive]}
    packet=review_input({'id':'a','prompt_text':'Use the stated matrix.'},{'scenes':[s,copy.deepcopy(s)]})
    second=packet['scenes'][1]
    assert second['texts']['primitives/0/matrix']=='[[2,0],[0,1]]'
    assert 'primitives/0/matrix' in second['read_only_fields']
    assert second['computed_linear_state'][0]['scene']==1


def test_malformed_fulfillment_raises_validation_error_instead_of_losing_valid_siblings():
    from localbench.finding_consistency import validate
    with pytest.raises(ValueError,match='Unknown fulfillment'):
        validate({'verdict':'met','fulfillment':['complete']})
