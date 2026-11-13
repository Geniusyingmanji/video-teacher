import pytest

from localbench.common import public_case
from localbench.rubric import DIMENSIONS, aggregate_dimensions, validate_scores
from localbench.scene import arithmetic, inspect_layout
from localbench.audit import audit, validate_review
from localbench.state import binary_search, derive_state


def test_measured_speech_borrows_time_without_truncation():
    from localbench.timing import speech_frames
    from localbench.scene import FPS
    # The model assigns 4 s to a recap, but spoken dates actually need 9 s.
    plan = {'scenes':[{'duration_s':s} for s in (12,12,12,12,8,4)]}
    speech = [6.2,6.1,7.8,7.2,5.8,9.0]
    frames = speech_frames(plan, speech)
    assert sum(frames) == 60*FPS
    assert all(count/FPS >= seconds+.25 for count,seconds in zip(frames,speech))
    assert frames[-1]/FPS > 9
    with pytest.raises(ValueError,match='do not fit'):
        speech_frames(plan, [12]*6)


def test_timing_normalization_is_bounded_and_finite():
    from localbench.timing import normalize_plan_timing, allocate_frames
    plan = {'scenes':[{'duration_s':v} for v in (4,7,9,14,16,17)]}
    normalize_plan_timing(plan,65)
    assert sum(s['duration_s'] for s in plan['scenes']) == pytest.approx(65)
    assert all(4 <= s['duration_s'] <= 24 for s in plan['scenes'])
    assert plan['scenes'][-1]['authored_duration_s']==17
    assert allocate_frames([100,1,1],20,[4,4,4],[8,8,8])==[8,6,6]
    with pytest.raises(ValueError,match='finite'):
        allocate_frames([float('nan')],60,[0],[100])


def test_source_plan_preflight_and_merged_manifest(tmp_path):
    import json
    from localbench.pipeline import resolve_source_plan
    with pytest.raises(ValueError,match='does not exist'):
        resolve_source_plan(tmp_path/'missing','x')
    with pytest.raises(ValueError,match='no previous plan'):
        resolve_source_plan(tmp_path,'x')
    source=tmp_path/'old'/'x'
    source.mkdir(parents=True)
    (source/'plan.json').write_text('{}')
    (tmp_path/'manifest.json').write_text(json.dumps({'cases':[{'id':'x','artifacts':[{'video_path':str(source/'code.mp4')}]}]}))
    assert resolve_source_plan(tmp_path,'x')==source/'plan.json'


def test_evaluation_rejects_replaced_video_and_changed_protocol(tmp_path):
    from localbench.provenance import evaluation_inventory, file_hash, freeze_run
    video=tmp_path/'code.mp4'
    video.write_bytes(b'original media')
    run={'cases':[{'id':'x','artifacts':[{'complete':True,'mode':'code',
                                       'video_path':str(video),'sha256':file_hash(video)}]}]}
    assert len(evaluation_inventory(run,{'x':{}}))==1
    video.write_bytes(b'replaced media')
    with pytest.raises(ValueError,match='hash mismatch'):
        evaluation_inventory(run,{'x':{}})
    freeze_run(tmp_path/'eval',{'model':'cheap','rubric':'v1'})
    freeze_run(tmp_path/'eval',{'model':'cheap','rubric':'v1'})
    with pytest.raises(ValueError,match='changed'):
        freeze_run(tmp_path/'eval',{'model':'cheap','rubric':'v2'})


def test_chemistry_charge_glyphs_are_renderable():
    from localbench.scene import unsupported_glyphs
    assert unsupported_glyphs('Na⁺ Cl⁻ √13 17² α →') == []
    assert chr(0x10ffff) in unsupported_glyphs(chr(0x10ffff))


def test_source_edit_changes_only_declared_region_and_preserves_first_scene(tmp_path):
    import numpy as np
    from PIL import Image, ImageDraw
    from localbench.source_scene import bind_source, edited_reference
    source=tmp_path/'source.png'
    original=Image.new('RGB',(400,300),'white')
    ImageDraw.Draw(original).line((10,250,390,250),fill='blue',width=4)
    original.save(source)
    plan={'scenes':[{'teaching_lines':['one short explanation']} for _ in range(4)],
          'source_edits':[{'id':'x','kind':'replace_text','old_text':'x','text':'10',
                           'bbox':[.1,.1,.25,.22],'from_scene':2}]}
    bind_source(plan,{'local_path':str(source)})
    first,_=edited_reference(plan['scenes'][0]['source_visual'])
    final,_=edited_reference(plan['scenes'][-1]['source_visual'])
    assert np.array_equal(np.asarray(first),np.asarray(original))
    changed=np.any(np.asarray(final)!=np.asarray(original),axis=2)
    assert changed.any()
    changed[30:66,40:100]=False
    assert not changed.any()
    static,_=edited_reference(plan['scenes'][-1]['source_visual'],apply_edits=False)
    assert np.array_equal(np.asarray(static),np.asarray(original))


