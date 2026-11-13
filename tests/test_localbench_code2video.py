import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from localbench import code2video, code2video_runtime as runtime, code2video_source as source
from localbench.common import write_json


def source_fixture(tmp_path, monkeypatch):
    root = tmp_path/'upstream'; root.mkdir()
    target = root/'src/agent.py'; target.parent.mkdir(); target.write_text('class TeachingVideoAgent: pass\n')
    lock = {'repository': 'https://github.com/showlab/Code2Video', 'commit': 'fixed',
            'files': {'src/agent.py': hashlib.sha256(target.read_bytes()).hexdigest()}}
    monkeypatch.setattr(source, 'source_lock', lambda: lock)
    return root, target


def test_source_rejects_missing_modified_and_symlink_files(tmp_path, monkeypatch):
    root, target = source_fixture(tmp_path, monkeypatch)
    assert source.verify_source(root)['commit'] == 'fixed'
    original = target.read_bytes()
    target.write_text('changed')
    with pytest.raises(ValueError, match='source missing or changed'): source.verify_source(root)
    target.unlink()
    with pytest.raises(ValueError): source.verify_source(root)
    external = tmp_path/'other.py'; external.write_bytes(original); target.symlink_to(external)
    with pytest.raises(ValueError): source.verify_source(root)


def test_configuration_records_fixed_source_and_image_identity(tmp_path, monkeypatch):
    root, _ = source_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime, 'inspect_image', lambda image: 'sha256:'+'a'*64)
    cfg = runtime.settings_from({'source_dir': 'upstream'}, tmp_path)
    assert cfg['upstream']['source_dir'] == str(root)
    assert cfg['docker_image_id'] == 'sha256:'+'a'*64
    assert cfg['feedback_rounds'] == 2 and cfg['critic_model_policy'] == 'same_as_generator'


@pytest.mark.parametrize('option,value', [('feedback_rounds',0), ('critic_frames',True),
    ('max_code_tokens',-2), ('max_fix_attempts',11), ('max_regenerate_attempts','3'),
    ('max_feedback_attempts',None), ('render_timeout_s',0), ('docker_image','x; touch /tmp/x')])
def test_invalid_runtime_settings_fail_before_image_inspection(tmp_path, monkeypatch, option, value):
    root, _ = source_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime, 'inspect_image', lambda _: pytest.fail('invalid settings reached Docker'))
    with pytest.raises(ValueError): runtime.settings_from({'source_dir': str(root), option:value}, tmp_path)


def test_missing_docker_never_calls_models(monkeypatch):
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: None)
    with pytest.raises(ValueError, match='needs Docker'): runtime.inspect_image(runtime.DEFAULT_IMAGE)


def renderer(tmp_path):
    return runtime.DockerRenderer(tmp_path, {'docker_image_id': 'sha256:'+'a'*64, 'render_timeout_s': 180})


def test_generated_python_runs_only_inside_network_disabled_container(tmp_path, monkeypatch):
    calls = []; monkeypatch.setenv('VIDEO_TEACHER_API_KEY', 'MUST_NOT_PASS_TO_CONTAINER')
    def run(args, **kw):
        calls.append((args,kw)); return subprocess.CompletedProcess(args, 0, 'ok', '')
    monkeypatch.setattr(runtime.subprocess, 'run', run)
    r = renderer(tmp_path)
    r.run(['python','-c','print(1)'], cwd=tmp_path, timeout=10)
    args = calls[0][0]
    assert args[:2] == ['docker','run'] and args[args.index('--network')+1] == 'none'
    assert '--read-only' in args and '--cap-drop' in args
    assert args[args.index('-v')+1] == str(tmp_path)+':/work:rw'
    assert 'MUST_NOT_PASS' not in json.dumps(calls)
    assert args[args.index('--entrypoint')+1] == 'python'
    with pytest.raises(ValueError): r.run(['bash','-c','true'], cwd=tmp_path, timeout=10)
    with pytest.raises(ValueError): r.run(['python','-c','print(1)'], cwd=tmp_path.parent, timeout=10)


