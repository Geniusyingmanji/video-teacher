import copy
import pytest
from localbench.relation_witness import validate


def row():
    return {'frame_id':'F00','screen_claims':['Air rises'],'comparison_claim':'Air rises',
        'claim_kind':'static_relation','observed_relations':[{'region':'diagram','objects':'air arrow',
        'geometry':'Arrowhead points downward into the water.'}],
        'reason':'The labelled rise arrow points down.','severity':'major','verdict':'contradicted',
        'contradiction_witness':{'kind':'opposed_relation','claim_quote':'Air rises',
            'diagram_relation_indices':[0],'expected':'upward arrow','observed':'downward arrow'}}


def check(r):return validate({'frames':[r]},[{'id':'F00'}])


def test_opposed_visible_relation_has_a_referentially_valid_witness():
    r=row();snapshot=copy.deepcopy(r)
    assert check(r)[0]['verdict']=='contradicted' and r==snapshot
    r['contradiction_witness']=None
    with pytest.raises(ValueError,match='typed witness'):check(r)


def test_missing_depiction_can_be_recorded_without_a_false_content_contradiction():
    r=row();r.update(verdict='insufficient_visual_support',severity='minor',
        observed_relations=[{'region':'diagram','objects':'water rectangle','geometry':'No connecting arrow is visible.'}],
        contradiction_witness=None,reason='The diagram does not demonstrate the described rise.')
    assert check(r)[0]['verdict']=='insufficient_visual_support'


def test_caption_or_fabricated_observation_cannot_supply_a_contradiction_witness():
    for index in [-1,1,True]:
        r=row();r['contradiction_witness']['diagram_relation_indices']=[index]
        with pytest.raises(ValueError,match='real diagram'):check(r)
    r=row();r['observed_relations'][0]['region']='caption'
    with pytest.raises(ValueError,match='caption/legend'):check(r)


def test_quote_identity_temporal_scope_and_witness_logic_are_required():
    r=row();r['contradiction_witness']['claim_quote']='Invented claim'
    with pytest.raises(ValueError,match='quote changed'):check(r)
    r=row();r['claim_kind']='ongoing_process'
    with pytest.raises(ValueError,match='single frame'):check(r)
    r=row();r['contradiction_witness']['observed']='upward arrow'
    with pytest.raises(ValueError,match='identical relations'):check(r)
    r=row();r['verdict']='consistent'
    with pytest.raises(ValueError,match='only contradicted'):check(r)
