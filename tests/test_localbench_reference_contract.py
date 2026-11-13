from pathlib import Path
import copy
import pytest
from localbench.common import digest,public_case
from localbench.reference_contract import (VERSION,reference_hash,validate_contract,judge_reference,validate_requirement_findings)


def fixture():
    case={'id':'a','prompt_text':'Show two replicas during a network partition.',
          'expected_visual_elements':['two nodes','CAP triangle']}
    contract={'case_id':'a','requirements':[{'id':'R01','text':'Show the two replicas and partition.',
        'kind':'explicit','prompt_quotes':['Show two replicas during a network partition.'],'reason':'Explicit public request.'}],
        'reference_items':[{'field':'expected_visual_elements','index':0,'quote':'two nodes',
        'role':'public_requirement','requirement_ids':['R01'],'reason':'The two requested replicas.'},
        {'field':'expected_visual_elements','index':1,'quote':'CAP triangle','role':'optional_implementation',
         'requirement_ids':[],'reason':'Public task does not require this depiction.'}],
        'concerns':[],'version':VERSION,'review_status':'editorial_reviewed','expert_verified':False,
        'public_input_hash':digest(public_case(case)),'reference_hash':reference_hash(case)}
    return case,contract


def test_contract_withholds_optional_style_but_keeps_required_semantics():
    case,contract=fixture();validate_contract(contract,case,frozen=True)
    exposed=judge_reference(contract)
    assert 'CAP triangle' not in str(exposed)
    assert 'two replicas' in str(exposed)
    assert contract['reference_items'][1]['quote']=='CAP triangle'


def test_contract_requires_complete_exact_reference_and_real_public_quotes():
    case,c=fixture()
    for mutate in [lambda d:d['requirements'][0].update(prompt_quotes=['Show a CAP triangle.']),
                   lambda d:d['reference_items'].pop(),
                   lambda d:d['reference_items'].append(copy.deepcopy(d['reference_items'][0])),
                   lambda d:d['reference_items'][1].update(quote='A triangle'),
                   lambda d:d['reference_items'][1].update(role='public_requirement')]:
        bad=copy.deepcopy(c);mutate(bad)
        with pytest.raises(ValueError):validate_contract(bad,case)


def test_stale_and_unreviewed_contracts_cannot_enter_scoring():
    case,c=fixture();case['prompt_text']+=' Draw a triangle.'
    with pytest.raises(ValueError,match='stale'):validate_contract(c,case,frozen=True)
    case,c=fixture();c['review_status']='model_proposal'
    with pytest.raises(ValueError,match='editorial'):validate_contract(c,case,frozen=True)
    case,c=fixture();case['expected_visual_elements'].append('an extra box')
    with pytest.raises(ValueError):validate_contract(c,case,frozen=True)


def test_requirement_coverage_cites_real_media_and_never_creates_optional_ids():
    _,c=fixture();r={'requirement_findings':[{'requirement_id':'R01','verdict':'met',
        'evidence_ids':['F01'],'reason':'Two replicas separated by a labelled broken connection.'}]}
    validate_requirement_findings(r,c,{'F01'})
    r['requirement_findings'][0]['requirement_id']='OPTIONAL_CAP_TRIANGLE'
    with pytest.raises(ValueError):validate_requirement_findings(r,c,{'F01'})
    r['requirement_findings'][0]['requirement_id']='R01';r['requirement_findings'][0]['evidence_ids']=['F99']
    with pytest.raises(ValueError):validate_requirement_findings(r,c,{'F01'})


def test_quote_ids_expand_to_real_text_without_changing_roles():
    from localbench.reference_contract import proposal_evidence,expand_proposal
    case,_=fixture();e=proposal_evidence(case)
    assert e['prompt_quotes'][0]['text']==case['prompt_text']
    raw={'case_id':'a','requirements':[{'id':'R01','text':'Show replicas','kind':'explicit',
        'prompt_quote_ids':['P00'],'reason':'Public request'}],
        'reference_items':[{'reference_id':'V00','role':'public_requirement','requirement_ids':['R01'],'reason':'Replicas'},
          {'reference_id':'V01','role':'optional_implementation','requirement_ids':[],'reason':'One drawing choice'}],
        'concerns':[]}
    expanded=expand_proposal(raw,case)
    validate_contract(expanded,case)
    assert expanded['requirements'][0]['prompt_quotes']==[case['prompt_text']]
    assert expanded['reference_items'][1]['quote']=='CAP triangle'
    assert expanded['reference_items'][1]['role']==raw['reference_items'][1]['role']
    assert 'prompt_quotes' not in raw['requirements'][0]
    raw['requirements'][0]['prompt_quote_ids']=['P99']
    with pytest.raises(ValueError,match='unknown'):expand_proposal(raw,case)


def test_quote_expansion_does_not_repair_semantic_or_coverage_errors():
    from localbench.reference_contract import expand_proposal
    case,_=fixture()
    raw={'case_id':'a','requirements':[{'id':'R01','text':'Replicas','kind':'explicit',
       'prompt_quote_ids':['P00'],'reason':'Required'}],
       'reference_items':[{'reference_id':'V00','role':'necessary_implication','requirement_ids':['R01'],'reason':'Required'}],
       'concerns':[]}
    with pytest.raises(ValueError,match='role'):validate_contract(expand_proposal(raw,case),case)
    raw['reference_items'][0]['role']='public_requirement'
    with pytest.raises(ValueError,match='unclassified'):validate_contract(expand_proposal(raw,case),case)


