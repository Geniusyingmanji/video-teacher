import unittest
from eval import quality_scoring as q
from eval.benchmark_scoring import VIDEO_AXES,TEACHING_AXES


class QualityScoringTests(unittest.TestCase):
    def axes(self,value=80):return {k:value for k in VIDEO_AXES+TEACHING_AXES}

    def test_one_failed_axis_has_local_effect_not_total_zero(self):
        axes=self.axes();axes['visual_quality']=0
        result=q.aggregate_quality(axes,narration_required=True,speech_score=80,acceptance_failures=['corrupted_equation'])
        self.assertAlmostEqual(result['score'],69.3333,places=3)
        self.assertFalse(result['strict_pass']);self.assertFalse(result['numeric_caps_applied'])

    def test_same_defect_does_not_change_unrelated_axes(self):
        axes=self.axes();before=dict(axes)
        q.aggregate_quality(axes,acceptance_failures=['essential_text_overlap'])
        self.assertEqual(axes,before)

    def test_zero_is_allowed_for_actual_all_zero_evidence_without_floor(self):
        result=q.aggregate_quality(self.axes(0),narration_required=True,speech_score=0)
        self.assertEqual(result['score'],0);self.assertTrue(result['valid'])

    def test_unknown_is_unverified_not_zero_or_renormalized(self):
        result=q.aggregate_quality(self.axes(),narration_required=True,speech_score=None)
        self.assertFalse(result['valid']);self.assertIsNone(result['score'])

    def test_score_is_monotonic_and_acceptance_does_not_change_number(self):
        previous=-1
        for value in range(101):
            a=q.aggregate_quality(self.axes(value),narration_required=True,speech_score=value)
            b=q.aggregate_quality(self.axes(value),narration_required=True,speech_score=value,acceptance_failures=['wrong_final_state'])
            self.assertGreaterEqual(a['score'],previous);previous=a['score']
            self.assertEqual(a['score'],b['score']);self.assertFalse(b['strict_pass'])

    def test_partial_speech_credit_is_retained(self):
        review={'criteria':[{'score':5},{'score':5},{'score':1},{'score':5}]}
        self.assertEqual(q.criterion_mean(review),75)

    def test_repeated_numeric_gate_does_not_multiply_penalty(self):
        a=q.aggregate_quality(self.axes(),acceptance_failures=['overlap'])
        b=q.aggregate_quality(self.axes(),acceptance_failures=['overlap']*8)
        self.assertEqual(a,b)

    def test_unresolved_criterion_is_not_replaced_by_zero_or_excluded_from_mean(self):
        from eval.rubric_6x6 import RUBRIC,validate_result
        from unittest.mock import patch
        import os
        rows=[{'id':key,'applicable':True,'score':4,'evidence_frames':[1],'finding':'visible evidence'}
              for key,_ in RUBRIC['visual_quality']]
        rows[0].update(score=None,finding='cannot resolve the small text in these samples')
        with patch.dict(os.environ,{'VIDEO_TEACHER_SCORING_POLICY':'quality-v12'}):
            judged=validate_result('visual_quality',{'criteria':rows},1)
        self.assertIsNone(judged['score']);self.assertEqual(judged['binary'],'UNVERIFIED')
        self.assertIsNone(q.criterion_mean(judged))

    def test_invalid_numbers_never_become_a_quality_score(self):
        for value in [None,True,float('nan'),float('inf'),-1,101]:
            axes=self.axes();axes['visual_quality']=value
            scored=q.aggregate_quality(axes)
            self.assertFalse(scored['valid']);self.assertIsNone(scored['score'])
