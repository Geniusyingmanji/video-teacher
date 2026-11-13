import copy
import json

import numpy as np
import pytest

from localbench.object_connections import closest_point,compile_connections,pixel,propose


def fixture():
    primitives=[
        {'type':'polyline','x':0,'y':0,'points':[[.1,.3],[.2,.25],[.3,.3]],'closed':False},
        {'type':'polyline','x':0,'y':0,'points':[[.1,.7],[.2,.65],[.3,.7]],'closed':False},
        {'type':'circle','x':.7,'y':.5,'r':.08},
        {'type':'line','x':.3,'y':.3,'x2':.5,'y2':.35,'color':'red'},
        {'type':'line','x':.5,'y':.65,'x2':.3,'y2':.7,'color':'red'},
        {'type':'text','x':.4,'y':.3,'text':'S-S','font_size':24,'align':'center'},
        {'type':'text','x':.4,'y':.7,'text':'S-S','font_size':24,'align':'center'},
        {'type':'text','x':.2,'y':.2,'text':'A','font_size':24,'align':'center'}]
    plan={'scenes':[{'title':'Three chains','narration':'A connects to C; C connects to B.',
                    'caption':'Two bridges','duration_s':10,'primitives':primitives}]}
    case={'id':'x','prompt_text':'Connect A to C and C to B; preserve the three backbones.'}
    raw={'connections':[{'scene':0,'connector':3,'source_shape':0,'target_shape':2,'label':5,
                         'prompt_quote':'Connect A to C','reason':'First bridge A to C'},
                        {'scene':0,'connector':4,'source_shape':2,'target_shape':1,'label':6,
                         'prompt_quote':'C to B','reason':'Second bridge C to B'}]}
    return plan,case,raw


def test_circle_attachment_uses_painted_radius_not_rectangular_corner():
    circle={'type':'circle','x':.5,'y':.5,'r':.1}
    center=pixel(.5,.5);p=closest_point(circle,center+[100,100])
    assert np.linalg.norm(p-center)==pytest.approx(30.2)
    assert np.allclose(p-center,np.array([30.2,30.2])/np.sqrt(2))


def test_polyline_support_is_the_stroke_not_bbox_and_closing_edge_is_real():
    p={'type':'polyline','points':[[0,0],[1,0],[1,1]],'closed':False}
    q=pixel(.4,.5);open_point=closest_point(p,q)
    assert not np.allclose(open_point,q)
    closed=closest_point({**p,'closed':True},q)
    assert np.linalg.norm(closed-q)<np.linalg.norm(open_point-q)
    assert abs((closed[0]-64)/896-(closed[1]-112)/302)<1e-9


def test_both_bridges_touch_actual_owners_preserving_backbones_and_text():
    plan,case,raw=fixture();saved=copy.deepcopy(plan)
    result,receipt=compile_connections(raw,plan,case)
    assert plan==saved and receipt['status']=='changed'
    assert receipt['semantic_binding']=='model_proposed_unverified'
    for i in [0,1,2,7]:assert result['scenes'][0]['primitives'][i]==plan['scenes'][0]['primitives'][i]
    for field in ['title','narration','caption','duration_s']:
        assert result['scenes'][0][field]==plan['scenes'][0][field]
    for record in receipt['connections']:
        assert max(record['on_support_error_px'])<1e-6
    for i in [5,6]:
        assert result['scenes'][0]['primitives'][i]['text']=='S-S'
        assert result['scenes'][0]['primitives'][i]['font_size']==24
    assert len(result['scenes'][0]['primitives'])==len(plan['scenes'][0]['primitives'])


def test_rejects_dynamic_owner_and_fabricated_public_quote():
    plan,case,raw=fixture();plan['scenes'][0]['primitives'][2]['dx']=.1
    with pytest.raises(ValueError,match='static'):compile_connections(raw,plan,case)
    plan,case,raw=fixture();raw['connections'][0]['prompt_quote']='A private answer'
    with pytest.raises(ValueError,match='public-task'):compile_connections(raw,plan,case)


def test_connector_cannot_be_its_own_or_another_connectors_anchor():
    plan,case,raw=fixture();raw['connections'][0]['target_shape']=4
    with pytest.raises(ValueError,match='anchor owner'):compile_connections(raw,plan,case)


def test_empty_binding_preserves_everything_and_is_not_successful_repair():
    plan,case,_=fixture();result,receipt=compile_connections({'connections':[]},plan,case)
    assert result==plan and receipt['status']=='no_change' and not receipt['connections']


def test_proposal_does_not_send_private_answers_or_frozen_questions(tmp_path):
    plan,case,_=fixture();case.update(expected_concepts=['PRIVATE_REFERENCE_SENTINEL'],question_pool={'Q1':'PRIVATE_QUESTION'})
    class Client:
        def chat(self,messages,**kwargs):
            text=json.dumps(messages)
            assert 'PRIVATE_REFERENCE_SENTINEL' not in text and 'PRIVATE_QUESTION' not in text
            assert 'primitive_index' in text
            return {'connections':[]}
    result,receipt=propose(Client(),plan,case,[],tmp_path/'proposal')
    assert result==plan and receipt['status']=='no_change'


