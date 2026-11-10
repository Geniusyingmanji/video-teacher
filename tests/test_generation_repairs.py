import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from generation.repair_feedback import compact, bounded_feedback, validated_frozen, feedback_for
from generation.source_plan import validate_plan, compile_plan
from generation.strict_video_contract import make_contract, contract_text
from generation.prompt_budget import request_budget
from eval import grounded_observations
from eval.benchmark_scoring import evidence_defects
from generation.quality_gate import assess
from scripts.build_lesson_prompts import revise


class RepairTests(unittest.TestCase):
    def test_nested_feedback_has_total_budget_and_keeps_actionable_errors(self):
        evidence = {f'field_{i}': {f'detail_{j}': 'evidence '*500
                    for j in range(20)} for i in range(20)}
        feedback = {'render_diagnostics': evidence, 'generation_error': 'speech too_long',
                    'gate_failures': ['narration_generated'],
                    'frozen_source_edit_regions': [[1, 2, 3, 4]],
                    'review_frames': ['one.jpg']}
        result = bounded_feedback(feedback)
        self.assertLess(len(json.dumps(result, ensure_ascii=False)), 12000)
        for key in ('generation_error', 'gate_failures', 'frozen_source_edit_regions', 'review_frames'):
            self.assertEqual(result[key], feedback[key])
        self.assertIn('retained on disk', result['render_diagnostics'])

    def test_plan_review_excludes_historical_failures_but_keeps_task(self):
        from generation.source_plan import review_plan
        from generation.strict_video_contract import ContractAPI
        from types import SimpleNamespace
        plan, contract = self.plan()
        contract.update(task={'prompt_text': 'Complete both probabilities.'},
                        quality_feedback={'generation_error': 'old speech too_long'},
                        storyboard_repair={'error': 'old rejected plan'})
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"valid": true, "finding": "Both answers match."}'))])
        with patch.object(ContractAPI, '__call__', autospec=True, return_value=(response, {})) as call:
            review_plan(ContractAPI(contract, Path('/unused')), plan, contract)
        scoped = call.call_args.args[0]
        self.assertEqual(scoped.contract['task'], contract['task'])
        self.assertNotIn('quality_feedback', scoped.contract)
        self.assertNotIn('storyboard_repair', scoped.contract)
        self.assertFalse(scoped.include_render_diagnostics)

    def test_current_quality_gate_requires_completion_and_presentation(self):
        generation = {'contract_version':'instructional-lesson-contract-v3'}
        evaluation = {'version':'video-teacher-2x8-v11', 'scoring':{'valid':True,'strict_pass':True},
                      'task_completion':{'valid':True,'passed':False},
                      'instructional_presentation':{'valid':True,'passed':False}}
        result = assess(generation, evaluation)
        self.assertFalse(result['checks']['task_completion'])
        self.assertFalse(result['checks']['instructional_presentation'])

    def test_duration_follows_requested_actions(self):
        short = {'id':'short','prompt_text':'Label the point.','task_type':'explanation',
                 'expected_narrative_order':['show point']}
        long = {**short, 'id':'long','task_type':'problem_solving',
                'expected_narrative_order':[f'operation {i}' for i in range(8)],
                'expected_concepts':[f'concept {i}' for i in range(5)],
                'expected_visual_elements':[f'element {i}' for i in range(6)]}
        self.assertLess(revise(short)['target_duration_s'], revise(long)['target_duration_s'])

    def test_rejected_regions_never_freeze_and_accepted_regions_stay_fixed(self):
        bad = {'source_edit_regions':[[400,200,1200,1000]],'source_plan_validation':{'valid':False}}
        self.assertIsNone(validated_frozen(bad))
        good = {'source_edit_regions':[[10,10,20,20]],'source_plan_validation':{'valid':True}}
        frozen = validated_frozen(good)
        self.assertEqual(validated_frozen(bad,frozen),good['source_edit_regions'])
        frozen[0][0] = 0
        self.assertEqual(good['source_edit_regions'][0][0],10)

    def test_compaction_preserves_full_task_but_bounds_diagnostic_arrays(self):
        task = {'id':'fixture','prompt_text':'Keep every original condition. '*2000}
        c = make_contract(task)
        c['quality_feedback'] = {'render_diagnostics':{'boxes':[[i]*4 for i in range(5000)]}}
        text = contract_text(c)
        self.assertIn(task['prompt_text'],text)
        self.assertLess(len(text)-len(task['prompt_text']),5000)
        self.assertEqual(len(compact(c['quality_feedback'])['render_diagnostics']['boxes']),8)
        boxes=[[i,i,i+1,i+1] for i in range(20)]
        self.assertEqual(compact({'frozen_source_edit_regions':boxes})['frozen_source_edit_regions'],boxes)

    def test_feedback_carries_actual_low_criteria_without_entire_evaluation(self):
        e = {'axes':{'conceptual_correctness':{'criteria':[
            {'id':'final_state','applicable':True,'score':2,'finding':'second answer missing','evidence_frames':[2]}]}}}
        f = feedback_for({'quality_gate':{'failures':['task_coverage']}},e)
        self.assertIn('second answer missing',json.dumps(f))
        self.assertNotIn('quality_evidence',f)

    def plan(self):
        c = {'source_size_pixels':[1000,1000]}
        p = {'source_edit_regions':[[100,100,200,180],[500,500,600,580]],
             'source_operations':[
                 {'id':'first','kind':'text','step':1,'box':[100,100,200,180],'text':'0.8','reason':'first edge'},
                 {'id':'second','kind':'text','step':2,'box':[500,500,600,580],'text':'0.4','reason':'second edge'}]}
        return p,c

    def test_source_compiler_cannot_omit_second_answer(self):
        p,c = self.plan()
        code = compile_plan(p,c)
        self.assertIn("'0.8'",code); self.assertIn("'0.4'",code)
        self.assertEqual(code.count('self.source_text'),2)
        self.assertEqual(code.count('self.play'),2)
        compile(code,'fixture','exec')

    def test_unreadable_source_box_is_rejected_before_plan_freezes(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.png';Image.new('RGB',(1000,1000),'white').save(source)
            contract=make_contract({'id':'tiny answer','prompt_text':'Write the answer in the blank box.'},source)
            plan={'source_edit_regions':[[100,100,200,110]],'source_operations':[
                {'id':'answer','kind':'text','step':1,'box':[100,100,200,110],'text':'0.8','reason':'answer'}]}
            with self.assertRaises(ValueError):validate_plan(plan,contract)

    def test_source_plan_rejects_widening_bad_points_and_missing_operations(self):
        p,c = self.plan()
        c['quality_feedback']={'frozen_source_edit_regions':[[1,1,10,10]]}
        with self.assertRaisesRegex(ValueError,'frozen'): validate_plan(p,c)
        del c['quality_feedback']
        p['source_operations'][0].update(kind='curve',points=[[0,0],[190,170]])
        with self.assertRaisesRegex(ValueError,'curve point'):validate_plan(p,c)
        p['source_operations']=[]
        with self.assertRaises(ValueError):validate_plan(p,c)

    def test_arrow_touching_answer_box_is_not_missed(self):
        from PIL import Image, ImageDraw
        from generation.source_geometry import rectangle_candidates
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.png';im=Image.new('RGB',(400,300),'white');draw=ImageDraw.Draw(im)
            draw.rectangle((100,80,220,130),outline='black',width=2)
            draw.polygon([(70,140),(130,100),(115,135)],fill='black')
            im.save(p)
            candidates=rectangle_candidates(p)
            self.assertTrue(any(abs(row['source_pixel_box'][0]-100)<8 and abs(row['source_pixel_box'][1]-80)<8 for row in candidates))

    def test_missing_worker_still_counts_in_ten_case_denominator(self):
        from scripts.run_qwen_multigpu import summarize,SCORING_VERSION
        with tempfile.TemporaryDirectory() as tmp:
            c=summarize(Path(tmp),[{'id':f'case{i}'} for i in range(10)],finished=True)
            self.assertEqual(c['total'],10);self.assertEqual(c['processed'],0)
            self.assertFalse(c['complete'])
            data=json.loads((Path(tmp)/SCORING_VERSION/'aggregate.json').read_text())
            self.assertEqual(data['n_total'],10);self.assertEqual(data['n_failed'],10)

    def test_exact_text_budget_fails_before_network_and_reserves_images(self):
        path='/root/models/Qwen3.8-27B/tokenizer.json'
        if not Path(path).exists(): self.skipTest('local tokenizer not installed')
        tokens,info=request_budget('Short request',4096,4)
        self.assertEqual(info['reserved_tokens'],9216)
        self.assertEqual(tokens,4096)
        with patch.dict(os.environ,{'LOCAL_CONTEXT_LENGTH':'200'}):
            with self.assertRaisesRegex(ValueError,'budget'):request_budget('x '*1000,4096,1)

    def test_verified_progression_does_not_erase_real_correctness_defects(self):
        axes={'conceptual_correctness':{'criteria':[{'id':'symbols','applicable':True,'score':1,'finding':'wrong answer','evidence_frames':[2]}]}}
        result=evidence_defects(axes,expected_steps=3,freeze_seconds=4,progression_verified=True)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['reason'],'critical_conceptual_correctness_symbols')
        self.assertTrue(evidence_defects({},expected_steps=3,freeze_seconds=4,progression_verified=False))

    def test_grounded_schema_rejects_guessed_frame_indices(self):
        invalid={'observations':[{'fact':'0.8','frames':[90]}],'visible_progression':True,'completed_task':True,'uncertainties':[]}
        valid={**invalid,'observations':[{'fact':'0.8 in lower box','frames':[1]}]}
        with patch.object(grounded_observations,'frames_as_multimodal_content',return_value=[]), patch.object(grounded_observations,'chat',side_effect=[json.dumps(invalid),json.dumps(valid)]) as call:
            self.assertEqual(grounded_observations.observe({},[object()]),{**valid, 'valid':True})
            self.assertEqual(call.call_count,2)

    def test_consistency_rejects_reported_conflict(self):
        response={'valid':False,'conflicting_axes':['conceptual_correctness'],'finding':'0.4 claimed but frame shows 0.8'}
        with patch.object(grounded_observations,'chat',return_value=json.dumps(response)), patch.object(grounded_observations,'frames_as_multimodal_content',return_value=[]):
            self.assertFalse(grounded_observations.consistency({}, {}, {'conceptual_correctness':{}}, [])['valid'])

    def test_exact_molecule_roundtrip_and_functional_groups(self):
        from generation.verified_assets import molecule_assets
        from rdkit import Chem
        inchi=Chem.MolToInchi(Chem.MolFromSmiles('COc1ccc(C(=O)OC)cc1O'))
        with tempfile.TemporaryDirectory() as tmp:
            a=molecule_assets({'prompt_text':'Draw '+inchi},Path(tmp))
            self.assertEqual(a['canonical_inchi'],inchi)
            self.assertTrue(all(a['functional_groups'].values()))
            self.assertTrue(Path(a['paths']['classified']).is_file())

    def test_layout_guard_rejects_overlapping_and_offscreen_labels(self):
        from manim import Scene, Text, tempconfig
        from generation.layout_guard import check_layout
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene(); scene.add(Text('Proximal',font_size=32),Text('Distal',font_size=32))
            self.assertIn('text_overlap',[e['kind'] for e in check_layout(scene)['failures']])
            scene.clear();scene.add(Text('outside',font_size=32).move_to([20,0,0]))
            self.assertIn('text_outside_frame',[e['kind'] for e in check_layout(scene)['failures']])

    def test_real_compiled_source_render_preserves_every_outside_pixel(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.png';Image.new('RGB',(1000,1000),'white').save(source)
            p,c=self.plan();c=make_contract({'id':'fixture','prompt_text':'Fill both answer boxes.'},source)
            (root/'contract.json').write_text(json.dumps(c));(root/'storyboard.json').write_text(json.dumps(p))
            (root/'scene.py').write_text(compile_plan(p,c))
            env=dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            r=subprocess.run([sys.executable,'-m','generation.strict_manim','--code',str(root/'scene.py'),'--scene','Section1Scene','--contract',str(root/'contract.json')],capture_output=True,text=True,env=env,timeout=90)
            self.assertEqual(r.returncode,0,r.stderr[-2000:])
            d=json.loads((root/'strict_diagnostics.json').read_text())
            self.assertEqual(d['source_preservation']['pre_encoding']['max_changed_pixels'],0)
            self.assertEqual(d['timing']['decoded_frames'],75)

    def test_verified_asset_calls_without_display_are_rejected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root/'molecule.png'
            Image.new('RGB',(300,200),'white').save(image)
            contract = make_contract({'prompt_text':'Show the verified initial and classified structures.'})
            contract['verified_assets'] = {'paths':{'initial':str(image),'classified':str(image)}}
            (root/'contract.json').write_text(json.dumps(contract))
            (root/'storyboard.json').write_text('{"source_edit_regions":[]}')
            (root/'scene.py').write_text('from manim import *\nclass Section1Scene(Scene):\n'
                '    def construct(self):\n'
                '        unused = self.verified_structure(False)\n'
                '        shown = self.verified_structure(True)\n'
                '        self.play(FadeIn(shown))\n')
            env = dict(os.environ,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            result = subprocess.run([sys.executable,'-m','generation.strict_manim','--code',str(root/'scene.py'),
                '--scene','Section1Scene','--contract',str(root/'contract.json')],capture_output=True,text=True,env=env,timeout=90)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('must actually appear',result.stderr)


if __name__=='__main__':unittest.main()
