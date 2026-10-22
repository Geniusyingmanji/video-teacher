import json
import unittest
from pathlib import Path

from scripts.build_candidate_400 import focus_multisource, focus_pilot


ROOT = Path(__file__).resolve().parents[1]


class Candidate400Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data/prompts/multisource_pilot_300.jsonl"
        cls.multisource = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_short_source_focus_preserves_complete_instruction(self):
        original = next(row for row in self.multisource if row["id"] == "grade_biology_task_10")
        revised = focus_multisource(original)
        self.assertIn(original["source"]["original_instruction"], revised["prompt_text"])
        self.assertEqual(revised["original_prompt_text"], original["prompt_text"])
        self.assertEqual(len(revised["expected_narrative_order"]), 3)
        self.assertNotIn("original_prompt_text", original)

    def test_long_source_is_not_silently_truncated(self):
        original = next(row for row in self.multisource
                        if len(row["source"].get("original_annotation", "")) > 300)
        revised = focus_multisource(original)
        self.assertEqual(revised["prompt_text"], original["prompt_text"])
        self.assertIn("manual_atomic_scope_required", revised["curation"]["quality_flags"])

    def test_pilot_duration_matches_target(self):
        path = ROOT / "data/prompts/pilot_v0_2.jsonl"
        original = next(row for line in path.read_text(encoding="utf-8").splitlines()
                        if (row := json.loads(line))["id"] == "math_exp_01")
        revised = focus_pilot(original)
        self.assertEqual(revised["target_duration_s"], 5)
        self.assertIn("5-second", revised["prompt_text"])
        self.assertEqual(revised["original_prompt_text"], original["prompt_text"])


if __name__ == "__main__":
    unittest.main()
