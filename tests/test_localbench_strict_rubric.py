import copy

import pytest

from localbench.rubric import DIMENSIONS,validate_scores
from localbench.strict_anchors import ANCHOR_ROWS
from localbench.relation_audit import validate


def ratings(name,score=3):
    return {'dimensions':{name:{'criteria':{k:{'status':'observed','score':score,'severity':'moderate',
             'reason':'A localized visible limitation.','limitation':'A label is ambiguous.',
             'high_score_evidence':'','evidence_ids':['F00']} for k in DIMENSIONS[name]['criteria']}}}}


def test_each_criterion_has_specific_failure_adequacy_and_high_score_anchors():
    assert set(ANCHOR_ROWS)==set(DIMENSIONS)
    assert sum(len(r) for r in ANCHOR_ROWS.values())==60
    for name,spec in DIMENSIONS.items():
        assert set(ANCHOR_ROWS[name])==set(spec['criteria'])
        assert all(len(t)==3 and all(len(x)>20 for x in t) for t in ANCHOR_ROWS[name].values())


def test_an_acknowledged_major_defect_cannot_receive_high_score():
    row=ratings('conceptual_correctness')
    row['dimensions']['conceptual_correctness']['criteria']['relationships'].update(score=5,severity='major',high_score_evidence='Fluent explanation.')
    with pytest.raises(ValueError,match='severity.*contradicts'):validate_scores(row,{'F00'},['conceptual_correctness'],strict=True)


@pytest.mark.parametrize('value',[1.5,2.5,3.5,4.5,True,float('nan')])
def test_current_protocol_rejects_half_ratings_and_non_numeric_levels(value):
    row=ratings('visual_quality')
    row['dimensions']['visual_quality']['criteria']['contrast']['score']=value
    with pytest.raises(ValueError):validate_scores(row,{'F00'},['visual_quality'],strict=True)


def test_integer_criteria_produce_fractional_aggregate_without_rounding_ratings():
    row=ratings('visual_quality')
    row['dimensions']['visual_quality']['criteria']['contrast'].update(score=4,severity='minor')
    assert validate_scores(row,{'F00'},['visual_quality'],strict=True)['visual_quality']['score']==pytest.approx(54.167)