def test_source_replacement_preserves_colored_geometry_inside_bbox(tmp_path):
    import numpy as np
    from PIL import Image, ImageDraw
    from localbench.source_scene import edited_reference
    from localbench.provenance import file_hash
    image=Image.new('RGB',(400,300),'white')
    ImageDraw.Draw(image).line((0,32,399,32),fill='#125d84',width=3)
    path=tmp_path/'source.png';image.save(path)
    visual={'path':str(path),'sha256':file_hash(path),'edits':[
        {'id':'x','bbox':[.1,.1,.25,.22],'text':'10'}]}
    final,issues=edited_reference(visual)
    assert np.array_equal(np.asarray(final)[31:34],np.asarray(image)[31:34])


def test_change_localization_uses_pixels_and_excludes_lower_text():
    from PIL import Image,ImageDraw
    from localbench.source_changes import change_boxes
    before=Image.new('RGB',(400,300),'white')
    ImageDraw.Draw(before).line((80,80,220,200),fill='blue',width=5)
    after=before.copy();draw=ImageDraw.Draw(after)
    draw.rectangle((145,130,162,146),fill='white')
    draw.rectangle((10,260,380,280),fill='black')
    boxes=change_boxes(before,after)
    assert len(boxes)==1
    x0,y0,x1,y1=boxes[0]['bbox']
    assert x0<=150<=x1 and y0<=140<=y1
    assert y1<250


def test_generation_input_excludes_reference():
    case={'id':'test','prompt_text':'question','expected_concepts':['secret answer'],
          'expected_narrative_order':['hidden solution'],'discipline_specific_rubric':['private'],
          'answer':'never expose','target_duration_s':60}
    assert public_case(case)=={'id':'test','prompt_text':'question','target_duration_s':60}


def make_scores():
    return {'dimensions':{name:{'criteria':{c:{'score':4,'status':'observed','reason':'specific',
                                               'evidence_ids':['F00']} for c in dim['criteria']}}
                          for name,dim in DIMENSIONS.items()}}


def test_unverified_does_not_renormalize_total():
    raw=make_scores()
    raw['dimensions']['audio_quality']['criteria']['signal'].update(score=None,status='unverified',evidence_ids=[])
    dims=validate_scores(raw,{'F00'})
    assert aggregate_dimensions(dims)['overall'] is None
    assert dims['visual_quality']['score']==75


def test_fabricated_evidence_rejected():
    raw=make_scores()
    raw['dimensions']['visual_quality']['criteria']['legibility']['evidence_ids']=['F999']
    with pytest.raises(ValueError,match='fabricated'):validate_scores(raw,{'F00'})


def test_source_image_is_not_generated_video_evidence():
    raw=make_scores()
    raw['dimensions']['task_completeness']['criteria']['result']['evidence_ids']=['S00']
    with pytest.raises(ValueError,match='actual generated-video'):
        validate_scores(raw,{'F00','S00'},observed_ids={'F00'})


def test_nested_dimensions_recover_only_unique_complete_scores():
    from localbench.rubric import normalize_dimension_nesting
    proper=make_scores();items=list(proper['dimensions'].items())
    root={};cursor=root
    for name,value in items:
        cursor[name]={'criteria':value['criteria']};cursor=cursor[name]
    nested={'dimensions':root}
    assert validate_scores(nested,{'F00'})==validate_scores(proper,{'F00'})
    cursor[items[0][0]]=items[0][1]
    with pytest.raises(ValueError,match='duplicate'):
        normalize_dimension_nesting(nested,list(DIMENSIONS))


def test_pairing_uses_same_tasks_and_keeps_missing_scores():
    from localbench.compare import paired_summary
    def row(id_,mode,value):
        return {'case_id':id_,'mode':mode,'scoring':{'overall':value},
                'dimensions':{k:{'score':value} for k in DIMENSIONS}}
    data=[row('a','code',90),row('a','slides',50),row('b','code',100),row('b','slides',None)]
    result=paired_summary(data)['dimensions']['overall']
    assert result['mean_delta']==40
    assert result['n_pairs']==1 and result['missing_ids']==['b']
    assert result['bootstrap_95_ci'] is None
    result=paired_summary(data,expected_ids=['a','b','entirely_failed'])['dimensions']['overall']
    assert result['n_tasks']==3 and result['missing_ids']==['b','entirely_failed']


