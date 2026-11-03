import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

from generation.lesson_spec import VERSION, CONTRACT_VERSION, duration_spec, validate_timeline
from generation.strict_video_contract import make_contract, outline_prompt, storyboard_prompt, code_prompt
from generation.strict_manim import inspect_exact, SourceFrameGuard
from generation.source_geometry import canvas_box
from scripts.build_lesson_prompts import revise
from eval.frame_extractor import extract_window
from eval import instructional_video as iv, task_completion


class LessonPipelineTests(unittest.TestCase):
    def case(self,duration=120):
        return {'id':'fixture','lesson_version':VERSION,'target_duration_s':duration,
                'prompt_text':'Solve 2x+5=17 visually. Keep both sides equal.'}

    def timeline(self,duration=120):
        return [{'id':f'step_{i}','start_s':i*duration/6,'end_s':(i+1)*duration/6,
                 'goal':f'explain step {i}','visible_evidence':f'equation state {i} changes on both sides','requirement_ids':['prompt']} for i in range(6)]

    def test_revision_preserves_exact_original_without_restoring_historical_task(self):
        original={'id':'a','prompt_text':'Create a five-second clip. Show 2x+5=17. Never change the givens.',
                  'original_prompt_text':'a different historical problem','expected_visual_elements':['x=6'],
                  'target_duration_s':5,'narrative_beats':[{'expected_frame_range':[1,8]}]}
        saved=copy.deepcopy(original);row=revise(original)
        self.assertEqual(original,saved)
        self.assertEqual(row['revision_provenance']['original_case'],saved)
        self.assertIn('Never change the givens.',row['prompt_text'])
        self.assertNotIn('five-second',row['prompt_text'])
        self.assertNotIn('different historical problem',row['prompt_text'])
        self.assertNotIn('narrative_beats',row)
        self.assertEqual(row['expected_visual_elements'][0],'x=6')
        physical={'id':'b','prompt_text':'Create a five-second teaching video. Measure the displacement after 5 seconds of motion.',
                  'target_duration_s':5}
        revised=revise(physical)
        self.assertIn('after 5 seconds of motion',revised['prompt_text'])
        self.assertNotIn('five-second teaching video',revised['prompt_text'])

    def test_all_400_revision_ids_original_obligations_and_durations(self):
        root=Path(__file__).resolve().parents[1]
        original=[json.loads(x) for x in (root/'data/prompts/candidate_400.jsonl').read_text().splitlines()]
        revised=[json.loads(x) for x in (root/'data/prompts/candidate_400_lessons_v1.jsonl').read_text().splitlines()]
        self.assertEqual(len(revised),400)
        self.assertEqual([r['id'] for r in original],[r['id'] for r in revised])
        for before,after in zip(original,revised):
            self.assertEqual(after,revise(before))
            self.assertIn(duration_spec(after)['duration_seconds'],(60,120,180))

    def test_prompts_and_contract_share_explicit_budget_and_chapters(self):
        from types import SimpleNamespace
        contract=make_contract(self.case())
        self.assertEqual(contract['version'],CONTRACT_VERSION)
        self.assertEqual(contract['frame_count'],1800)
        section=SimpleNamespace(id='section_1',animations=[],lecture_lines=[])
        for prompt in (outline_prompt(contract),storyboard_prompt(contract,{}),code_prompt(contract,section,'')):
            self.assertIn('120',prompt)
            self.assertIn('2x+5=17',prompt)
            self.assertNotIn('exactly FIVE SECONDS',prompt)
        self.assertIn('begin_teaching_step',code_prompt(contract,section,''))

    def test_bad_duration_and_gapped_or_incomplete_timeline_are_rejected(self):
        for duration in (True,float('nan'),0,29,181):
            with self.subTest(duration=duration),self.assertRaises(ValueError):duration_spec(self.case(duration))
        with self.assertRaises(ValueError):duration_spec({'target_duration_s':120})
        contract=make_contract(self.case())
        self.assertEqual(len(validate_timeline({'teaching_timeline':self.timeline()},contract)),6)
        for fault in ('gap','missing','duplicate'):
            timeline=self.timeline()
            if fault=='gap':timeline[2]['start_s']+=1
            if fault=='missing':timeline.pop()
            if fault=='duplicate':timeline[1]['id']=timeline[0]['id']
            with self.subTest(fault=fault),self.assertRaises(ValueError):validate_timeline({'teaching_timeline':timeline},contract)
        for fault in ('repeated_content','missing_requirement','wrong_requirement'):
            timeline=self.timeline()
            if fault=='repeated_content':timeline[1]['visible_evidence']=timeline[0]['visible_evidence']
            if fault=='missing_requirement':
                for row in timeline:row['requirement_ids']=[]
            if fault=='wrong_requirement':timeline[0]['requirement_ids']=['historical_task']
            with self.subTest(fault=fault),self.assertRaises(ValueError):validate_timeline({'teaching_timeline':timeline},contract)

    def test_later_failed_attempt_cannot_replace_an_earlier_usable_candidate(self):
        from scripts.run_qwen_multigpu import candidate_rank
        usable=({'complete':True,'quality_gate':{'passed':False}},{'scoring':{'valid':True,'score':35}},0)
        failed=({'complete':False,'quality_gate':{'passed':False}},{'scoring':{'valid':False,'score':None}},1)
        self.assertEqual(max([usable,failed],key=candidate_rank)[2],0)
        accepted=({'complete':True,'quality_gate':{'passed':True}},{'scoring':{'valid':True,'score':75}},2)
        self.assertEqual(max([usable,accepted],key=candidate_rank)[2],2)

    def test_reference_viewport_allows_teaching_panel_but_not_source_changes(self):
        self.assertEqual(canvas_box([0,0,200,100],(200,100),(400,400),[0,0,1,.5]),[0,0,1,.5])
        pixels=np.zeros((100,100,3),dtype=np.uint8)
        guard=SourceFrameGuard([],protected_viewport=[0,0,1,.6]);guard.check(pixels)
        pixels[80,50]=255;guard.check(pixels)
        self.assertTrue(guard.report()['valid'])
        pixels[30,50]=1;guard.check(pixels)
        self.assertFalse(guard.report()['valid'])

    def test_window_sampling_includes_final_frame_and_real_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.mp4'
            writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),15,(160,90))
            for i in range(450):writer.write(np.full((90,160,3),i%255,dtype=np.uint8))
            writer.release()
            frames,times=extract_window(path,20,30)
            self.assertEqual(len(frames),21)
            self.assertEqual(times[0],20)
            self.assertAlmostEqual(times[-1],449/15)
            self.assertTrue(inspect_exact(path,30)['valid'])
            self.assertFalse(inspect_exact(path,120)['valid'])

    def test_segment_citations_cannot_be_invented_or_borrowed_from_other_requirements(self):
        required=[{'id':'prompt','text':'Show both operations','kind':'instruction'}]
        segments=[{'id':0,'requirement_evidence':[{'id':'prompt','evidence_frames':[2,3]}]}]
        raw={'requirements':[{'id':'prompt','expected':'two operations','observed':'both visible','finding':'two swaps',
                             'status':'met','evidence_frames':[], 'segment_citations':[{'segment_id':0,'frames':[2]}]}]}
        self.assertTrue(task_completion.validate(raw,required,18,segments)['passed'])
        raw['requirements'][0]['segment_citations'][0]['frames']=[1]
        with self.assertRaises(ValueError):task_completion.validate(raw,required,18,segments)

    def test_every_window_is_reviewed_and_late_overlap_caps_the_whole_video(self):
        observation={'events':[],'issues':[],'summary':'fixture',
                     'criteria':[{'id':key,'score':5,'finding':'visible','evidence_frames':[1,3]} for key in iv.CRITERIA]}
        observation['requirement_evidence']=[{'id':'prompt','status':'met','evidence_frames':[1],'finding':'visible'}]
        bad=copy.deepcopy(observation)
        bad['issues']=[{'kind':'overlap','severity':'severe','essential':True,'frames':[1,2],
                        'region':[.1,.1,.5,.3],'finding':'late essential labels overlap'}]
        class Capture:
            def get(self,key):return 15 if key==cv2.CAP_PROP_FPS else 1800
            def isOpened(self):return True
            def release(self):pass
        frames=[Image.new('RGB',(120,80),'black')]*3
        observations=[copy.deepcopy(observation) for _ in range(11)]+[bad,copy.deepcopy(observation)]
        with patch.object(cv2,'VideoCapture',return_value=Capture()), \
             patch('eval.frame_extractor.extract_window',return_value=(frames,[0,1,2])) as windows, \
             patch('eval.frame_extractor.extract_frames',return_value=frames), \
             patch.object(iv,'review',side_effect=observations), \
             patch.object(iv,'compare_still',side_effect=[{'preferred':label,'video_label':label,'video_preferred':True,'advantage':'substantive'} for label in ('A','B')]):
            result=iv.assess_video(self.case(),'fixture.mp4')
        self.assertEqual(windows.call_count,12)
        self.assertTrue(result['all_windows_reviewed'])
        self.assertFalse(result['passed']);self.assertLessEqual(result['score'],39)

    def test_failed_window_keeps_successful_evidence_for_same_video_retry(self):
        observation={'events':[],'issues':[],'summary':'fixture','requirement_evidence':[],
                     'criteria':[{'id':key,'score':4,'finding':'visible','evidence_frames':[1,3]} for key in iv.CRITERIA]}
        class Capture:
            def get(self,key):return 15 if key==cv2.CAP_PROP_FPS else 450
            def isOpened(self):return True
            def release(self):pass
        frames=[Image.new('RGB',(120,80),'black')]*3
        comparison={'preferred':'tie','video_preferred':False,'advantage':'none'}
        with patch.object(cv2,'VideoCapture',return_value=Capture()), \
             patch('eval.frame_extractor.extract_window',return_value=(frames,[0,1,2])), \
             patch('eval.frame_extractor.extract_frames',return_value=frames), \
             patch.object(iv,'review',side_effect=[copy.deepcopy(observation),ValueError('bad judge JSON'),copy.deepcopy(observation)]):
            result=iv.assess_video(self.case(30),'fixture.mp4')
        self.assertFalse(result['valid']);self.assertFalse(result['all_windows_reviewed'])
        self.assertEqual(len(result['segments']),3)
        with patch.object(cv2,'VideoCapture',return_value=Capture()), \
             patch('eval.frame_extractor.extract_window',return_value=(frames,[0,1,2])), \
             patch('eval.frame_extractor.extract_frames',return_value=frames), \
             patch.object(iv,'review',return_value=copy.deepcopy(observation)) as call, \
             patch.object(iv,'compare_still',return_value=comparison):
            resumed=iv.assess_video(self.case(30),'fixture.mp4',previous=result)
        self.assertEqual(call.call_count,2)  # one failed window plus the global review
        self.assertTrue(resumed['all_windows_reviewed'])

    def test_real_minute_render_and_refusal_to_stretch_a_short_clip(self):
        try:import manim
        except ImportError:self.skipTest('Manim required')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);contract=make_contract(self.case(60))
            (root/'contract.json').write_text(json.dumps(contract))
            (root/'storyboard.json').write_text(json.dumps({'teaching_timeline':self.timeline(60),'source_edit_regions':[]}))
            equations=['2x + 5 = 17','2x = 17 - 5','2x = 12','x = 12 / 2','x = 6','2 * 6 + 5 = 17']
            lines=['from manim import *','class Section1Scene(Scene):',' def construct(self):']
            for i,equation in enumerate(equations):
                lines += [f'  self.begin_teaching_step("step_{i}")','  self.clear()',
                          f'  label = Text({equation!r},font_size=36)',
                          '  self.play(FadeIn(label),run_time=2)','  self.wait(4)',f'  self.wait({3 if i==5 else 4})']
            code=root/'section_1.py';code.write_text('\n'.join(lines)+'\n')
            env=dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            command=[sys.executable,'-m','generation.strict_manim','--code',str(code),'--scene','Section1Scene','--contract',str(root/'contract.json')]
            run=subprocess.run(command,capture_output=True,text=True,env=env,timeout=180)
            self.assertEqual(run.returncode,0,run.stderr[-4000:])
            result=json.loads((root/'strict_diagnostics.json').read_text())
            self.assertEqual(result['timing']['decoded_frames'],900)
            self.assertTrue(result['teaching_timeline']['valid'])
            code.write_text('from manim import *\nclass Section1Scene(Scene):\n def construct(self):\n  self.begin_teaching_step("step_0")\n  self.play(FadeIn(Text("x=6")),run_time=1)\n')
            run=subprocess.run(command,capture_output=True,text=True,env=env,timeout=60)
            self.assertNotEqual(run.returncode,0)

    def test_real_source_lesson_preserves_reference_and_has_separate_caption_panel(self):
        try:import manim
        except ImportError:self.skipTest('Manim required')
        from PIL import ImageDraw
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.png'
            image=Image.new('RGB',(854,480),'white')
            ImageDraw.Draw(image).rectangle([200,100,600,240],outline='black',width=3);image.save(source)
            contract=make_contract(self.case(30),source)
            (root/'contract.json').write_text(json.dumps(contract))
            chapters=[{'id':f'step_{i}','start_s':i*10,'end_s':(i+1)*10,'goal':f'show value step {i}','visible_evidence':f'value and explanation {i}','requirement_ids':['prompt']} for i in range(3)]
            (root/'storyboard.json').write_text(json.dumps({'source_edit_regions':[[200,100,600,240]],'teaching_timeline':chapters}))
            code=root/'section_1.py'
            code.write_text('from manim import *\nclass Section1Scene(Scene):\n def construct(self):\n'
                '  self.begin_teaching_step("step_0")\n'
                '  note=self.teaching_caption("Keep the same quantity on both sides")\n'
                '  self.play(FadeIn(note),run_time=2)\n  self.wait(7)\n'
                '  self.begin_teaching_step("step_1")\n'
                '  self.play(FadeIn(self.source_text("6",[200,100,600,240])),run_time=2)\n'
                '  self.wait(4)\n  self.wait(4)\n'
                '  self.begin_teaching_step("step_2")\n'
                '  self.play(FadeOut(note),run_time=2)\n  self.wait(7)\n')
            env=dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            run=subprocess.run([sys.executable,'-m','generation.strict_manim','--code',str(code),'--scene','Section1Scene',
                '--contract',str(root/'contract.json')],capture_output=True,text=True,env=env,timeout=120)
            self.assertEqual(run.returncode,0,run.stderr[-4000:])
            result=json.loads((root/'strict_diagnostics.json').read_text())
            self.assertTrue(result['source_preservation']['valid'])
            self.assertEqual(result['source_preservation']['pre_encoding']['checked_frames'],450)


if __name__=='__main__':unittest.main()
