import copy
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image

from eval import instructional_video as iv
from generation.quality_gate import assess


class InstructionalVideoTests(unittest.TestCase):
    def observation(self,score=4):
        return {'events':[], 'issues':[], 'criteria':[{'id':key,'score':score,
                'finding':'located evidence','evidence_frames':[1,3]} for key in iv.CRITERIA], 'summary':'fixture'}

    def event(self,kind='operation',region=None):
        return {'kind':kind,'before_frame':1,'after_frame':3,'region':region or [0,0,1,1],
                'before':'original objects','after':'original objects exchange slots','learning_value':'the required swap is visible'}

    def comparisons(self,advantage='substantive'):
        return [{'preferred':'A','video_label':'A','video_preferred':True,'advantage':advantage},
                {'preferred':'B','video_label':'B','video_preferred':True,'advantage':advantage}]

    def moving_frames(self):
        frames=[]
        for left in (10,30,50):
            pixels=np.zeros((80,120,3),dtype=np.uint8);pixels[20:40,left:left+15]=255
            frames.append(Image.fromarray(pixels))
        return frames

    def test_frozen_frame_evidence_prevents_the_judge_from_inventing_events(self):
        frame=Image.new('RGB',(120,80),'black')
        with patch.object(iv,'_ask',return_value=self.observation()) as call:
            iv.review({'prompt_text':'Show the two swaps.'},[frame]*3)
            schema=call.call_args.args[1]['json_schema']['schema']
            self.assertEqual(schema['properties']['events']['maxItems'],0)
        with patch.object(iv,'_ask',return_value=self.observation()) as call:
            iv.review({'prompt_text':'Show the two swaps.'},self.moving_frames())
            schema=call.call_args.args[1]['json_schema']['schema']
            self.assertGreater(schema['properties']['events']['maxItems'],0)

    def test_actual_relevant_operation_can_pass_without_large_global_motion(self):
        frames=[]
        for left in (105,115,125):
            p=np.zeros((480,854,3),dtype=np.uint8);p[105:115,left:left+10]=255;frames.append(Image.fromarray(p))
        event=self.event(region=[100/854,100/480,140/854,140/480])
        events=iv.verify_events([event],frames)
        self.assertTrue(events[0]['transition_verified'])
        result=iv.score_review(self.observation(),events,self.comparisons())
        self.assertTrue(result['passed']);self.assertEqual(result['score'],75)

    def test_reveal_and_decorative_motion_do_not_count_as_reasoning(self):
        for kind in ('reveal','decoration'):
            events=iv.verify_events([self.event(kind)],self.moving_frames())
            self.assertFalse(events[0]['transition_verified'])
            result=iv.score_review(self.observation(5),events,self.comparisons())
            self.assertFalse(result['passed']);self.assertLessEqual(result['score'],49)

    def test_frozen_content_cannot_pass_on_model_claims_of_operations(self):
        frame=self.moving_frames()[0]
        events=iv.verify_events([self.event()],[frame]*3)
        self.assertFalse(events[0]['transition_verified'])
        result=iv.score_review(self.observation(5),events,self.comparisons())
        self.assertLessEqual(result['score'],49)

    def test_final_still_equivalence_blocks_high_score_even_with_visible_motion(self):
        events=iv.verify_events([self.event()],self.moving_frames())
        result=iv.score_review(self.observation(5),events,self.comparisons('cosmetic'))
        self.assertFalse(result['passed']);self.assertLessEqual(result['score'],49)

    def test_persistent_layout_overlap_cannot_average_away(self):
        raw=self.observation(5);raw['issues']=[{'kind':'overlap','severity':'severe','essential':True,
            'frames':[2,3],'region':[.1,.1,.5,.3],'finding':'essential captions overlap'}]
        events=iv.verify_events([self.event()],self.moving_frames())
        result=iv.score_review(raw,events,self.comparisons())
        self.assertLessEqual(result['score'],39);self.assertFalse(result['passed'])
        applied=iv.apply({'valid':True,'score':100,'strict_pass':True},result)
        self.assertEqual(applied['score'],39);self.assertEqual(applied['eight_axis_diagnostic_score'],100)

    def test_writing_animation_in_one_frame_is_not_persistent_layout_failure(self):
        raw=self.observation();raw['issues']=[{'kind':'overlap','severity':'severe','essential':True,
            'frames':[2],'region':[.1,.1,.5,.3],'finding':'transient text transition'}]
        events=iv.verify_events([self.event()],self.moving_frames())
        self.assertTrue(iv.score_review(raw,events,self.comparisons())['passed'])

    def test_order_biased_comparison_is_unverified_not_a_favorable_average(self):
        comparisons=self.comparisons();comparisons[1]['video_preferred']=False
        result=iv.score_review(self.observation(5),[],comparisons)
        self.assertFalse(result['valid']);self.assertIsNone(result['score'])

    def test_conclusive_failure_stays_bounded_when_comparison_is_uncertain(self):
        observed=self.observation(5)
        for row in observed['criteria']:
            if row['id']=='visual_explanation':row['score']=1
        comparisons=self.comparisons();comparisons[1]['video_preferred']=False
        result=iv.score_review(observed,[],comparisons)
        self.assertTrue(result['valid']);self.assertFalse(result['comparison_valid'])
        self.assertEqual(result['decision_type'],'bounded_rejection')
        self.assertFalse(result['passed']);self.assertLessEqual(result['score'],49)

    def test_missing_boolean_and_nan_presentation_scores_cannot_pass(self):
        for value in (None,True,float('nan')):
            result=iv.apply({'valid':True,'score':100,'strict_pass':True},{'valid':True,'score':value,'passed':True})
            self.assertFalse(result['valid']);self.assertIsNone(result['score'])
        generation={'complete':True,'timing':{'valid':True}}
        gate=assess(generation,{'version':'video-teacher-2x8-v7','scoring':{'valid':True,'strict_pass':True}})
        self.assertIn('instructional_presentation',gate['failures'])

    def test_schema_rejects_invented_regions_repeated_criteria_and_reverse_time(self):
        for mutation in ('box','criterion','time','frame'):
            raw=self.observation();raw['events']=[self.event()]
            if mutation=='box':raw['events'][0]['region']=[0,0,2,1]
            if mutation=='criterion':raw['criteria'][1]['id']=raw['criteria'][0]['id']
            if mutation=='time':raw['events'][0]['after_frame']=1
            if mutation=='frame':raw['criteria'][0]['evidence_frames']=[True]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):iv.validate(raw,3)

    def test_uncertain_review_retries_same_video_but_valid_low_review_does_not(self):
        from eval import run_benchmark_v2 as runner
        uncertain={'errors':[],'instructional_presentation':{'valid':False},
                   'supplementary':{'teaching_engagement':{'valid':True}}}
        low={'errors':[],'instructional_presentation':{'valid':True,'score':20,'passed':False},
             'supplementary':{'teaching_engagement':{'valid':True}}}
        with patch.object(runner,'evaluate',side_effect=[uncertain,low]) as call:
            runner.evaluate_with_retry({}, {'status':'ok','video_path':'same.mp4'})
            self.assertEqual(call.call_count,2)
        with patch.object(runner,'evaluate',return_value=low) as call:
            runner.evaluate_with_retry({}, {'status':'ok','video_path':'same.mp4'})
            self.assertEqual(call.call_count,1)

    def test_substantive_comparison_needs_an_ordered_evidence_pair(self):
        raw={'preferred':'A','advantage':'substantive','finding':'a swap is visible',
             'lost_information':'actual trajectory','before_frame':0,'after_frame':0}
        with self.assertRaises(ValueError):iv.validate_comparison(raw,3)