def test_sector_geometry_uses_documented_clockwise_degrees_and_arc_is_unfilled():
    from localbench.scene import render_frame,validate_plan
    p={'type':'sector','x':.5,'y':.5,'r':.2,'start_angle':0,'end_angle':90,'fill':'#ff0000','color':'#ff0000'}
    scene={'title':'Quarter circle','caption':'A clockwise quarter circle.','narration':'The red sector is one quarter of the circle.',
           'duration_s':15,'primitives':[p]}
    plan={'case_id':'sector','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    case={'id':'sector','target_duration_s':60}
    validate_plan(plan,case)
    im,_=render_frame(scene,.5)
    assert im.getpixel((542,293))==(255,0,0)
    assert im.getpixel((542,233))!=(255,0,0)
    scene['primitives'][0]['type']='arc';im,_=render_frame(scene,.5)
    assert im.getpixel((542,293))!=(255,0,0)
    for invalid in (float('nan'),-1,361):
        bad=copy.deepcopy(plan);bad['scenes'][0]['primitives'][0]['end_angle']=invalid
        with pytest.raises(ValueError):validate_plan(bad,case)


@pytest.mark.parametrize('fix',[True,False])
def test_teaching_repair_is_limited_to_invalid_dimension_and_retains_sibling(tmp_path,fix):
    from localbench.judge import assess_teaching
    good=ratings('conceptual_correctness')['dimensions']
    bad=ratings('instructional_structure')['dimensions']
    bad['instructional_structure']['criteria']['transition'].update(score=4,severity='moderate')
    class Client:
        calls=0
        def chat(self,messages,**kwargs):
            self.calls+=1
            if self.calls==1:return {'dimensions':{**copy.deepcopy(good),**copy.deepcopy(bad)}}
            assert 'ONLY' in messages[-1]['content']
            if fix:bad['instructional_structure']['criteria']['transition']['score']=3
            return {'dimensions':copy.deepcopy(bad)}
    client=Client();errors=[]
    dimensions,raw,_=assess_teaching(client,[],list(good)+list(bad),{'F00'},{'F00'},'fixture',tmp_path,errors)
    assert client.calls==2 and dimensions['conceptual_correctness']['score']==50
    assert (dimensions['instructional_structure']['score']==50) if fix else (dimensions['instructional_structure']['score'] is None)
    assert len(errors)==(0 if fix else 1)


def test_high_score_requires_positive_criterion_evidence():
    row=ratings('visual_quality')
    item=row['dimensions']['visual_quality']['criteria']['contrast'];item.update(score=5,severity='none',limitation='none observed')
    with pytest.raises(ValueError,match='high score needs'):validate_scores(row,{'F00'},['visual_quality'],strict=True)
    item['high_score_evidence']='The smallest essential labels remain clearly separated from their local filled-box background.'
    assert validate_scores(row,{'F00'},['visual_quality'],strict=True)['visual_quality']['score'] is not None


def test_unrequested_optional_items_do_not_receive_free_full_credit():
    row=ratings('task_completeness')
    for key in ('verification','constraints'):
        row['dimensions']['task_completeness']['criteria'][key].update(status='not_applicable',score=None,
          evidence_ids=[],applicability_reason='The public prompt contains no such request/restriction.')
    d=validate_scores(row,{'F00'},['task_completeness'],strict=True)['task_completeness']
    assert d['score']==50 and d['applicable_criteria_count']==4
    row['dimensions']['task_completeness']['criteria']['demonstration'].update(status='not_applicable',score=None,
       evidence_ids=[],applicability_reason='A required diagram is absent.')
    with pytest.raises(ValueError,match='not optional'):validate_scores(row,{'F00'},['task_completeness'],strict=True)


def test_unverified_optional_item_does_not_disappear_from_score():
    row=ratings('task_completeness');row['dimensions']['task_completeness']['criteria']['verification'].update(status='unverified',score=None,evidence_ids=[])
    assert validate_scores(row,{'F00'},['task_completeness'],strict=True)['task_completeness']['score'] is None


def test_relation_contradiction_needs_claim_geometry_and_region():
    frames=[{'id':'F00'}]
    raw={'frames':[{'frame_id':'F00','screen_claims':['Flow from A to B'],
         'comparison_claim':'Flow from A to B','claim_kind':'static_relation',
         'observed_relations':[{'region':'diagram','objects':'A, B','geometry':'Arrowhead at A; line starts at B'}],
         'verdict':'contradicted','severity':'major','reason':'Diagram shows reverse flow.'}]}
    assert validate(raw,frames)
    broken=copy.deepcopy(raw);broken['frames'][0]['observed_relations']=[]
    with pytest.raises(ValueError,match='both'):validate(broken,frames)
    broken=copy.deepcopy(raw);broken['frames'][0]['observed_relations'][0].pop('region')
    with pytest.raises(ValueError,match='geometry'):validate(broken,frames)


@pytest.mark.parametrize('kind',['instruction','ongoing_process'])
def test_static_auditor_cannot_treat_motion_instruction_as_completed_state(kind):
    raw={'frames':[{'frame_id':'F00','screen_claims':['Moving sectors to a single point'],
         'comparison_claim':'Moving sectors to a single point','claim_kind':kind,
         'observed_relations':[{'region':'diagram','objects':'sectors','geometry':'Sectors at initial vertices.'}],
         'reason':'The sectors have not yet reached a single point.','severity':'minor','verdict':'contradicted'}]}
    with pytest.raises(ValueError,match='single frame'):validate(raw,[{'id':'F00'}])
    raw['frames'][0].update(verdict='ambiguous',severity='none')
    assert validate(raw,[{'id':'F00'}])


def test_severity_disagreement_is_preserved_without_rewriting_numeric_scores():
    from localbench.strict_anchors import score_review_conflicts
    dims={'conceptual_correctness':{'criteria':{'relationships':{'score':3.5}}}}
    before=copy.deepcopy(dims)
    checks=[{'id':'direction','verdict':'fail','severity':'major','affected':['conceptual_correctness.relationships']}]
    assert score_review_conflicts(checks,dims)[0]['score']==3.5
    assert dims==before
    dims['conceptual_correctness']['criteria']['relationships']['score']=2
    assert not score_review_conflicts(checks,dims)


def test_renderable_bad_layout_is_retained_in_baseline_and_after_bounded_method_repairs(tmp_path,monkeypatch):
    from localbench.pipeline import generate_one
    import localbench.pipeline as pipeline
    case={'id':'layout','prompt_text':'Explain two labels.','target_duration_s':60,'pedagogical_target_audience':'high school'}
    scene={'title':'Two labels','caption':'Both labels are visible.','slide_text':'Two labels.',
           'duration_s':15,'narration':'This is an explanation of the two labels shown here.',
           'primitives':[{'type':'text','x':.5,'y':.5,'align':'center','text':'FIRST'},
                         {'type':'text','x':.5,'y':.5,'align':'center','text':'SECOND'}]}
    plan={'case_id':'layout','scenes':[copy.deepcopy(scene) for _ in range(4)]}
    class Client:
        calls=0
        def chat(self,*args,**kwargs):self.calls+=1;return copy.deepcopy(plan)
    monkeypatch.setattr(pipeline,'synthesize',lambda *a,**k:('unused.wav',[]))
    monkeypatch.setattr(pipeline,'encode',lambda *a,**k:{'complete':True,'mode':'code'})
    for policy,expected_calls in [('report',1),('repair_then_report',3)]:
        c=Client();result=generate_one(case,tmp_path/policy,c,['code'],layout_policy=policy)
        assert result['status']=='rendered' and c.calls==expected_calls
        assert any(i['kind']=='text_overlap' for i in result['layout_findings'])


def test_audio_schema_retry_keeps_actual_media_and_requires_strict_fields(tmp_path,monkeypatch):
    from localbench.judge import assess_audio
    import localbench.judge as judge
    import localbench.asr as asr
    path=tmp_path/'chunk.wav';path.write_bytes(b'fixture audio passed only to a fake listener')
    monkeypatch.setattr(asr,'transcribe',lambda p:{'signal':{'digital_silence':False}})
    monkeypatch.setattr(judge,'reconcile',lambda a,r:{'status':'observed_present','reason':'fixture listener',
        'transcript':r['transcript'],'utterances':[],'transcript_valid':True,'timing_valid':False,'source':'fixture'})
    class Client:
        calls=0
        def chat(self,messages,**kwargs):
            self.calls+=1
            fields={'score':4,'reason':'Actual articulation is clear.'}
            if self.calls>1:fields.update(severity='none',limitation='none observed',high_score_evidence='')
            return {'transcript':'Actual spoken words.','speech_presence':'present',
                    'criteria':{k:fields.copy() for k in DIMENSIONS['audio_quality']['criteria']}}
    c=Client();r=assess_audio(c,{'id':'A01','status':'extracted','start_s':20,'end_s':40,'path':str(path),'sha256':'abc',
                                 'is_video_start':False,'is_video_end':False})
    assert c.calls==2 and r['status']=='reviewed'
    assert r['schema_reviews'][0]['status']=='invalid' and r['criteria']['signal']['score']==4
