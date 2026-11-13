#!/usr/bin/env python3
"""Exercise real pinned upstream definitions with fixture models/media; no live APIs.

This is adapter validation, NOT a generated-video quality test or Docker/Manim
acceptance test. The outputs are synthetic fixtures and never benchmark results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from unittest.mock import patch
import wave

import imageio_ffmpeg
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from localbench import assets, code2video
from localbench.code2video_source import default_source_dir, verify_source
from localbench.common import write_json


def validate(source_dir, out):
    source = verify_source(source_dir)
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    fixture = out/'fixture.mp4'
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=854x480:r=15:d=15',
                    '-c:v', 'libx264', '-threads', '2', '-pix_fmt', 'yuv420p', str(fixture)], check=True)
    source_image = out/'public.png'; Image.new('RGB', (120,80),'red').save(source_image)
    case = {'id': 'offline_fixture', 'prompt_text': 'Explain how four stages connect using the given image.',
            'pedagogical_target_audience': 'high school', 'task_type': 'explanation',
            'target_duration_s': 60, 'audio_narration_required': True, 'narration_language': 'en',
            'source': {'dataset': 'GRADE', 'source_image_path': 'image/before/fixture.png'},
            'private_reference': 'PRIVATE_SENTINEL_NEVER_SEND'}
    settings = {'upstream': source, 'feedback_rounds':2, 'critic_frames':4, 'max_code_tokens':10000,
                'max_fix_attempts':3, 'max_regenerate_attempts':2, 'max_feedback_attempts':2}
    class Client:
        def __init__(self, fail_critic=False): self.calls=[];self.fail_critic=fail_critic
        def chat(self, messages, **kw):
            assert 'PRIVATE_SENTINEL' not in json.dumps(messages)
            self.calls.append(kw['purpose'])
            text = messages[0]['content'][0]['text']
            if ':critic_' in kw['purpose']:
                if self.fail_critic: raise RuntimeError('fixture critic unavailable')
                if sum(':critic_' in c for c in self.calls) == 1:
                    line=re.search(r'\|dot\|place_at_grid\|B2\|1\.0\|(\d+)\|',text)
                    assert line, 'official grid extraction did not find the generated object'
                    return {'layout': {'has_issues': True, 'improvements': [{
                        'problem':'Fixture layout move',
                        'solution':f"Line {line.group(1)}: self.place_at_grid(dot, 'C3', scale_factor=1.0)"}]}}
                return {'layout': {'has_issues': False, 'improvements': []}}
            assert len(messages[0]['content']) == 2, 'public image missing from planner/coder/repair'
            assert '/work/input_00.png' in text
            if 'As an outstanding instructional design expert' in text:
                assert 'around 1.0 minutes' in text
                return json.dumps({'topic':'Fixture','target_audience':'high school','sections':[
                    {'id':f'section_{i+1}','title':'Stage','content':'A relationship','example':'A diagram'} for i in range(4)]})
            if 'Storyboard Requirements' in text:
                return json.dumps({'sections':[{'id':f'section_{i+1}','title':'Stage',
                    'lecture_lines':['A relationship'],'animations':['Show a relationship'],
                    'duration_s':15,'narration':'Explain this relationship clearly with a concrete example.'} for i in range(4)]})
            match=re.search(r'class (Section\dScene)',text)
            scene=match.group(1) if match else 'Section1Scene'
            return (f'from manim import *\nclass {scene}(TeachingScene):\n    def construct(self):\n'
                    "        dot = Dot()\n        self.place_at_grid(dot, 'B2', scale_factor=1.0)\n        self.wait(15)\n")
    class Renderer:
        TimeoutExpired=subprocess.TimeoutExpired
        def __init__(self,directory,settings):self.directory=directory;self.durations={};self.failed_once=False
        def run(self,cmd,*,cwd,**kw):
            if cmd[0]=='python':return subprocess.CompletedProcess(cmd,0,'Syntax OK','')
            if cmd[2]=='section_1.py' and not self.failed_once:
                self.failed_once=True
                return subprocess.CompletedProcess(cmd,1,'',"NameError: name 'unknown_fixture' is not defined")
            path=Path(cwd)/'media/videos'/Path(cmd[2]).stem/'480p15'/(cmd[3]+'.mp4')
            path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(fixture,path)
            return subprocess.CompletedProcess(cmd,0,'','')
    def tts(plan,directory,**kw):
        for i,s in enumerate(plan['scenes']):
            p=directory/f'scene_{i:02d}/slot.wav';p.parent.mkdir(parents=True,exist_ok=True)
            with wave.open(str(p),'wb') as f:
                f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*int(s['duration_s']*24000))
        return directory/'fixture_audio.wav',None
    def forbidden(*a,**kw):raise AssertionError('offline validation attempted network')
    with patch.object(socket.socket,'connect',forbidden),patch.object(socket.socket,'connect_ex',forbidden), \
         patch.object(assets,'asset_path',lambda _:source_image),patch.object(code2video,'DockerRenderer',Renderer), \
         patch.object(code2video,'synthesize',tts):
        client=Client()
        result=code2video.generate_code2video(case,out/'success',client,settings,{'backend':'fixture'})
        assert result['status']=='rendered' and abs(result['artifacts'][0]['duration_s']-60)<.5
        assert sum(':critic_' in c for c in client.calls)==8
        # 1 outline + 1 storyboard + 4 code + at least one real ScopeRefine repair.
        assert sum(':request_' in c for c in client.calls)>=7
        assert "self.place_at_grid(dot, 'C3'" in (out/'success/offline_fixture/section_1.py').read_text()
        failing=Client(fail_critic=True)
        try:code2video.generate_code2video(case,out/'critic_failure',failing,settings,{'backend':'fixture'})
        except ValueError as exc:assert 'critic stage incomplete' in str(exc)
        else:raise AssertionError('critic failure was treated as success')
        status=json.loads((out/'critic_failure/offline_fixture/framework_status.json').read_text())
        assert len(status['critic_errors'])==8
    receipt={'passed':True,'upstream_commit':source['commit'],'source_hashes':source['files'],
             'real_upstream_components':['outline','storyboard','code','scope_refine','grid_critic_loop','grid_code_modifier'],
             'network_blocked':True,'model_calls':'fixtures only','renderer':'fixture clips, no generated Python executed',
             'tts':'silence fixtures','real_ffmpeg_assembly':True,'duration_s':result['artifacts'][0]['duration_s'],
             'not_validated':['live model API','Docker Manim rendering','teaching quality']}
    write_json(out/'validation.json',receipt)
    print(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,default=default_source_dir())
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();validate(a.source_dir,a.out)
