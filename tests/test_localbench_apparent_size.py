import copy
import json
from argparse import Namespace

import numpy as np
import pytest

from localbench.apparent_size import compile_orders,object_geometry,propose,repair


def setup():
    ps=[{'type':'line','x':.15,'y':.8,'x2':.15,'y2':.75,'color':'green'},
        {'type':'line','x':.3,'y':.6,'x2':.3,'y2':.5,'color':'green'},
        {'type':'text','x':.5,'y':.1,'text':'Trees','font_size':24}]
    s={'title':'Perspective','caption':'Smaller farther away','narration':'Compare these two trees near and far.',
       'duration_s':10,'primitives':ps,'arithmetic_checks':[]}
    plan={'case_id':'x','scenes':[copy.deepcopy(s) for _ in range(4)]}
    case={'id':'x','prompt_text':'Show size shrinking with distance.','target_duration_s':40}
    raw={'orders':[{'scene':0,'objects':[[0],[1]],'prompt_quote':'size shrinking with distance','reason':'These comparable trees are ordered near to far.'}]}
    return plan,case,raw


def test_reorders_existing_heights_preserving_anchors_text_and_timing():
    plan,case,raw=setup();source=copy.deepcopy(plan)
    candidate,receipt=compile_orders(raw,plan,case)
    assert plan==source and receipt['status']=='changed'
    a,b=candidate['scenes'][0]['primitives'][:2]
    assert a['y']==pytest.approx(.8) and b['y']==pytest.approx(.6)
    assert a['x']==.15 and b['x']==.3
    assert a['y']-a['y2']==pytest.approx(.1)
    assert b['y']-b['y2']==pytest.approx(.05)
    assert candidate['scenes'][1:]==plan['scenes'][1:]
    for k,v in plan['scenes'][0].items():
        if k!='primitives':assert candidate['scenes'][0][k]==v
    assert candidate['scenes'][0]['primitives'][2]==plan['scenes'][0]['primitives'][2]


def test_compound_object_scales_all_its_shapes_about_same_bottom_anchor():
    plan,case,raw=setup()
    ps=plan['scenes'][0]['primitives']
    ps[0]={'type':'rect','x':.1,'y':.7,'w':.03,'h':.1}
    ps[1]={'type':'rect','x':.3,'y':.4,'w':.06,'h':.2}
    ps += [{'type':'circle','x':.115,'y':.67,'r':.03},
           {'type':'polyline','x':.33,'y':.4,'points':[[.3,.4],[.33,.34],[.36,.4]],'closed':False}]
    raw['orders'][0]['objects']=[[0,3],[1,4]]
    before=[object_geometry(ps,g) for g in raw['orders'][0]['objects']]
    candidate,r=compile_orders(raw,plan,case);after=candidate['scenes'][0]['primitives']
    measured=[object_geometry(after,g) for g in raw['orders'][0]['objects']]
    assert measured[0][0]>measured[1][0]
    for old,new in zip(before,measured):assert np.allclose(old[1],new[1])
    assert after[0]['w']/ps[0]['w']==pytest.approx(after[3]['r']/ps[3]['r'])
    assert after[1]['w']/ps[1]['w']==pytest.approx((after[4]['points'][2][0]-after[4]['points'][0][0])/.06)


@pytest.mark.parametrize('kind',['dynamic','shared','private_quote','text'])
def test_rejects_unsupported_or_ambiguous_bindings(kind):
    plan,case,raw=setup()
    if kind=='dynamic':plan['scenes'][0]['primitives'][0]['dx']=.1
    elif kind=='shared':raw['orders'][0]['objects']=[[0],[0,1]]
    elif kind=='private_quote':raw['orders'][0]['prompt_quote']='PRIVATE_REFERENCE'
    else:raw['orders'][0]['objects']=[[0],[2]]
    with pytest.raises(ValueError):compile_orders(raw,plan,case)