def test_generation_resume_checks_hash_and_preserves_failed_attempt(tmp_path):
    from localbench.pipeline import resumable_case
    from localbench.common import write_json
    from localbench.provenance import file_hash
    case=tmp_path/'x';case.mkdir()
    write_json(case/'manifest.json',{'id':'x','status':'render_failed','public_input_hash':'h'})
    previous,destination=resumable_case(tmp_path,'x','h',['code'])
    assert previous is None and destination==tmp_path/'retries'/'attempt_001'
    assert (case/'manifest.json').exists()
    video=case/'code.mp4';video.write_bytes(b'encoded bytes')
    result={'id':'x','status':'rendered','public_input_hash':'h',
            'artifacts':[{'mode':'code','complete':True,'video_path':str(video),'sha256':file_hash(video)}]}
    write_json(case/'manifest.json',result)
    assert resumable_case(tmp_path,'x','h',['code'])[0]==result
    video.write_bytes(b'altered media')
    with pytest.raises(ValueError,match='missing or changed'):
        resumable_case(tmp_path,'x','h',['code'])


@pytest.mark.parametrize('expression',["__import__('os').system('echo no')",'2**999','float("nan")','[1][0]'])
def test_arithmetic_does_not_execute_code(expression):
    with pytest.raises(ValueError):arithmetic(expression)


def test_arithmetic_and_schema_typing():
    assert arithmetic('180-(35+65)')==80
    raw=make_scores();raw['dimensions']['audio_quality']['criteria']['signal']['score']=True
    with pytest.raises(ValueError):validate_scores(raw,{'F00'})


def test_overlap_is_measured_from_text_bounds():
    p={'scenes':[{'title':'Test','caption':'Caption','primitives':[
        {'type':'text','text':'Label A','x':.2,'y':.2},
        {'type':'text','text':'Label B','x':.2,'y':.2}]}]}
    assert any(x['kind']=='text_overlap' for x in inspect_layout(p))


def test_nonliteral_audit_quote_rejected():
    with pytest.raises(ValueError,match='nonliteral'):
        validate_review({'id':'x','decision':'revise','checks':[],
                         'issues':[{'field':'prompt_text','quote':'not actually present'}]},
                        {'id':'x','prompt_text':'actual complete prompt'})


def test_binary_search_known_first_middle_case():
    trace=binary_search([1,3,5,7,9,11,13,15],7)
    assert trace==[{'low':0,'high':7,'mid':3,'value':7,'decision':'found'}]
    assert len(binary_search([1,3,5,7,9,11,13,15],15))==4
    with pytest.raises(ValueError):binary_search([3,1],1)


def test_state_derived_from_public_values_not_id():
    state=derive_state({'prompt_text':'Show binary search for the value 9 in [1, 3, 5, 7, 9].'})
    assert state['target']==9
    assert state['trace'][-1]['mid']==4
    assert arithmetic('(0+7)//2')==3
    assert arithmetic('7==7') is True


def test_exact_flat_criterion_mapping_is_normalized_without_changing_scores():
    raw=make_scores()
    raw['dimensions']['visual_quality']=raw['dimensions']['visual_quality']['criteria']
    normalized=validate_scores(raw,{'F00'})
    assert normalized['visual_quality']['score']==75
    assert normalized['visual_quality']['criteria']['legibility']['score']==4


def test_source_image_path_never_accepts_answer_or_traversal():
    from localbench.assets import asset_path
    for path in ['image/gt/math.png','../../secret','/absolute/path']:
        with pytest.raises(ValueError):asset_path({'source_image_path':path})


def test_linear_solver_supports_unseen_constants_and_signs():
    state=derive_state({'prompt_text':'Find x such that 3x - 5 = 7. Show how to solve it.'})
    assert state['solution']=='4'
    state=derive_state({'prompt_text':'Find x such that -2x + 3 = 10.'})
    assert state['solution']=='-7/2'


def test_punnett_varied_crosses_have_correct_recessive_fractions():
    assert derive_state({'prompt_text':'Cross Aa x Aa. Find the homozygous recessive fraction.'})['fraction']=='1/4'
    assert derive_state({'prompt_text':'Cross Aa x aa. Find the homozygous recessive fraction.'})['fraction']=='1/2'
    assert derive_state({'prompt_text':'Cross AA x aa. Find the homozygous recessive fraction.'})['fraction']=='0'


def test_genetics_pronunciation_preserves_allele_case():
    from localbench.pipeline import spoken_text
    state=derive_state({'prompt_text':'Cross Aa x Aa. Find the homozygous recessive fraction.'})
    text=spoken_text({'narration':"A parent is Aa. The 'A' allele differs from the 'a' allele. Count aa.",
                       'state_visual':{'state':state}})
    assert text.startswith('A parent is capital A, lowercase a.')
    assert 'capital A allele' in text and 'lowercase a allele' in text
    assert 'Count lowercase a, lowercase a.' in text
