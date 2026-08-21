import unittest

from scripts.compare_standard_eval import compare_metric, holm_adjust, paired_stats, score


class CompareStandardEvalTest(unittest.TestCase):
    def test_extracts_aggregate_and_dimension_scores(self):
        row = {"aggregate_score": 2.5, "visual_quality": {"score": 3.25}}
        self.assertEqual(score(row, "aggregate_score"), 2.5)
        self.assertEqual(score(row, "visual_quality"), 3.25)

    def test_rejects_boolean_and_non_finite_scores(self):
        self.assertIsNone(score({"aggregate_score": True}, "aggregate_score"))
        self.assertIsNone(score({"aggregate_score": float("nan")}, "aggregate_score"))

    def test_comparison_uses_only_jointly_scored_cases(self):
        left = {"a": {"aggregate_score": 2}, "b": {"aggregate_score": 4}, "c": {}}
        right = {"a": {"aggregate_score": 1}, "b": {"aggregate_score": 2}, "c": {"aggregate_score": 3}}
        result = compare_metric(left, right, "aggregate_score", seed=1, draws=100)
        self.assertEqual(result["case_ids"], ["a", "b"])
        self.assertEqual(result["mean_difference"], 1.5)

    def test_constant_difference_has_undefined_standardized_effect(self):
        result = paired_stats([1.0, 1.0], seed=1, draws=100)
        self.assertIsNone(result["cohens_dz"])

    def test_holm_adjustment_is_monotone_in_sorted_order(self):
        adjusted = holm_adjust([0.04, 0.01, 0.03])
        self.assertEqual(adjusted, [0.06, 0.03, 0.06])

    def test_draw_count_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "draws"):
            paired_stats([0.1, 0.2], seed=1, draws=0)


if __name__ == "__main__":
    unittest.main()
