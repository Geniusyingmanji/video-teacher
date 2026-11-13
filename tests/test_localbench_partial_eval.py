from localbench.judge import independent_stage
from localbench.rubric import DIMENSIONS,aggregate_dimensions


def test_invalid_independent_stage_cannot_become_score_or_erase_siblings():
    errors=[];scores={name:{'score':75} for name in DIMENSIONS}
    def invalid():raise ValueError('observed score requires evidence')
    scores.update(independent_stage('alignment',['crossmodal_alignment'],invalid,errors))
    assert scores['conceptual_correctness']['score']==75
    assert scores['visual_quality']['score']==75
    assert scores['crossmodal_alignment']['score'] is None
    assert aggregate_dimensions(scores)['overall'] is None
    assert errors[0]['error_type']=='ValueError'
    assert errors[0]['affected_dimensions']==['crossmodal_alignment']
    for criterion in scores['crossmodal_alignment']['criteria'].values():
        assert criterion['status']=='unverified' and criterion['score'] is None
        assert not criterion['evidence_ids']


def test_successful_stage_results_are_returned_without_score_changes():
    errors=[];expected={'visual_quality':{'score':50,'criteria':{'original':'evidence'}}}
    assert independent_stage('presentation',['visual_quality'],lambda:expected,errors) is expected
    assert not errors
