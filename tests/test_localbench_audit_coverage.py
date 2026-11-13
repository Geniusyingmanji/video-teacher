import json

from localbench.audit import review_material
from localbench.audit_coverage import coverage_record,summarize
from localbench.common import digest


def task():
    return {'id':'a','discipline':'mathematics','task_type':'problem_solving',
            'prompt_text':'Calculate 2+3.','target_duration_s':60,'expected_concepts':['5']}


def test_bound_review_ignores_local_notes_but_invalidates_changed_content(tmp_path):
    row=task();_,_,material=review_material(row,tmp_path)
    review={'id':'a','decision':'revise','input_hash':digest(row),**material}
    row['local_review']={'note':'editorial metadata changed'}
    r=coverage_record(row,[(review,'review.json')],{'a'})
    assert r['current_review_input_supported'] and not r['whole_row_hash_matches']
    assert not r['expert_approved']
    row['expected_concepts']=['wrong private reference']
    assert not coverage_record(row,[(review,'review.json')],{'a'})['current_review_input_supported']
    assert json.loads((tmp_path/'review_input.json').read_text())['view']['expected_concepts']==['5']


def test_image_hash_changes_invalidate_review_and_legacy_source_stays_unproven(tmp_path,monkeypatch):
    from PIL import Image
    from localbench import audit,assets
    path=tmp_path/'source.png';Image.new('RGB',(20,20),'white').save(path)
    monkeypatch.setattr(audit,'asset_path',lambda source:path)
    monkeypatch.setattr(assets,'asset_path',lambda source:path)
    row=task();row['source']={'dataset':'GRADE','source_image_path':'image/before/a.png',
                              'target_image_path':'must-never-be-read.png'}
    _,content,material=review_material(row,tmp_path/'saved')
    assert len(content)==2 and (tmp_path/'saved/public_source.png').read_bytes()==path.read_bytes()
    legacy={'id':'a','decision':'usable','input_hash':digest(row)}
    assert not coverage_record(row,[(legacy,'legacy.json')],{'a'})['current_review_input_supported']
    bound={**legacy,**material}
    assert coverage_record(row,[(bound,'bound.json')],{'a'})['current_review_input_supported']
    Image.new('RGB',(20,20),'black').save(path)
    assert not coverage_record(row,[(bound,'bound.json')],{'a'})['current_review_input_supported']


def test_historical_matching_text_and_failed_reviews_have_distinct_coverage():
    row=task();review={'id':'a','decision':'reject','input_hash':digest(row)}
    r=coverage_record(row,[(review,'valid.json'),({'id':'a','status':'review_error'},'error.json')],set())
    assert len(r['reviews'])==1 and r['current_review_input_supported']
    assert summarize([r])['expert_approved']==0
    review['input_hash']='old'
    r=coverage_record(row,[(review,'old.json')],set())
    assert r['reviewed_any_version'] and not r['current_review_input_supported']
