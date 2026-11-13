import copy

from localbench.requirements import output_checks


def test_silence_is_a_requirement_failure_without_changing_scores():
    result={'scoring':{'overall':95},'dimensions':{}}
    original=copy.deepcopy(result)
    checks=output_checks(result,[{'id':'A00','digital_silence':True,'transcript_valid':True,'transcript':''}])
    assert 'spoken_narration_presence' in checks['failed']
    assert 'sampled_speech_visual_synchrony' in checks['failed']
    assert result==original
    assert not checks['changes_weighted_scores']


def test_missing_or_undecodable_speech_is_not_proof_of_absence():
    checks=output_checks({},[{'id':'A00','status':'unverified','error':'decode failure'}])
    assert 'spoken_narration_presence' in checks['unverified']
    assert not checks['failed']


def test_low_alignment_needs_real_paired_failure_evidence():
    dimension={'criteria':{'synchrony':{'status':'observed','score':2}},
               'observations':[{'verdict':'misaligned','evidence_ids':['F01']}]}
    result={'dimensions':{'crossmodal_alignment':dimension}}
    assert 'sampled_speech_visual_synchrony' not in output_checks(result)['failed']
    dimension['observations'][0]['evidence_ids'].append('A00')
    assert 'sampled_speech_visual_synchrony' in output_checks(result)['failed']


def test_positive_sample_does_not_certify_full_lesson_or_language():
    dimension={'criteria':{'synchrony':{'status':'observed','score':5}},
               'observations':[{'verdict':'aligned','evidence_ids':['A00','F01']}]}
    result={'dimensions':{'crossmodal_alignment':dimension}}
    checks=output_checks(result,[{'id':'A00','transcript_valid':True,'transcript':'a short fragment'}],
                         {'metadata':{'decoded_duration_s':64}}, {'target_duration_s':65})
    assert checks['status']=='incomplete_evidence'
    assert 'audio_quality_scoring' in checks['unverified']
    assert checks['checks'][0]['status']=='observed'
    assert 'presence only' in checks['checks'][0]['reason']
    bad=output_checks(result,[],{'metadata':{'decoded_duration_s':5}},{'target_duration_s':65})
    assert 'target_duration' in bad['failed']


def test_evidence_range_normalization_preserves_actual_scores_and_rejects_gaps():
    import pytest
    from localbench.rubric import DIMENSIONS,validate_scores
    criteria={k:{'status':'observed','score':3,'evidence_ids':['F00-F02'],'reason':'Observed frames.'}
              for k in DIMENSIONS['visual_quality']['criteria']}
    raw={'dimensions':{'visual_quality':{'criteria':criteria}}}
    valid=validate_scores(raw,{'F00','F01','F02'},['visual_quality'])
    assert valid['visual_quality']['criteria']['legibility']['evidence_ids']==['F00','F01','F02']
    assert valid['visual_quality']['score']==50
    assert raw['dimensions']['visual_quality']['criteria']['legibility']['evidence_ids']==['F00-F02']
    with pytest.raises(ValueError):validate_scores(raw,{'F00','F02'},['visual_quality'])


def test_absence_observation_normalization_does_not_invent_positions_or_change_verdict():
    from localbench.verification import normalize_absence_observation
    raw={'checks':[{'id':'x','verdict':'fail','failure_type':'missing_visual',
                    'evidence_ids':['F00'],'observed_positions_or_counts':[],
                    'reason':'Only explanatory text is visible; no diagram is drawn.'}]}
    result=normalize_absence_observation(raw)
    assert result['checks'][0]['observed_positions_or_counts']==raw['checks'][0]['reason']
    assert result['checks'][0]['verdict']=='fail'
    assert raw['checks'][0]['observed_positions_or_counts']==[]


def test_public_requirement_failures_remain_visible_without_rewriting_scores():
    r={'reference_contract_hash':'frozen-hash','scoring':{'overall':93},
       'requirement_findings':[{'requirement_id':'R01','verdict':'missing','reason':'No required ray diagram appears.', 'evidence_ids':['F00','F31']},
                               {'requirement_id':'R02','verdict':'unverified','reason':'Label unreadable.', 'evidence_ids':['F10']}]}
    before=copy.deepcopy(r);d=output_checks(r)
    assert d['version']=='localbench-output-checks-dev3'
    assert 'public_requirement:R01' in d['failed']
    assert 'public_requirement:R02' in d['unverified']
    assert r==before and not d['changes_weighted_scores']


def test_refreshing_old_score_diagnostics_preserves_file(tmp_path):
    import json
    from localbench.requirements import checks_from_score_file
    p=tmp_path/'run/case/code/scores.json';p.parent.mkdir(parents=True)
    row={'case_id':'case','output_checks':{'version':'old'},'reference_contract_hash':'hash',
         'requirement_findings':[{'requirement_id':'R01','verdict':'missing','reason':'No diagram.', 'evidence_ids':['F01']}]}
    p.write_text(json.dumps(row));before=p.read_bytes()
    assert checks_from_score_file(p)=={'version':'old'}
    refreshed=checks_from_score_file(p,refresh=True)
    assert 'public_requirement:R01' in refreshed['failed']
    assert p.read_bytes()==before
