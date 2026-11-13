import json

import pytest
from PIL import Image

from localbench import assets,source_audit
from localbench.audit import validate_review


def test_nested_evidence_quotes_match_actual_text_not_json_escapes():
    row={'id':'a','discipline_specific_rubric':['Is the "Goguryeo" label inside the red region?',
                                              'Keep other labels fixed.']}
    review={'id':'a','decision':'revise','checks':[],
            'issues':[{'field':'discipline_specific_rubric','quote':'Is the "Goguryeo" label inside the red region?'}]}
    assert validate_review(review,row)==review
    review['issues'][0]['quote']='Is the "Goguryeo" label outside the red region?'
    with pytest.raises(ValueError,match='nonliteral'):validate_review(review,row)
    review['issues'][0]['quote']='red region? Keep other'
    with pytest.raises(ValueError,match='nonliteral'):validate_review(review,row)


def test_nested_attachment_path_must_exist_and_quotes_must_match():
    row={'id':'a','public_attachments':[{'local_path':'/public/source.png'}]}
    review={'id':'a','decision':'revise','checks':[],
            'issues':[{'field':'public_attachments[0].local_path','quote':''}]}
    validate_review(review,row)
    for field in ('public_attachments[1].local_path','public_attachments[-1].local_path',
                  'public_attachments[0].answer','__class__'):
        review['issues'][0]['field']=field
        with pytest.raises(ValueError,match='actual field'):validate_review(review,row)
    review['issues'][0]={'field':'public_attachments[0].local_path','quote':'wrong.png'}
    with pytest.raises(ValueError,match='nonliteral'):validate_review(review,row)


def source_case(tmp_path,monkeypatch):
    path=tmp_path/'public.png';Image.new('RGB',(20,20),'white').save(path)
    monkeypatch.setattr(source_audit,'asset_path',lambda source:path)
    monkeypatch.setattr(assets,'asset_path',lambda source:path)
    row={'id':'a','prompt_text':'Find the path from A to H.',
         'expected_concepts':['PRIVATE_ANSWER'],
         'discipline_specific_rubric':['PRIVATE_RUBRIC'],
         'source':{'dataset':'GRADE','source_image_path':'image/before/a.png',
                   'target_image_path':'SECRET_ANSWER_IMAGE'},
         'local_review':{'secret':'PRIVATE_EDIT'}}
    return row,path


def test_independent_source_input_excludes_references_and_binds_image_bytes(tmp_path,monkeypatch):
    row,path=source_case(tmp_path,monkeypatch)
    material,content=source_audit.source_material(row)
    text=json.dumps(content)
    for forbidden in ('PRIVATE_ANSWER','PRIVATE_RUBRIC','SECRET_ANSWER_IMAGE','PRIVATE_EDIT','local_path'):
        assert forbidden not in text
    assert len(content)==2 and content[1]['image_url']['url'].startswith('data:image/png;base64,')
    row['expected_concepts']=['CHANGED_PRIVATE_ANSWER']
    assert source_audit.source_material(row)[0]['input_hash']==material['input_hash']
    Image.new('RGB',(20,20),'black').save(path)
    assert source_audit.source_material(row)[0]['input_hash']!=material['input_hash']


def test_independent_source_fails_on_changed_source_before_call(tmp_path,monkeypatch):
    row,_=source_case(tmp_path,monkeypatch)
    class NoCall:
        def chat(self,*args,**kwargs):raise AssertionError('must not call')
    with pytest.raises(ValueError,match='changed between'):
        source_audit.run_check(row,NoCall(),tmp_path/'out','wrong-hash')


def test_independent_source_preserves_explicit_uncertainty():
    result={'id':'a','status':'conditional','answer':'Depends on moisture.',
            'observations':[{'claim':'Temperature curve','location':'red curve'}],
            'reasoning':['Use relative humidity definition.'],'assumptions':[], 'uncertainties':[]}
    with pytest.raises(ValueError,match='assumptions'):source_audit.validate_check(result,'a')
    result['assumptions']=['Constant vapor pressure.']
    assert source_audit.validate_check(result,'a')==result
    result['status']='uncertain'
    with pytest.raises(ValueError,match='uncertainties'):source_audit.validate_check(result,'a')
    result['uncertainties']=['Moisture time series unspecified.']
    assert source_audit.validate_check(result,'a')==result


def test_image_only_observer_cannot_read_task_or_private_reference(tmp_path,monkeypatch):
    from localbench.source_observation import observation_material,validate_observation
    row,_=source_case(tmp_path,monkeypatch)
    row['prompt_text']='SECRET_TASK_TO_SHIFT_LEFT'
    material,content=observation_material(row)
    assert json.loads(content[0]['text'])=={'id':'a'}
    assert 'SECRET_TASK' not in json.dumps(content) and 'PRIVATE_' not in json.dumps(content)
    assert not material['task_text_provided'] and not material['reference_provided']
    with pytest.raises(ValueError):validate_observation([], 'a')


def test_attached_observation_requires_current_image_and_success(tmp_path,monkeypatch):
    from localbench.source_observation import observation_material,load_for_review
    row,image_path=source_case(tmp_path,monkeypatch)
    material,_=observation_material(row)
    base=tmp_path/'observations';(base/'a').mkdir(parents=True)
    path=base/'a/result.json'
    record={**material,'status':'observed','result':{'id':'a','labels':[],
            'relations':[{'description':'A line','location':'middle'}],'uncertainties':[]}}
    path.write_text(json.dumps(record))
    assert load_for_review(row,base)[0]==record['result']
    record['task_text_provided']=True;path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='not bound'):load_for_review(row,base)
    record['task_text_provided']=False;path.write_text(json.dumps(record))
    Image.new('RGB',(20,20),'black').save(image_path)
    with pytest.raises(ValueError,match='not bound'):load_for_review(row,base)