def test_ties_are_reported_without_inventing_new_sizes_and_ordered_is_noop():
    plan,case,raw=setup();plan['scenes'][0]['primitives'][0]['y2']=.7
    candidate,r=compile_orders(raw,plan,case)
    assert candidate==plan and r['orders'][0]['status']=='insufficient_existing_size_difference'
    plan['scenes'][0]['primitives'][0]['y2']=.6
    candidate,r=compile_orders(raw,plan,case)
    assert candidate==plan and r['orders'][0]['status']=='already_ordered'


def test_model_input_excludes_private_answers(tmp_path):
    plan,case,raw=setup();case['expected_concepts']=['PRIVATE_REFERENCE']
    plan['scenes'][0]['primitives'].append({'type':'line','x':.1,'y':.2,'x2':.9,'y2':.2})
    class Client:
        def chat(self,msg,**kwargs):
            assert 'PRIVATE_REFERENCE' not in json.dumps(msg)
            return {'orders':[{k:v for k,v in raw['orders'][0].items() if k!='prompt_quote'}|{'axis':'height','reference_line':3,'requirement_id':'P0'}]}
    _,receipt=propose(Client(),plan,case,[],tmp_path)
    assert receipt['status']=='changed'


def test_horizontal_extent_can_be_ordered_without_inventing_height():
    plan,case,raw=setup();ps=plan['scenes'][0]['primitives']
    ps[0]={'type':'line','x':.4,'y':.8,'x2':.6,'y2':.8}
    ps[1]={'type':'line','x':.3,'y':.6,'x2':.7,'y2':.6}
    raw['orders'][0]['axis']='width'
    candidate,r=compile_orders(raw,plan,case)
    a,b=candidate['scenes'][0]['primitives'][:2]
    assert a['y']==a['y2']==.8 and b['y']==b['y2']==.6
    assert a['x2']-a['x']==pytest.approx(.4)
    assert b['x2']-b['x']==pytest.approx(.2)
    assert r['orders'][0]['axis']=='width'
    ordered,_=compile_orders(raw,candidate,case)
    assert ordered==candidate


def test_depth_is_derived_from_horizon_even_if_model_lists_objects_backwards():
    plan,case,raw=setup();plan['scenes'][0]['primitives'].append({'type':'line','x':.1,'y':.2,'x2':.9,'y2':.2})
    raw['orders'][0].update(reference_line=3,objects=[[1],[0]])
    candidate,r=compile_orders(raw,plan,case)
    order=r['orders'][0]
    assert order['objects']==[[0],[1]] and order['depth_order']['derived_indices']==[1,0]
    assert order['after_extents_px'][0]>order['after_extents_px'][1]
    assert candidate['scenes'][0]['primitives'][3]==plan['scenes'][0]['primitives'][3]


@pytest.mark.parametrize('horizon',[{'type':'line','x':.1,'y':.9,'x2':.9,'y2':.9},
    {'type':'line','x':.1,'y':.2,'x2':.9,'y2':.3}])
def test_incompatible_ground_plane_reference_is_rejected(horizon):
    plan,case,raw=setup();plan['scenes'][0]['primitives'].append(horizon);raw['orders'][0]['reference_line']=3
    with pytest.raises(ValueError):compile_orders(raw,plan,case)


def test_same_depth_left_right_objects_share_a_layer_instead_of_being_rejected():
    plan,case,raw=setup();ps=plan['scenes'][0]['primitives']
    ps.extend([{**ps[0],'x':.85,'x2':.85},{**ps[1],'x':.7,'x2':.7},
               {'type':'line','x':.1,'y':.2,'x2':.9,'y2':.2}])
    raw['orders'][0].update(reference_line=5,objects=[[0],[1],[3],[4]])
    candidate,r=compile_orders(raw,plan,case);record=r['orders'][0]
    assert record['objects']==[[0],[3],[1],[4]]
    assert record['depth_order']['depth_layers_in_derived_order']==[[0,1],[2,3]]
    assert record['after_extents_px'][0]==pytest.approx(record['after_extents_px'][1])
    assert record['after_extents_px'][2]==pytest.approx(record['after_extents_px'][3])
    assert record['after_extents_px'][0]>record['after_extents_px'][2]
    assert candidate['scenes'][0]['primitives'][5]==ps[5]


