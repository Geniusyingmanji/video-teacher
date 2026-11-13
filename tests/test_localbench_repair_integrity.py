import copy
import json
from pathlib import Path

import pytest

from localbench.common import digest, public_case, write_json
from localbench.local_repair import apply_patch, repair
from localbench.provenance import file_hash
from localbench.rubric import DIMENSIONS


def scene_plan():
    scene={'title':'A step','caption':'Old caption.','narration':'This is a short spoken explanation of the step.',
           'duration_s':4,'primitives':[{'type':'text','x':.2,'y':.3,'text':'x = 6','size':26}]}
    return {'case_id':'a','scenes':[copy.deepcopy(scene) for _ in range(4)]}


def bound(tmp_path, field='caption'):
    case={'id':'a','prompt_text':'Explain the step.','target_duration_s':16}
    directory=tmp_path/'source';directory.mkdir()
    video=directory/'code.mp4';video.write_bytes(b'original unchanged media')
    p=scene_plan();write_json(directory/'plan.json',p)
    source={'id':'a','public_input_hash':digest(public_case(case)),
            'artifacts':[{'mode':'code','complete':True,'video_path':str(video),'sha256':file_hash(video)}]}
    from localbench.scene import renderer_fingerprint, VERSION
    source['artifacts'][0].update(plan_sha256=digest(p),scene_version=VERSION,renderer_sha256=renderer_fingerprint())
    patch={'case_id':'a','video_sha256':file_hash(video),'plan_sha256':digest(p),
           'replacements':[{'scene':1,'field':field,'old_text':p['scenes'][1][field],
                            'new_text':'A corrected clear caption.' if field=='caption' else 'The corrected explanation preserves all required task facts.'}]}
    return case,source,patch,p,video


@pytest.mark.parametrize('speech,fail',[(False,False),(True,False),(False,True)])
def test_local_repair_is_bound_and_preserves_original_on_failure(tmp_path, monkeypatch, speech, fail):
    import localbench.pipeline as pipeline
    import localbench.rerender as rerender
    import localbench.fixed_scene_speech as fixed
    case,source,patch,original,video=bound(tmp_path,'narration' if speech else 'caption')
    source.update(scoring={'overall':100},acceptance={'status':'passed'},quality_passed=True)
    seen={}
    def encode(plan,directory,audio,**kw):
        seen.update(plan=copy.deepcopy(plan),audio=audio,options=kw)
        if fail:raise ValueError('candidate encode failed')
        dest=directory/'code.mp4';dest.write_bytes(b'candidate')
        return {'mode':'code','complete':True,'video_path':str(dest),'sha256':file_hash(dest)}
    def synthesize(plan,source_plan,source_video,scenes,out,**kw):
        seen['speech_scenes']=scenes
        assert source_plan==original and source_video==video
        return tmp_path/'replacement.wav',{'unchanged_outside_replacements':True}
    monkeypatch.setattr(pipeline,'encode',encode)
    monkeypatch.setattr(rerender,'decoded_audio_hash',lambda _: 'same-decoded-samples')
    monkeypatch.setattr(fixed,'synthesize',synthesize)
    out=tmp_path/'repair';result=repair(case,source,patch,out)
    assert file_hash(video)==patch['video_sha256']
    assert json.loads((video.parent/'plan.json').read_text())==original
    if fail:
        assert result['status']=='repair_failed_original_retained'
        assert result['artifacts']==source['artifacts']
    else:
        assert result['status']=='rendered'
        assert 'scoring' not in result and 'acceptance' not in result and 'quality_passed' not in result
        assert result['evaluation_status']=='not_evaluated_after_repair'
        assert len(result['local_repair']['untargeted_render_checks'])==3
        assert seen['options']['copy_audio'] is (not speech)
        assert [s['duration_s'] for s in seen['plan']['scenes']]==[4]*4
        assert seen['plan']['scenes'][0]==original['scenes'][0]
        if speech:assert seen['speech_scenes']==[1]
        else:assert result['local_repair']['decoded_audio_identical']
    assert (out/'delivery.json').exists()


@pytest.mark.parametrize('field',['plan_sha256','video_sha256','case_id'])
def test_stale_patch_rejected_before_any_encoding(tmp_path,field):
    case,source,patch,_,_=bound(tmp_path);patch[field]='wrong'
    with pytest.raises(ValueError):repair(case,source,patch,tmp_path/'candidate')
    assert not (tmp_path/'candidate').exists()


def test_computed_captions_cannot_be_silently_patched_in_an_unused_field():
    p=scene_plan();p['scenes'][1]['teaching_cues']={'version':'computed'}
    patch={'replacements':[{'scene':1,'field':'caption','old_text':'Old caption.','new_text':'Corrected.'}]}
    with pytest.raises(ValueError,match='computed'):apply_patch(p,patch)


def rating(name):
    return {'criteria':{key:{'status':'observed','score':3,'severity':'moderate','reason':'A limited but visible demonstration.',
                            'limitation':'An intermediate label is unclear.','high_score_evidence':'','evidence_ids':['F00']}
                        for key in DIMENSIONS[name]['criteria']}}


