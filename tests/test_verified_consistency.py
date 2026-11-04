import unittest

from eval import verified_consistency as consistency
from eval import benchmark_scoring


class VerifiedConsistencyTests(unittest.TestCase):
    def fixture(self):
        axes={key: {'summary':'The final array is broken; it is not sorted.',
                    'criteria':[{'id':'state','finding':'An empty first box is visible.'}]}
              for key in benchmark_scoring.VIDEO_AXES + benchmark_scoring.TEACHING_AXES}
        raw={'axes':{key:{field:{'status':'agrees','observed':'The first box is empty.',
                     'evidence_frames':[1]} for field in ('summary','state')} for key in axes}}
        return axes,raw

    def test_correct_negative_reports_are_valid_and_bound_to_literal_source(self):
        axes,raw=self.fixture()
        result=consistency.validate(raw,axes,2)
        self.assertTrue(result['valid'])
        self.assertEqual(result['axes']['visual_quality']['state']['report_statement'],
                         axes['visual_quality']['criteria'][0]['finding'])
        result['axes']['visual_quality']['state']['report_statement']='The array is sorted.'
        with self.assertRaisesRegex(ValueError,'statement was changed'):
            consistency.validate(result,axes,2)

    def test_each_statement_needs_a_decision_and_real_frame_evidence(self):
        axes,raw=self.fixture()
        del raw['axes']['visual_quality']['state']
        with self.assertRaisesRegex(ValueError,'every literal'):
            consistency.validate(raw,axes,2)
        axes,raw=self.fixture();raw['axes']['visual_quality']['state']['evidence_frames']=[3]
        with self.assertRaisesRegex(ValueError,'actual frame'):
            consistency.validate(raw,axes,2)

    def test_material_conflicts_and_uncertainty_continue_to_block_validity(self):
        axes,raw=self.fixture()
        raw['axes']['visual_quality']['state']['status']='conflict'
        result=consistency.validate(raw,axes,2)
        self.assertFalse(result['valid']);self.assertEqual(result['conflicting_axes'],['visual_quality'])
        raw['axes']['visual_quality']['state']['status']='uncertain'
        result=consistency.validate(raw,axes,2)
        self.assertFalse(result['valid']);self.assertEqual(result['uncertain_axes'],['visual_quality'])

    def test_nonmaterial_quality_opinions_do_not_invent_factual_conflicts(self):
        axes,raw=self.fixture()
        raw['axes']['visual_quality']['summary'].update(status='non_material',evidence_frames=[])
        self.assertTrue(consistency.validate(raw,axes,2)['valid'])