def test_timeout_removes_container(tmp_path, monkeypatch):
    calls = []
    def run(args, **kw):
        calls.append(args)
        if args[1] == 'run': raise subprocess.TimeoutExpired(args,kw['timeout'])
        return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr(runtime.subprocess,'run',run)
    with pytest.raises(subprocess.TimeoutExpired): renderer(tmp_path).run(['python','-c','1'],cwd=tmp_path,timeout=10)
    assert calls[1][:3] == ['docker','rm','-f']
    assert calls[1][3] == calls[0][calls[0].index('--name')+1]


def test_wrong_duration_becomes_repair_feedback_and_stale_media_is_removed(tmp_path, monkeypatch):
    output=tmp_path/'media/videos/section_1/480p15/Section1Scene.mp4'
    output.parent.mkdir(parents=True); output.write_bytes(b'stale')
    def run(args, **kw):
        assert not output.exists()
        output.write_bytes(b'fresh')
        return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr(runtime.subprocess,'run',run)
    monkeypatch.setattr(runtime,'metadata',lambda path: {'duration': 3})
    r=renderer(tmp_path);r.durations['section_1']=15
    result=r.run(['manim','-ql','section_1.py','Section1Scene'],cwd=tmp_path,timeout=180)
    assert result.returncode == 1 and 'duration must be' in result.stderr
    assert json.loads((tmp_path/'render_logs/0001.json').read_text())['returncode']==1


def storyboard():
    rows=[{'id':f'section_{i+1}','title':'Part','lecture_lines':['Short bullet'],
           'animations':['Show the concept'],'duration_s':15,
           'narration':'Explain this relationship clearly with a concrete example.'} for i in range(4)]
    return SimpleNamespace(sections=[SimpleNamespace(**r) for r in rows],enhanced_storyboard={'sections':rows})


@pytest.mark.parametrize('invalid',['id','duplicate','count','narration','animations'])
def test_storyboard_rejects_unsafe_paths_or_incomplete_delivery(invalid):
    agent=storyboard()
    if invalid=='id':agent.sections[0].id='../escape'
    elif invalid=='duplicate':agent.sections[1].id=agent.sections[0].id
    elif invalid=='count':agent.sections.pop()
    elif invalid=='narration':agent.enhanced_storyboard['sections'][0]['narration']=''
    else:agent.sections[0].animations=[]
    with pytest.raises(ValueError):code2video.storyboard_plan(agent,{'id':'a','target_duration_s':60})


def test_narration_plan_preserves_public_target_and_order():
    plan=code2video.storyboard_plan(storyboard(),{'id':'a','target_duration_s':60})
    assert len(plan['scenes'])==4 and sum(s['duration_s'] for s in plan['scenes'])==60


def test_assembly_preserves_all_sections_in_original_order_and_no_time_stretch(tmp_path,monkeypatch):
    agent=storyboard();agent.section_videos={}
    for section in reversed(agent.sections):
        path=tmp_path/(section.id+'.mp4');path.write_bytes(b'fixture');agent.section_videos[section.id]=str(path)
    plan=code2video.storyboard_plan(agent,{'id':'a','target_duration_s':60});calls=[]
    def command(args):calls.append(args);Path(args[-1]).write_bytes(b'media')
    monkeypatch.setattr(code2video,'run_command',command)
    monkeypatch.setattr(code2video,'metadata',lambda path,**kw:
        {'duration':60 if Path(path).name=='code2video.mp4' else 15,'frame_count':900,'fps':15,'size':[854,480]})
    artifact=code2video.assemble(agent,plan,tmp_path/'audio.wav',tmp_path)
    assert artifact['complete'] and artifact['mode']=='code2video'
    concat=(tmp_path/'section_concat.txt').read_text()
    assert concat.index('section_1')<concat.index('section_2')<concat.index('section_3')<concat.index('section_4')
    assert all('-shortest' not in c and '-t' not in c and '-vf' not in c for c in calls)


def test_source_loader_does_not_import_provider_cli_or_host_manim(tmp_path,monkeypatch):
    root=tmp_path/'upstream'
    contents={
        'prompts/base_class.py':"base_class='base'\n",
        **{f'prompts/stage{i}.py':f'def stage{i}(): return {i}\n' for i in range(1,5)},
        'src/utils.py':'from manim import *\nimport unavailable_provider\ndef extract_answer_from_response(x): return x\n',
        'src/scope_refine.py':'class ScopeRefineFixer: pass\n',
        'src/agent.py':'from unavailable_provider import *\nfrom prompts import *\nclass TeachingVideoAgent: pass\nraise RuntimeError("CLI executed")\n'}
    for name,content in contents.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    lock={'files':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in contents.items()}}
    monkeypatch.setattr(source,'source_lock',lambda:lock)
    ns1=source.load_definitions(root);ns2=source.load_definitions(root)
    assert ns1['TeachingVideoAgent'] is not ns2['TeachingVideoAgent']
    assert ns1['extract_answer_from_response']('text')=='text' and ns1['stage4']()==4


