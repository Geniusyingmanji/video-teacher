import json
import unittest
from unittest.mock import patch

from eval import teaching_engagement as engagement
from eval import benchmark_scoring as scoring
from eval.rubric_6x6 import RUBRIC, RUBRIC_VERSION


class TeachingEngagementTests(unittest.TestCase):
    def rows(self, score=4):
        return [{'id': key, 'applicable': True, 'score': score,
                 'evidence_frames': [1], 'finding': 'A task-relevant change is visible.'}
                for key, _ in engagement.RUBRIC['teaching_engagement']]

    def test_supplement_is_evidence_backed_and_excluded(self):
        with patch.object(engagement, 'chat', return_value=json.dumps({'criteria': self.rows()})):
            with patch.object(engagement, 'frames_as_multimodal_content', return_value=[]):
                result = engagement.score({'prompt_text': 'Label the angle.', 'actual_duration_s': 5}, [object()])
        self.assertTrue(result['valid'])
        self.assertEqual(result['score'], 75)
        self.assertFalse(result['included_in_total'])
        self.assertEqual(result['rubric_version'], engagement.VERSION)

    def test_no_positive_score_without_evidence(self):
        rows = self.rows()
        rows[0]['evidence_frames'] = []
        with patch.object(engagement, 'chat', return_value=json.dumps({'criteria': rows})), \
             patch.object(engagement, 'frames_as_multimodal_content', return_value=[]):
            with self.assertRaises(ValueError):
                engagement.score({}, [object()])

    def test_engagement_never_compensates_for_incorrectness(self):
        axes = {name: 90 for names in scoring.GROUPS.values() for name in names}
        axes['conceptual_correctness'] = 20
        before = scoring.score_case(axes)
        after = scoring.score_case({**axes, 'teaching_engagement': 100})
        self.assertEqual(before, after)
        self.assertFalse(after['strict_pass'])

    def test_partial_supplement_has_no_complete_mean(self):
        report = engagement.aggregate([
            {'supplementary': {'teaching_engagement': {'valid': True, 'score': 100}}},
            {'supplementary': {'teaching_engagement': {'valid': False, 'score': None}}}])
        self.assertEqual(report['n_valid'], 1)
        self.assertIsNone(report['mean_complete_only'])
        self.assertEqual(report['diagnostic_mean_available_only'], 100)

    def test_new_rules_cover_duration_and_representation(self):
        self.assertEqual(RUBRIC_VERSION, '6x6-v3')
        clarity = dict(RUBRIC['pedagogical_clarity'])
        representation = dict(RUBRIC['didactic_affordances'])
        self.assertIn('actual clip duration', clarity['readability'])
        self.assertIn('labeling task', representation['step_evidence'])


if __name__ == '__main__':
    unittest.main()
