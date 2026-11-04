import copy
import unittest
from eval.evidence_audit import reconcile
from eval import benchmark_operators as operators
from eval import rubric_6x6, benchmark_video_rubric
import numpy as np

class EvidenceAuditTests(unittest.TestCase):
    def fixture(self):
        return {'axes': {'visual_quality': {'score': 95}, 'signal_quality': {'score': 95},
                         'conceptual_correctness': {'score': 95}},
                'instructional_presentation': {'valid': True, 'criteria': [
                    {'id': 'layout_readability', 'score': 2, 'finding': 'Essential label clipped in window 3',
                     'evidence_frames': [1, 3], 'segment_id': 3}]}}

    def test_cited_local_defect_binds_matching_axes_and_preserves_raw(self):
        result = self.fixture(); reconcile(result)
        for axis in ['visual_quality', 'signal_quality']:
            self.assertEqual(result['axes'][axis]['score'], 25)
            self.assertEqual(result['axes'][axis]['overview_score_before_evidence_audit'], 95)
            self.assertEqual(result['axes'][axis]['evidence_constraints'][0]['evidence']['segment_id'], 3)
        self.assertEqual(result['axes']['conceptual_correctness']['score'], 95)

    def test_uncited_or_invalid_review_never_causes_deduction(self):
        for change in ['uncited', 'invalid']:
            result = self.fixture()
            if change == 'uncited': result['instructional_presentation']['criteria'][0]['evidence_frames'] = []
            else: result['instructional_presentation']['valid'] = False
            reconcile(result)
            self.assertEqual(result['axes']['visual_quality']['score'], 95)

    def test_diagnostic_indices_cannot_be_presented_as_quality_scores(self):
        frames=[np.zeros((30,40,3),np.uint8) for _ in range(20)]
        for report in [operators.signal_quality(frames),operators.temporal_consistency(frames,15,3)]:
            self.assertIsNone(report['score']);self.assertFalse(report['quality_score'])

    def test_half_points_valid_but_arbitrary_precision_rejected(self):
        for module,axis in [(rubric_6x6,'pedagogical_clarity'),(benchmark_video_rubric,'signal_quality')]:
            rows=[{'id':key,'applicable':True,'score':3.5,'evidence_frames':[1],'finding':'Specific evidence'} for key,_ in module.RUBRIC[axis]]
            module.validate_result(axis,{'criteria':rows},1)
            rows[0]['score']=3.7
            with self.assertRaises(ValueError):module.validate_result(axis,{'criteria':rows},1)

    def test_repeated_measured_clipping_is_detected_without_a_model_rating(self):
        result={'axes':{'visual_quality':{'score':95}},'render_geometry':{'checks':[
            {'time_s':time,'failures':[{'kind':'text_outside_frame','text':'answer','outside_fraction':.3}]}
            for time in (10.,12.)]}}
        reconcile(result)
        self.assertEqual(result['axes']['visual_quality']['score'],25)
        self.assertEqual(result['evidence_audit']['constraints'][0]['source'],'render_geometry')

    def test_transient_or_small_clipping_does_not_get_major_defect_rating(self):
        for fraction,times in [(.1,(10.,12.)),(.3,(10.,10.))]:
            result={'axes':{'visual_quality':{'score':95}},'render_geometry':{'checks':[
                {'time_s':time,'failures':[{'kind':'text_outside_frame','text':'answer','outside_fraction':fraction}]}
                for time in times]}}
            reconcile(result)
            self.assertEqual(result['axes']['visual_quality']['score'],95)
