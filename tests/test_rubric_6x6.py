import unittest

from eval.rubric_6x6 import RUBRIC, validate_result
from eval.run_eval import aggregate
from generation.short_clip_prompt import focused_prompt, select_action


class Rubric6x6Test(unittest.TestCase):
    def test_registry_has_six_distinct_criteria_per_dimension(self):
        self.assertEqual(len(RUBRIC), 6)
        for criteria in RUBRIC.values():
            self.assertEqual(len(criteria), 6)
            self.assertEqual(len({row[0] for row in criteria}), 6)

    def test_result_requires_complete_evidence_and_hard_gate(self):
        dimension = "visual_quality"
        rows = [dict(id=key, applicable=True, score=5,
                     evidence_frames=[1, 4], finding="Visible in the sampled frames")
                for key, _ in RUBRIC[dimension]]
        good = validate_result(dimension, {"criteria": rows}, 8)
        self.assertEqual(good["score"], 5)
        self.assertEqual(good["binary"], "PASS")
        rows[1]["score"] = 2
        self.assertEqual(validate_result(dimension, {"criteria": rows}, 8)["binary"], "FAIL")
        rows[1]["evidence_frames"] = [9]
        with self.assertRaises(ValueError):
            validate_result(dimension, {"criteria": rows}, 8)

    def test_focused_prompt_selects_one_change_and_preserves_text(self):
        case = {"expected_narrative_order": ["show curve", "place point",
                                             "slide point and tangent together", "hold result"]}
        self.assertEqual(select_action(case), "slide point and tangent together")
        prompt = focused_prompt(case, 3.0)
        self.assertIn("3.0-second", prompt)
        self.assertIn("slide point and tangent together", prompt)
        self.assertIn("Do not redraw or alter existing text", prompt)

    def test_aggregate_reports_criterion_failures(self):
        dim = "visual_quality"
        row = {"id": "x", "aggregate_score": 2.0, "strict_pass": False,
               dim: {"score": 2.0, "criteria": [
                   {"id": "legibility", "applicable": True, "score": 2}]}}
        result = aggregate([row], {"x": {"discipline": "math"}}, {dim: object()})
        self.assertEqual(result["per_criterion"][dim]["legibility"]["low_1_or_2"], 1)


if __name__ == "__main__":
    unittest.main()
