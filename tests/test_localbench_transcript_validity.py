import copy

from localbench.transcript_validity import apply_validity


def test_lexical_gap_cannot_receive_complete_overall_score_but_keeps_observed_ratings():
    raw={'scoring':{'overall':99,'groups':{'video':100,'teaching':98}},
         'dimensions':{'conceptual_correctness':{'score':100}},'evaluation_status':'scored_all_dimensions'}
    snapshot=copy.deepcopy(raw)
    audio=[{'id':'A02','transcript_guard':{'status':'partial','unresolved_spans':[{'id':'U00','start_s':37,'end_s':38}]}}]
    out=apply_validity(raw,audio)
    assert raw==snapshot and out['dimensions']==raw['dimensions']
    assert out['scoring']['overall'] is None and out['scoring']['observed_evidence_mean']==99
    assert out['scoring']['groups']==raw['scoring']['groups']
    assert not out['transcript_evidence_validity']['all_transcript_evidence_resolved']


def test_guard_does_not_invent_an_overall_score_when_another_stage_is_missing():
    raw={'scoring':{'overall':None,'status':'unresolved_verification_conflict'},'dimensions':{},
         'evaluation_status':'incomplete_scores'}
    resolved=[{'id':'A00','transcript_guard':{'status':'corroborated','unresolved_spans':[]}}]
    assert apply_validity(raw,resolved)['scoring']==raw['scoring']
    missing=[{'id':'A00','transcript_guard':{'status':'listener_evidence_unavailable'}}]
    out=apply_validity(raw,missing)
    assert out['scoring']['overall'] is None and out['scoring']['observed_evidence_mean'] is None
    assert out['scoring']['prior_status']=='unresolved_verification_conflict'
    assert apply_validity(raw,[])==raw
