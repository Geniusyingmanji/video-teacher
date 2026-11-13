import json

from localbench.split import assign, local_exposure


def test_exposure_propagates_through_same_source_and_near_duplicate_components():
    rows=[{'id':c,'prompt_text':f'Unique {c}','source':s} for c,s in [
        ('a',{'dataset':'source','source_id':'one'}),('b',{'dataset':'source','source_id':'one'}),
        ('c',{}),('d',{'dataset':'source','source_id':'two'})]]
    result,edges=assign(rows,{'a':[{'path':'actual_result.json'}]},[('b','c')])
    by_id={r['id']:r for r in result}
    assert all(by_id[c]['partition']=='development' for c in 'abc')
    assert by_id['c']['reason']=='related_to_development'
    assert by_id['d']['partition']=='reserved_candidate'
    assert len({by_id[c]['group_id'] for c in 'abc'})==1


def test_split_is_order_invariant_and_does_not_group_whole_source_dataset():
    rows=[{'id':'b','prompt_text':'Second question','source':{'dataset':'same','source_id':'b'}},
          {'id':'a','prompt_text':'First question','source':{'dataset':'same','source_id':'a'}}]
    assert assign(rows,{'a':[]},[])==assign(rows[::-1],{'a':[]},[])
    result,_=assign(rows,{'a':[]},[])
    assert result[0]['partition']=='development' and result[1]['partition']=='reserved_candidate'


def test_nested_trials_and_failed_planned_cases_are_not_reserved(tmp_path):
    trial=tmp_path/'results/localbench/continuous/round98'
    trial.mkdir(parents=True)
    (trial/'manifest.json').write_text(json.dumps({'cases':[{'id':'a','status':'failed'}],
                                                 'planned_ids':['a','b']}))
    (trial/'case.json').write_text(json.dumps({'id':'c'}))
    (trial/'evaluation_tasks.jsonl').write_text(json.dumps({'id':'d'})+'\n')
    exposure,receipts=local_exposure(tmp_path,set('abcde'))
    assert set(exposure)==set('abcd')
    assert all(r['sha256'] and r['matched_ids'] for r in receipts.values())
    assigned,_=assign([{'id':c,'prompt_text':c} for c in 'abcde'],exposure,[])
    assert {r['id'] for r in assigned if r['partition']=='reserved_candidate'}=={'e'}


def test_full_candidate_inventory_and_free_text_mentions_do_not_count(tmp_path):
    trial=tmp_path/'results/localbench/continuous/round98'
    trial.mkdir(parents=True)
    (trial/'candidate_bank.jsonl').write_text(json.dumps({'id':'unused'})+'\n')
    (trial/'notes.json').write_text(json.dumps({'id':'unused'}))
    (trial/'manifest.json').write_text(json.dumps({'cases':[], 'note':'unused'}))
    selected=tmp_path/'results/new_trial';selected.mkdir(parents=True)
    (selected/'tasks.jsonl').write_text(json.dumps({'id':'selected'})+'\n')
    exposure,_=local_exposure(tmp_path,{'unused','selected'})
    assert set(exposure)=={'selected'}


def test_retained_membership_survives_removed_experiment_outputs(tmp_path):
    path=tmp_path/'data/development_membership.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'cases':[{'id':'a','reason':'related_to_development'}]}))
    exposure,_=local_exposure(tmp_path,{'a','b'})
    assigned,_=assign([{'id':c,'prompt_text':c} for c in 'ab'],exposure,[])
    assert assigned[0]['partition']=='development'
    assert assigned[0]['reason']=='retained_development_membership'
    assert assigned[1]['partition']=='reserved_candidate'
