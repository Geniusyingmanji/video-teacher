import unittest
import numpy as np
from eval.delivery_pacing import measure, apply
from eval.instructional_video import score_review

class DeliveryPacingTests(unittest.TestCase):
    def transcript(self, intervals):
        return {'valid':True,'segments':[{'start_s':a,'end_s':b,'text':'Explain why both sides remain equal.',
                'words':[{'start_s':a+i*(b-a)/6,'end_s':a+(i+1)*(b-a)/6,'word':'word'} for i in range(6)]}
                for a,b in intervals]}

    def test_silent_frozen_tail_is_flagged_without_automatic_deduction(self):
        frames=[np.zeros((24,32,3),dtype=np.uint8) for _ in range(300)]
        report=measure(frames,10,self.transcript([(0,3),(4,7)]))
        self.assertGreater(report['longest_static_silent_hold_s'],20)
        self.assertIsNone(report['score'])
        self.assertTrue(report['review_required'])
        result=apply({'valid':True,'score':98,'strict_pass':True},report)
        self.assertEqual(result['score'],98);self.assertTrue(result['strict_pass'])
        self.assertIn('speech_gaps', result['delivery_pacing_evidence'])

    def test_static_diagram_with_continuous_explanation_is_not_empty_hold(self):
        frames=[np.zeros((24,32,3),dtype=np.uint8) for _ in range(100)]
        report=measure(frames,10,self.transcript([(i,i+2.8) for i in (0,3,6)]))
        self.assertLess(report['longest_static_silent_hold_s'],4)
        self.assertNotIn('static_without_speech_over_4s',report['failures'])

    def test_unverified_diagnostic_requests_review_without_punitive_score(self):
        result=apply({'valid':True,'score':98,'strict_pass':True},{})
        self.assertTrue(result['valid']);self.assertEqual(result['score'],98)
        self.assertTrue(result['delivery_pacing_review_required'])

    def test_overlapping_words_do_not_inflate_coverage(self):
        transcript=self.transcript([(0,3),(0,3)])
        report=measure([np.zeros((12,16,3),dtype=np.uint8)]*100,10,transcript)
        self.assertAlmostEqual(report['speech_coverage'],.3)