@pytest.mark.parametrize('flag',['method_apparent_size','evaluation_transcript_guard'])
def test_flags_must_be_boolean_before_any_service(tmp_path,flag):
    from localbench.run import execute
    p=tmp_path/'config.json';p.write_text(json.dumps({flag:'true'}))
    with pytest.raises(ValueError,match=flag+' must be a boolean'):execute(Namespace(command='method',config=p))


def test_full_cli_orders_size_before_connections_and_enables_transcript_guard(monkeypatch,tmp_path):
    from localbench import run,judge,apparent_size,object_connections
    from localbench.common import digest,public_case,write_json
    from localbench.provenance import file_hash
    from localbench.rubric import DIMENSIONS,aggregate_dimensions
    _,case,_=setup();data=tmp_path/'cases.jsonl';data.write_text(json.dumps(case)+'\n')
    cfg=tmp_path/'services.json';cfg.write_text(json.dumps({'generator':{'model':'fixture','url':'https://example.test/v1','api_key':'fixture'},
        'audio_judge':False,'method_apparent_size':True,'method_object_connections':True,'evaluation_transcript_guard':True}))
    calls=[]
    def generate(c,out,*a,**kw):
        calls.append('generate');p=out/c['id']/'code.mp4';p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
        return {'id':c['id'],'status':'rendered','public_input_hash':digest(public_case(c)),
            'artifacts':[{'complete':True,'mode':'code','video_path':str(p),'sha256':file_hash(p)}]}
    def stage(name):
        def f(c,r,*a,**kw):calls.append(name);return r
        return f
    def evaluate(video,c,out,*a,**kw):
        assert kw['transcript_guard'] is True;calls.append('evaluate')
        r={'case_id':c['id'],'video_sha256':file_hash(video),'case_hash':digest(c),'scoring':aggregate_dimensions({k:{'score':80} for k in DIMENSIONS})}
        write_json(out/'scores.json',r);return r
    monkeypatch.setattr(run,'generate_one',generate);monkeypatch.setattr(run,'improve',stage('improve'))
    monkeypatch.setattr(apparent_size,'repair',stage('size'));monkeypatch.setattr(object_connections,'repair',stage('connect'))
    monkeypatch.setattr(judge,'evaluate',evaluate);monkeypatch.setattr(run,'resolve_tts',lambda x:{'backend':'fixture'})
    args=Namespace(command='method',config=cfg,model=None,url=None,api_key_env=None,data=data,ids=['x'],suite='all',backend='code',
        out=tmp_path/'run',resume=False,manifest=None,api_workers=1,render_workers=1,eval_workers=1,max_calls=5,max_tokens=10000,no_repair=False)
    assert run.execute(args)==0 and calls==['generate','improve','size','connect','evaluate']
    settings=json.loads((args.out/'run_config.json').read_text())
    assert settings['method_apparent_size'] and settings['evaluation_transcript_guard']


def test_repair_retains_latest_artifact_if_source_reconstruction_fails(monkeypatch,tmp_path):
    from localbench import artifact_plan
    plan,case,_=setup();artifact={'mode':'code','complete':True,'video_path':'latest.mp4'}
    result={'artifacts':[artifact]}
    monkeypatch.setattr(artifact_plan,'load',lambda a:(plan,{}))
    monkeypatch.setattr(artifact_plan,'verify',lambda *a:{'status':'mismatch'})
    class Client:
        def chat(self,*a,**kw):raise AssertionError('No model call allowed on unverified source')
    after=repair(case,result,tmp_path,Client())
    assert after['artifacts']==[artifact] and after['apparent_size_repair']['status']=='failed_current_artifact_retained'
