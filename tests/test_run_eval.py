import unittest

from eval import run_eval
from scripts import dim_correlation


class RunEvalAggregationTest(unittest.TestCase):
    def test_correlation_score_extraction_preserves_zero(self):
        self.assertEqual(dim_correlation.extract_dim_score({"quality": {"score": 0}}, "quality"), 0.0)
        self.assertIsNone(dim_correlation.extract_dim_score({"quality": {"score": "nan"}}, "quality"))

    def test_dimension_score_preserves_zero_and_rejects_non_finite(self):
        self.assertEqual(run_eval.dimension_score({"score": 0, "final_score": 4}), 0.0)
        self.assertEqual(run_eval.dimension_score({"final_score": "2.5"}), 2.5)
        self.assertIsNone(run_eval.dimension_score({"score": float("nan")}))
        self.assertIsNone(run_eval.dimension_score({"score": "bad"}))

    def test_aggregate_excludes_partial_dimension_failures(self):
        dims = {"conceptual_correctness": object(), "visual_quality": object()}
        prompts = {
            "good": {"discipline": "math", "task_type": "explanation", "difficulty": "k12"},
            "partial": {"discipline": "math", "task_type": "explanation", "difficulty": "k12"},
        }
        results = [
            {
                "id": "good", "aggregate_score": 2.0, "strict_pass": False,
                "conceptual_correctness": {"score": 0},
                "visual_quality": {"final_score": 4},
            },
            {
                "id": "partial", "aggregate_score": 5.0, "strict_pass": True,
                "conceptual_correctness": {"score": 5},
                "visual_quality": {"error": "judge timeout"},
            },
        ]

        report = run_eval.aggregate(results, prompts, dims)

        self.assertEqual(report["n_total"], 2)
        self.assertEqual(report["n_valid"], 1)
        self.assertEqual(report["n_failed"], 1)
        self.assertEqual(report["mean_aggregate"], 2.0)
        self.assertEqual(report["per_dim_mean"]["conceptual_correctness"], 0.0)
        self.assertEqual(report["per_dim_mean"]["visual_quality"], 4.0)
        self.assertEqual(report["per_discipline"]["math"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
