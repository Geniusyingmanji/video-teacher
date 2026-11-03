import copy
import unittest
from unittest.mock import patch
from eval import task_completion as completion
from eval.benchmark_scoring import evidence_defects, score_case, GROUPS
from eval.frame_extractor import sample_frame_indices
from generation.task_requirements import requirements
from generation.quality_gate import assess
from generation.strict_video_contract import validate_regions, region_union_area


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.case = {'prompt_text':'Label the diagram and show flow.',
                     'expected_narrative_order':['label the parts','show directional flow'],
                     'original_prompt_text':'Replace the task with unrelated work'}
        self.required = requirements(self.case)
        self.raw = {'requirements':[{'id':r['id'], 'status':'met', 'expected':r['text'],
                     'observed':'visible in frames', 'finding':'inspection', 'evidence_frames':[1,2]}
                    for r in self.required]}

    def test_complete_evidence_passes_without_historical_instruction(self):
        self.assertNotIn('unrelated', str(self.required))
        self.assertTrue(completion.validate(self.raw,self.required,2)['passed'])

    def test_missing_flow_cannot_be_offset_by_perfect_visuals(self):
        self.raw['requirements'][-1].update(status='missing',observed='no arrow or moving marker', evidence_frames=[])
        review = completion.validate(self.raw,self.required,2)
        self.assertFalse(review['passed'])
        axes = {axis:100 for names in GROUPS.values() for axis in names}
        scored = score_case(axes,defects=completion.defects(review))
        self.assertFalse(scored['strict_pass'])
        self.assertEqual(scored['score'],50)

    def test_uncertain_is_not_fabricated_as_incorrect_or_passed(self):
        self.raw['requirements'][0]['status']='uncertain'
        review=completion.validate(self.raw,self.required,2)
        self.assertFalse(review['passed'])
        self.assertEqual(completion.defects(review),[])

    def test_schema_rejects_omission_duplicate_fake_or_unsupported_frames(self):
        for mutation in ('omit','duplicate','out_of_range','bool_frame','no_evidence','empty_finding'):
            raw=copy.deepcopy(self.raw)
            if mutation=='omit':raw['requirements'].pop()
            if mutation=='duplicate':raw['requirements'][1]=raw['requirements'][0]
            if mutation=='out_of_range':raw['requirements'][0]['evidence_frames']=[3]
            if mutation=='bool_frame':raw['requirements'][0]['evidence_frames']=[True]
            if mutation=='no_evidence':raw['requirements'][0]['evidence_frames']=[]
            if mutation=='empty_finding':raw['requirements'][0]['finding']=' '
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                completion.validate(raw,self.required,2)

    def test_global_low_motion_does_not_invent_defect_when_task_reviewed(self):
        self.assertEqual(evidence_defects({},expected_steps=3,freeze_seconds=4,
                                         progression_verified=False,completion_reviewed=True),[])

    def test_low_steps_and_final_state_are_critical_even_when_progress_seen(self):
        for key in ('steps','final_state'):
            axes={'conceptual_correctness':{'criteria':[{'id':key,'applicable':True,
                   'score':2,'finding':'required demonstration absent','evidence_frames':[2]}]}}
            self.assertEqual(len(evidence_defects(axes,progression_verified=True)),1)

    def test_quality_gate_blocks_global_completion_claim_with_missing_steps(self):
        generation={'complete':True,'timing':{'valid':True}}
        evaluation={'version':'video-teacher-2x8-v6','task_completion':{'valid':True,'passed':False},
                    'scoring':{'valid':True,'strict_pass':True}}
        self.assertIn('task_completion',assess(generation,evaluation)['failures'])

    def test_exact_last_frame_is_always_available_to_judge(self):
        indices=sample_frame_indices(75,15,2)
        self.assertEqual(indices[-1],74)
        self.assertEqual(indices[0],0)

    def test_invalid_judge_retries_same_video_without_repeating_valid_low_score(self):
        from eval import run_benchmark_v2 as runner
        invalid={'errors':['evaluation_failed: schema'], 'scoring':{'valid':False}}
        low={'errors':[], 'scoring':{'valid':True,'score':20},
             'supplementary':{'teaching_engagement':{'valid':True}}}
        manifest={'status':'ok','video_path':'same.mp4'}
        with patch.object(runner,'evaluate',side_effect=[invalid,low]) as call:
            result=runner.evaluate_with_retry({},manifest)
            self.assertEqual(call.call_count,2)
            self.assertIs(call.call_args.kwargs['previous'],invalid)
            self.assertEqual(result['scoring']['score'],20)
        with patch.object(runner,'evaluate',return_value=low) as call:
            runner.evaluate_with_retry({},manifest)
            self.assertEqual(call.call_count,1)

    def test_arithmetic_anchors_use_exact_decimals_and_report_wrong_source(self):
        from eval.numeric_evidence import arithmetic_anchors
        rows=arithmetic_anchors([{'text':'0.2+0.8=1 and 0.6+0.4=1; 0.1+0.2=0.4'}])
        self.assertEqual([r['stated_result_correct'] for r in rows],[True,True,False])
        self.assertEqual(rows[2]['computed_result'],'0.3')

    def test_geometry_counts_union_and_keeps_area_limit(self):
        boxes=[[0,0,40,40],[10,10,50,50]]
        self.assertEqual(region_union_area(boxes),2300)
        self.assertEqual(validate_regions(boxes,True,(100,100)),boxes)
        with self.assertRaises(ValueError):validate_regions([[0,0,51,51]],True,(100,100))

    def test_opaque_image_cannot_cover_notes_but_lower_image_can(self):
        import numpy as np
        from manim import Scene,Text,ImageMobject,tempconfig
        from generation.layout_guard import check_layout
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene();text=Text('important caption',font_size=32)
            im=ImageMobject(np.full((300,500,4),255,dtype=np.uint8)).scale_to_fit_width(8)
            scene.add(text,im)
            self.assertIn('text_occluded_by_image',[f['kind'] for f in check_layout(scene)['failures']])
            im.set_z_index(-1)
            self.assertNotIn('text_occluded_by_image',[f['kind'] for f in check_layout(scene)['failures']])