def test_truncated_dimension_batch_recovers_in_smaller_calls(tmp_path):
    from localbench.judge import assess_teaching
    wanted=['conceptual_correctness','visual_teaching']
    class Client:
        calls=[]
        def chat(self,messages,**kwargs):
            self.calls.append(kwargs)
            if len(self.calls)==1:raise ValueError('provider truncated completion')
            prompt=messages[-1]['content']
            name=next(n for n in wanted if 'dimension: '+n+'.' in prompt)
            assert kwargs['max_tokens']<self.calls[0]['max_tokens']
            return {'dimensions':{name:rating(name)}}
    c=Client();errors=[]
    dims,_,_=assess_teaching(c,[],wanted,{'F00'},{'F00'},'a',tmp_path,errors)
    assert len(c.calls)==3 and not errors
    assert all(dims[n]['score']==50 for n in wanted)
    assert (tmp_path/'split_dimensions/conceptual_correctness/raw_visual_judge.json').exists()
    assert json.loads((tmp_path/'teaching_schema_reviews.json').read_text())[-1]['recovery']=='split_dimension_calls'


def test_requirement_recovery_chunks_and_retains_valid_dimension_ratings(tmp_path):
    from localbench.judge import assess_teaching
    contract={'requirements':[{'id':'R'+str(i)} for i in range(12)]}
    class Client:
        calls=0
        def chat(self,messages,**kw):
            self.calls+=1
            if self.calls==1:return {'dimensions':{'task_completeness':rating('task_completeness')}}
            start=int(kw['purpose'].split(':')[-1]);ids=[r['id'] for r in contract['requirements'][start:start+5]]
            assert len(ids)<=5
            return {'requirement_findings':[{'requirement_id':id_,'verdict':'met','fulfillment':'complete',
                                            'reason':'Required result and check are visible.','evidence_ids':['F00']} for id_ in ids]}
    c=Client();errors=[]
    dims,_,findings=assess_teaching(c,[],['task_completeness'],{'F00'},{'F00'},'a',tmp_path,errors,contract)
    assert c.calls==4 and not errors and len(findings)==12
    assert dims['task_completeness']['score']==50


@pytest.mark.parametrize('backend',['unified','native','code2video'])
def test_known_bad_public_outline_stops_before_any_generation_request(tmp_path,backend):
    case={'id':'a','prompt_text':"Derive Snell: v1*sin(theta1)=v2*sin(theta2).",'target_duration_s':60}
    class Forbidden:
        def chat(self,*a,**k):pytest.fail('bad reference reached a model call')
    if backend=='unified':
        from localbench.pipeline import generate_one
        fn=lambda:generate_one(case,tmp_path,Forbidden(),['code'])
    elif backend=='native':
        from localbench.native_pipeline import generate_native
        fn=lambda:generate_native(case,tmp_path,Forbidden(),None,None)
    else:
        from localbench.code2video import generate_code2video
        fn=lambda:generate_code2video(case,tmp_path,Forbidden(),{},None)
    with pytest.raises(ValueError,match='scientific conflict'):fn()
    assert not list(tmp_path.iterdir())


def test_caption_patch_actual_encoder_copies_audio_and_keeps_duration(tmp_path):
    import wave
    import numpy as np
    from localbench.pipeline import encode
    from localbench.rerender import decoded_audio_hash
    case={'id':'a','prompt_text':'Explain the step.','target_duration_s':16}
    p=scene_plan();directory=tmp_path/'source';directory.mkdir()
    wave_path=directory/'fixture.wav'
    with wave.open(str(wave_path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
        t=np.arange(16*24000)/24000
        wav.writeframes((np.sin(2*np.pi*440*t)*1000).astype('<i2').tobytes())
    write_json(directory/'plan.json',p)
    artifact=encode(p,directory,wave_path,mode='code')
    source={'id':'a','public_input_hash':digest(public_case(case)),'artifacts':[artifact]}
    patch={'case_id':'a','video_sha256':artifact['sha256'],'plan_sha256':digest(p),
           'replacements':[{'scene':1,'field':'caption','old_text':'Old caption.','new_text':'Only this caption changes.'}]}
    result=repair(case,source,patch,tmp_path/'candidate')
    assert result['status']=='rendered'
    new=result['artifacts'][0]
    assert new['frame_count']==artifact['frame_count']
    assert new['duration_s']==artifact['duration_s']
    assert decoded_audio_hash(new['video_path'])==decoded_audio_hash(artifact['video_path'])
    assert file_hash(artifact['video_path'])==patch['video_sha256']


def test_mutated_source_plan_cannot_be_rebound_by_updating_only_the_patch_hash(tmp_path):
    case,source,patch,plan,video=bound(tmp_path)
    plan['scenes'][0]['caption']='Unrecorded source change.'
    write_json(video.parent/'plan.json',plan)
    patch['plan_sha256']=digest(plan)
    with pytest.raises(ValueError,match='generation plan/renderer receipt'):
        repair(case,source,patch,tmp_path/'candidate')
