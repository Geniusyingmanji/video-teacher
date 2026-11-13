import pytest
import json

from localbench.human import rating_task
from localbench.human_agreement import compare, criterion_score, metrics, rank, match_scores
from localbench.rubric import DIMENSIONS


def test_task_clusters_preserve_variants_and_undefined_correlation():
    pairs=[{'case_id':'a','human_mean':1,'judge':2},
           {'case_id':'a','human_mean':3,'judge':4},
           {'case_id':'b','human_mean':5,'judge':4}]
    r=metrics(pairs)
    assert r['n_videos']==3 and r['n_tasks']==2 and r['mae']==1
    assert r['cluster_bootstrap_mae_95_ci']==[1,1]
    assert rank([1,3,3]).tolist()==[1,2.5,2.5]
    assert metrics([{'case_id':'a','human_mean':5,'judge':5}])['spearman'] is None


def test_invalidated_dimensions_cannot_enter_agreement_as_valid_scores():
    s={'dimensions':{'conceptual_correctness':{'score':None,'criteria':{
        'facts':{'status':'observed','score':5}}}}}
    assert criterion_score(s,'conceptual_correctness','facts') is None


def test_audio_criterion_uses_duration_weights_on_original_scale():
    s={'dimensions':{'audio_quality':{'score':50,'chunk_reviews':[
        {'status':'reviewed','start_s':0,'end_s':10,'criteria':{'signal':{'score':1}}},
        {'status':'reviewed','start_s':10,'end_s':40,'criteria':{'signal':{'score':5}}}]}}}
    assert criterion_score(s,'audio_quality','signal')==4


def test_no_ratings_or_single_rater_never_claim_paired_validation():
    tasks=[rating_task({'prompt_text':'Synthetic test'},'v1',r,'study') for r in ('r1','r2')]
    mapping=[{'item_id':'v1','case_id':'a','mode':'code'}]
    assert compare(tasks,[],mapping,{})['status']=='no_human_ratings'
    response={k:tasks[0][k] for k in ('assignment_id','item_id','rater_id','rubric_version')}
    response['dimensions']={d:{k:{'score':3,'note':'synthetic fixture'} for k in spec['criteria']}
                            for d,spec in DIMENSIONS.items()}
    s={'dimensions':{d:{'score':50,'criteria':{k:{'status':'observed','score':3} for k in spec['criteria']}}
                     for d,spec in DIMENSIONS.items()}}
    r=compare(tasks,[response],mapping,{'v1':s})
    assert r['status']=='no_usable_pairs'
    assert r['criteria']['visual_quality']['legibility']['mae'] is None


def test_matching_requires_task_and_media_hashes_and_one_score_per_video(tmp_path):
    study=tmp_path/'study';(study/'coordinator').mkdir(parents=True)
    (study/'coordinator/mapping.json').write_text(json.dumps([{
        'item_id':'v1','case_id':'a','original_sha256':'video_hash'}]))
    (study/'run_config.json').write_text(json.dumps({'case_hashes':{'a':'task_hash'},'rubric_version':'version'}))
    directory=tmp_path/'eval';p=directory/'a/code/scores.json';p.parent.mkdir(parents=True)
    score={'case_id':'a','video_sha256':'video_hash','case_hash':'stale_task',
           'rubric_version':'version','judge_model':'qwen-flash'}
    p.write_text(json.dumps(score))
    _,matched,_,skipped=match_scores(study,[directory])
    assert not matched and len(skipped)==1
    score['case_hash']='task_hash';p.write_text(json.dumps(score))
    assert set(match_scores(study,[directory])[1])=={'v1'}
    with pytest.raises(ValueError,match='multiple judge results'):
        match_scores(study,[directory,directory])