def test_code2video_cli_keeps_failed_case_in_denominator(tmp_path,monkeypatch):
    import sys
    from localbench import run, judge
    from localbench.common import digest, public_case
    from localbench.provenance import file_hash
    rows=[{'id':id_,'prompt_text':'Explain the diagram.','target_duration_s':60} for id_ in ('a','b')]
    data=tmp_path/'tasks.jsonl';data.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    config=tmp_path/'config.json';write_json(config,{'generator':{'model':'fixture','url':'https://example.test/v1','api_key':'fixture'},'audio_judge':False})
    monkeypatch.setattr(runtime,'settings_from',lambda *a:{'upstream':{'commit':'fixed'}})
    monkeypatch.setattr(run,'resolve_tts',lambda *a:{'backend':'fixture'})
    def generate(case,out,*a):
        if case['id']=='b':raise ValueError('critic incomplete')
        p=out/'a/video.mp4';p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
        return {'id':'a','status':'rendered','public_input_hash':digest(public_case(case)),
                'framework':'official_code2video_adapted','artifacts':[
                    {'complete':True,'mode':'code2video','video_path':str(p),'sha256':file_hash(p)}]}
    monkeypatch.setattr(code2video,'generate_code2video',generate)
    monkeypatch.setattr(judge,'evaluate',lambda video,case,*a,**kw:{'case_id':case['id'],'scoring':{'overall':75}})
    argv=['teacher.py','bench','--framework','code2video','--config',str(config),'--data',str(data),'--num','2','--out',str(tmp_path/'run')]
    monkeypatch.setattr(sys,'argv',argv)
    assert run.main()==2
    report=json.loads((tmp_path/'run/summary.json').read_text())
    assert report['planned_cases']==2 and report['delivered_cases']==report['scored_cases']==1
    assert report['all_cases_mean'] is None
    failed=next(r for r in report['cases'] if r['id']=='b')
    assert failed['framework']=='official_code2video_adapted' and failed['overall'] is None


@pytest.mark.parametrize('command,backend',[('method','code'),('bench','video')])
def test_framework_rejects_incompatible_route_before_runtime(tmp_path,monkeypatch,command,backend):
    import sys
    from localbench import run
    config=tmp_path/'config.json';write_json(config,{'generator':{'model':'fixture','url':'https://example.test/v1','api_key':'fixture'},'audio_judge':False})
    data=tmp_path/'tasks.jsonl';data.write_text(json.dumps({'id':'a','prompt_text':'Explain.'})+'\n')
    monkeypatch.setattr(runtime,'settings_from',lambda *a:pytest.fail('invalid route reached runtime'))
    monkeypatch.setattr(sys,'argv',['teacher.py',command,'--backend',backend,'--framework','code2video','--config',str(config),'--data',str(data),'--num','1'])
    assert run.main()==2


def test_installer_pins_downloads_and_refuses_changed_files(tmp_path,monkeypatch):
    import io
    from scripts import setup_code2video as setup
    content=b'class TeachingVideoAgent: pass\n';calls=[]
    lock={'commit':'fixed','files':{'src/agent.py':hashlib.sha256(content).hexdigest()}}
    monkeypatch.setattr(setup,'source_lock',lambda:lock)
    monkeypatch.setattr(source,'source_lock',lambda:lock)
    def download(url,**kw):calls.append(url);return io.BytesIO(content)
    monkeypatch.setattr(setup.urllib.request,'urlopen',download)
    destination=tmp_path/'download'
    assert setup.setup(destination)==destination and len(calls)==1
    assert '/fixed/src/agent.py' in calls[0]
    setup.setup(destination);assert len(calls)==1
    (destination/'src/agent.py').write_text('changed')
    with pytest.raises(ValueError,match='refusing overwrite'):setup.setup(destination)