def test_link_repair_cannot_invent_obligations_or_change_classification():
    from localbench.reference_contract import apply_link_repairs
    case,c=fixture()
    c['reference_items'][0].update(reference_id='V00',requirement_ids=['R99'])
    c['reference_items'][1]['reference_id']='V01'
    patch={'patches':[{'reference_id':'V00','previous_requirement_ids':['R99'],'requirement_ids':['R01']}]}
    fixed=apply_link_repairs(c,patch);validate_contract(fixed,case)
    assert fixed['requirements']==c['requirements']
    assert fixed['reference_items'][0]['role']==c['reference_items'][0]['role']
    assert c['reference_items'][0]['requirement_ids']==['R99']
    for links in [[],['R88'],['R01','R01']]:
        patch['patches'][0]['requirement_ids']=links
        with pytest.raises(ValueError):apply_link_repairs(c,patch)
    patch['patches'][0]['requirement_ids']=['R01'];patch['patches'][0]['role']='optional_implementation'
    with pytest.raises(ValueError):apply_link_repairs(c,patch)


def test_public_source_is_frozen_and_stale_image_contract_is_rejected(tmp_path,monkeypatch):
    import json
    from PIL import Image
    from localbench.reference_contract import source_input,public_source_hash
    from localbench import assets
    source=tmp_path/'public.png';Image.new('RGB',(30,20),'blue').save(source)
    private=tmp_path/'SECRET_TARGET.png';private.write_bytes(b'not an image; must not be read')
    monkeypatch.setattr(assets,'asset_path',lambda record:source)
    case,c=fixture();case['source']={'dataset':'GRADE','source_image_path':'image/before/test.png','target_image_path':str(private)}
    record,parts=source_input(case,tmp_path/'run')
    assert len([p for p in parts if p['type']=='image_url'])==1
    assert 'SECRET_TARGET' not in json.dumps(record)+json.dumps(public_case(case))
    assert Path(record['snapshot_path']).read_bytes()==source.read_bytes()
    c.update(public_input_hash=digest(public_case(case)),public_source_sha256=public_source_hash(case),public_source_observed=True)
    validate_contract(c,case,frozen=True)
    Image.new('RGB',(30,20),'red').save(source)
    with pytest.raises(ValueError,match='source changed'):validate_contract(c,case,frozen=True)


def test_source_reference_cannot_claim_review_without_image_observation(tmp_path,monkeypatch):
    from PIL import Image
    from localbench.reference_contract import public_source_hash
    from localbench import assets
    source=tmp_path/'public.png';Image.new('RGB',(20,20),'white').save(source)
    monkeypatch.setattr(assets,'asset_path',lambda record:source)
    case,c=fixture();case['source']={'dataset':'GRADE','source_image_path':'test.png'}
    c.update(public_input_hash=digest(public_case(case)),public_source_sha256=public_source_hash(case))
    with pytest.raises(ValueError,match='not observed'):validate_contract(c,case,frozen=True)


def test_semantic_protocol_requires_contract_and_keeps_old_protocols_addressable():
    from localbench.judge import evaluation_version
    assert evaluation_version()== 'localbench-ten-dimensions-dev14-integer-r4'
    assert evaluation_version({'case_id':'x'})=='localbench-ten-dimensions-dev14-integer-r4+reference-contract-v1'
    assert evaluation_version({'case_id':'x'},True)=='localbench-ten-dimensions-dev14-integer-r4+reference-contract-v1+semantic-outcomes-v1'
    with pytest.raises(ValueError,match='requires'):evaluation_version(None,True)


def test_requirement_id_alias_preserves_raw_values_and_rejects_ambiguity():
    _,contract=fixture()
    item={'id':'R01','verdict':'met','evidence_ids':['F01'],'reason':'Observed demonstration.'}
    raw={'requirement_findings':[item]}
    result=validate_requirement_findings(raw,contract,{'F01'})
    assert result[0]['requirement_id']=='R01' and 'id' not in result[0]
    assert result[0]['verdict']==item['verdict'] and result[0]['evidence_ids']==item['evidence_ids']
    assert 'requirement_id' not in item
    item['requirement_id']='R02'
    with pytest.raises(ValueError,match='conflicting'):validate_requirement_findings(raw,contract,{'F01'})


def test_source_citation_may_support_but_not_replace_generated_evidence():
    _,contract=fixture()
    item={'requirement_id':'R01','verdict':'met','evidence_ids':['S00','F01'],
          'reason':'Compare the public source and actual final frame.'}
    raw={'requirement_findings':[item]}
    validate_requirement_findings(raw,contract,{'S00','F01'},observed_ids={'F01'})
    item['evidence_ids']=['S00']
    with pytest.raises(ValueError,match='source alone'):
        validate_requirement_findings(raw,contract,{'S00','F01'},observed_ids={'F01'})
    item['evidence_ids']=['S99','F01']
    with pytest.raises(ValueError,match='supplied media'):
        validate_requirement_findings(raw,contract,{'S00','F01'},observed_ids={'F01'})
