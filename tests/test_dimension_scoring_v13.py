import copy
import unittest
from unittest.mock import patch
from eval.dimension_scoring import apply, VERSION
from eval.benchmark_scoring import VIDEO_AXES, TEACHING_AXES
from generation.quality_gate import assess


def fixture():
    return {'axes': {k: {'criteria': [{'id': 'rated', 'score': 5}]} for k in VIDEO_AXES + TEACHING_AXES},
            'instructional_presentation': {'valid': True, 'passed': False, 'all_windows_reviewed': True,
                'criteria': [{'id': 'layout_readability', 'score': 5}]},
            'task_completion': {'valid': True, 'passed': False, 'coverage': 1,
                                'requirements': [{'status': 'met'}]},
            'duration_validation': {'valid': True}, 'consistency_review': {'valid': True},
            'narration_required': True, 'speech_transcript': {'valid': True},
            'narration_review': {'valid': True, 'passed': False, 'criteria': [{'score': 5}]}}


class DimensionScoringTests(unittest.TestCase):
    def test_acceptance_is_derived_from_dimensions_not_legacy_booleans(self):
        result = apply(fixture())
        self.assertTrue(result['scoring']['strict_pass'])
        gate = assess({'complete': True, 'timing': {'valid': True}}, result)
        self.assertTrue(gate['passed'])
        self.assertEqual(gate['failures'], [])

    def test_layout_failure_is_scored_in_presentation_only(self):
        row = fixture()
        before = apply(row)
        after = apply(row, {'complete': True, 'timing': {'valid': True},
                           'strict_diagnostics': {'layout': {'valid': False}}})
        self.assertEqual(after['dimensions']['instructional_presentation']['score'], 50)
        self.assertEqual(after['dimensions']['conceptual_correctness'], before['dimensions']['conceptual_correctness'])
        self.assertIn('instructional_presentation', after['scoring']['dimension_failures'])

    def test_missing_evidence_is_unverified_and_not_a_quality_failure(self):
        row = fixture(); row['narration_review'] = {'valid': False}
        result = apply(row)
        self.assertIsNone(result['dimensions']['spoken_teaching']['score'])
        self.assertIsNone(result['scoring']['score'])
        self.assertEqual(result['scoring']['evaluation_status'], 'unverified')
        self.assertNotIn('spoken_teaching', result['scoring']['dimension_failures'])

    def test_task_coverage_affects_its_dimension_and_teaching_group_only(self):
        row = fixture(); before = apply(row)
        row['task_completion'].update(coverage=.25, requirements=[{'status': 'missing'}])
        after = apply(row)
        self.assertEqual(after['dimensions']['task_completeness']['score'], 25)
        self.assertEqual(after['scoring']['groups']['video_quality'], before['scoring']['groups']['video_quality'])
        self.assertLess(after['scoring']['score'], before['scoring']['score'])
        self.assertIn('task_completeness', after['scoring']['dimension_failures'])

    def test_timing_is_a_reported_dimension_not_an_extra_veto(self):
        result = apply(fixture())
        gate = assess({'complete': True, 'timing': {'valid': False}}, result)
        self.assertFalse(gate['passed'])
        self.assertIn('instruction_following', gate['failures'])
        self.assertEqual(result['dimensions']['instruction_following']['score'], 0)
        self.assertTrue(result['scoring']['valid'])
        self.assertGreater(result['scoring']['score'], 0)

    def test_unavailable_video_has_no_stale_numeric_scores(self):
        result = apply(fixture(), {'complete': False})
        self.assertTrue(all(d['score'] is None for d in result['dimensions'].values()))
        self.assertEqual(result['scoring']['evaluation_status'], 'unavailable_video')

    def test_uncertain_requirement_is_not_counted_as_zero(self):
        row = fixture(); row['task_completion']['requirements'][0]['status'] = 'uncertain'
        self.assertIsNone(apply(row)['dimensions']['task_completeness']['score'])

    def test_version_dispatch_and_historical_policy_are_separate(self):
        from eval.quality_scoring import apply as dispatch
        with patch.dict('os.environ', {'VIDEO_TEACHER_SCORING_POLICY': 'quality-v13'}):
            self.assertEqual(dispatch(fixture())['version'], VERSION)
        with patch.dict('os.environ', {'VIDEO_TEACHER_SCORING_POLICY': 'quality-v12'}):
            self.assertEqual(dispatch(fixture())['version'], 'video-teacher-quality-v12')

    def test_repeat_assessment_does_not_accumulate_penalties_or_mutate_input(self):
        row = fixture(); before = copy.deepcopy(row)
        first = apply(row)
        self.assertEqual(row, before)
        self.assertEqual(first, apply(first))

    def test_report_uses_dimension_results_and_separates_unknown_cases(self):
        from eval.run_benchmark_v2 import report
        good = fixture(); good['id'] = 'good'
        unknown = fixture(); unknown['id'] = 'unknown'; unknown['narration_review'] = {'valid': False}
        rows = [apply(good), apply(unknown)]
        reported = report(rows, {k: {'audio_narration_required': True} for k in ('good', 'unknown')})
        self.assertEqual(reported['spoken_teaching']['n_passed'], 1)
        self.assertEqual(reported['spoken_teaching']['unverified_ids'], ['unknown'])
        self.assertEqual(reported['spoken_teaching']['failed_ids'], [])
        self.assertFalse(reported['ranking_publishable'])
        self.assertIsNone(reported['ranking_score'])

    def test_long_video_missing_window_review_is_unverified(self):
        row = fixture()
        row['duration_validation']['duration_seconds'] = 120
        row['instructional_presentation'].pop('all_windows_reviewed')
        result = apply(row)
        self.assertEqual(result['scoring']['evaluation_status'], 'unverified')
        self.assertIn('incomplete_video_review', result['scoring']['errors'])
        self.assertIsNone(result['scoring']['score'])