@pytest.mark.parametrize('outcome',['changed','binding_mismatch','audio_mismatch','no_change','protected'])
def test_final_stage_uses_current_artifact_and_preserves_it_on_failure(monkeypatch,tmp_path,outcome):
    from localbench import artifact_plan,pipeline,rerender,visual_agent
    from localbench.object_connections import repair
    from localbench.scene import validate_plan
    plan,case,raw=fixture()
    plan['case_id']=case['id'];plan['scenes']=[copy.deepcopy(plan['scenes'][0]) for _ in range(4)]
    case['target_duration_s']=40;validate_plan(plan,case)
    if outcome=='protected':plan['scenes'][0]['state_visual']={}
    incoming={'mode':'code','complete':True,'video_path':'retained-stage.mp4','sha256':'current'}
    oldest={'mode':'code','video_path':'first-baseline.mp4'}
    after={'mode':'code','complete':True,'video_path':'connected.mp4','sha256':'new'}
    result={'artifacts':[incoming],'original_artifacts':[oldest]};before=copy.deepcopy(result)
    calls=[]
    def load(a):
        assert a==incoming;calls.append('load');return copy.deepcopy(plan),{}
    def verify(a,p,out):
        assert a==incoming;calls.append('verify')
        return {'status':'mismatch' if outcome=='binding_mismatch' else 'verified'}
    monkeypatch.setattr(artifact_plan,'load',load);monkeypatch.setattr(artifact_plan,'verify',verify)
    monkeypatch.setattr(visual_agent,'evidence',lambda *a,**kw:[])
    def encode(p,out,audio,**kw):
        assert audio==incoming['video_path'] and kw['copy_audio']
        assert p['scenes'][0]['primitives'][2]==plan['scenes'][0]['primitives'][2]
        calls.append('encode');return after
    monkeypatch.setattr(pipeline,'encode',encode)
    monkeypatch.setattr(rerender,'decoded_audio_hash',lambda p:p if outcome=='audio_mismatch' else 'same')
    class Client:
        def chat(self,*args,**kwargs):
            if kwargs['purpose'].startswith('connection_instances:'):
                return {'groups':[{'id':f'G{i}','include':[0],
                    'exclude':[{'scene':s,'reason':'Fixture isolates only the first scene'} for s in [1,2,3]],
                    'reason':'The initial scene depicts the attached relation'} for i in range(2)]}
            calls.append('model');return {'connections':[]} if outcome=='no_change' else raw
    repaired=repair(case,result,tmp_path/'stage',Client());state=repaired['object_connections_repair']
    assert result==before
    if outcome=='changed':
        assert repaired['artifacts']==[after] and repaired['pre_connection_artifacts']==[incoming]
        assert repaired['original_artifacts']==[oldest] and state['decoded_audio_identical']
        assert calls==['load','verify','model','encode']
    else:
        assert repaired['artifacts']==[incoming]
        if outcome in ('audio_mismatch','binding_mismatch'):assert state['status']=='failed_current_artifact_retained'
        if outcome in ('protected','binding_mismatch'):assert 'model' not in calls
        if outcome=='no_change':assert 'encode' not in calls and state['status']=='no_change'


def test_object_connection_flag_rejects_strings_before_services(tmp_path):
    from types import SimpleNamespace
    from localbench.run import execute
    config=tmp_path/'config.json';config.write_text(json.dumps({'method_object_connections':'true'}))
    with pytest.raises(ValueError,match='method_object_connections must be a boolean'):
        execute(SimpleNamespace(command='method',config=config))


@pytest.mark.parametrize('enabled,no_repair,expected',[(True,False,['generate','improve','connect','evaluate']),
    (False,False,['generate','improve','evaluate']),(True,True,['generate','evaluate'])])
def test_cli_connection_stage_follows_ordinary_repair_and_reaches_evaluation(monkeypatch,tmp_path,enabled,no_repair,expected):
    from argparse import Namespace
    from localbench import run,judge,object_connections
    from localbench.common import digest,public_case,write_json
    from localbench.provenance import file_hash
    from localbench.rubric import DIMENSIONS,aggregate_dimensions
    case={'id':'x','prompt_text':'Connect the objects.','target_duration_s':40}
    data=tmp_path/'cases.jsonl';data.write_text(json.dumps(case)+'\n')
    config=tmp_path/'services.json';config.write_text(json.dumps({'generator':{'model':'fixture','url':'https://example.test/v1','api_key':'fixture'},'audio_judge':False,'method_object_connections':enabled}))
    calls=[]
    def generate(c,out,*a,**kw):
        calls.append('generate');p=out/c['id']/'code.mp4';p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
        return {'id':c['id'],'status':'rendered','public_input_hash':digest(public_case(c)),
                'artifacts':[{'complete':True,'mode':'code','video_path':str(p),'sha256':file_hash(p)}]}
    def improve(c,r,*a,**kw):calls.append('improve');return {**r,'ordinary_repaired':True}
    def connect(c,r,*a,**kw):
        assert r['ordinary_repaired'];calls.append('connect');return {**r,'object_connections_repair':{'status':'fixture'}}
    def evaluate(video,c,out,*a,**kw):
        calls.append('evaluate');r={'case_id':c['id'],'video_sha256':file_hash(video),'case_hash':digest(c),
             'scoring':aggregate_dimensions({k:{'score':80} for k in DIMENSIONS})}
        write_json(out/'scores.json',r);return r
    monkeypatch.setattr(run,'generate_one',generate);monkeypatch.setattr(run,'improve',improve)
    monkeypatch.setattr(object_connections,'repair',connect);monkeypatch.setattr(judge,'evaluate',evaluate)
    monkeypatch.setattr(run,'resolve_tts',lambda x:{'backend':'fixture'})
    args=Namespace(command='method',config=config,model=None,url=None,api_key_env=None,data=data,ids=['x'],suite='all',backend='code',
        out=tmp_path/'run',resume=False,manifest=None,api_workers=1,render_workers=1,eval_workers=1,max_calls=5,max_tokens=10000,no_repair=no_repair)
    assert run.execute(args)==0 and calls==expected
    public=json.loads((args.out/'run_config.json').read_text())
    assert public.get('method_object_connections',False)==enabled
