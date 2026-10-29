import json
import unittest
from pathlib import Path

from scripts.build_candidate_400 import (DISCIPLINEGEN_FACT_REPAIRS, REPLACEMENTS,
                                         focus_multisource, focus_pilot, source_additions)


ROOT = Path(__file__).resolve().parents[1]


class Candidate400Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data/prompts/multisource_pilot_300.jsonl"
        cls.multisource = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_short_source_focus_preserves_complete_instruction(self):
        original = next(row for row in self.multisource if row["id"] == "grade_biology_task_16")
        revised = focus_multisource(original)
        self.assertIn(original["source"]["original_instruction"], revised["prompt_text"])
        self.assertEqual(revised["original_prompt_text"], original["prompt_text"])
        self.assertEqual(len(revised["expected_narrative_order"]), 3)
        self.assertNotIn("original_prompt_text", original)

    def test_verified_replacements_keep_source_and_answer(self):
        additions = {row["id"]: row for row in source_additions()}
        self.assertEqual(set(additions), set(REPLACEMENTS.values()))
        candidate_ids = {json.loads(line)["id"] for line in
                         (ROOT / "data/prompts/candidate_400.jsonl").read_text(encoding="utf-8").splitlines()}
        self.assertEqual(len(candidate_ids), 400)
        self.assertTrue(set(REPLACEMENTS).isdisjoint(candidate_ids))
        self.assertTrue(set(additions) <= candidate_ids)
        for row in additions.values():
            self.assertTrue(row["source"]["source_id"])
            self.assertTrue(row["discipline_specific_rubric"])
            if row["source"]["dataset"] == "GRADE":
                self.assertTrue(row["source"]["source_image_path"].startswith("image/before/"))
                self.assertTrue(row["source"]["target_image_path"].startswith("image/gt/"))

    def test_food_chain_repair_removes_unsupported_link(self):
        original = next(row for row in self.multisource if row["id"] == "grade_biology_task_10")
        revised = focus_multisource(original)
        self.assertIn("bear unconnected", revised["prompt_text"])
        self.assertTrue(any("no fox" in rule for rule in revised["discipline_specific_rubric"]))
        self.assertEqual(revised["source"], original["source"])
        self.assertEqual(revised["curation"]["visual_pair_screening"]["status"], "target_rejected")

    def test_grade_targets_with_unrequested_edits_are_not_scoring_references(self):
        cases = {row["id"]: row for row in self.multisource}
        for case_id in ("grade_biology_task_22", "grade_biology_task_24"):
            revised = focus_multisource(cases[case_id])
            self.assertEqual(revised["curation"]["visual_pair_screening"]["status"],
                             "target_rejected")

    def test_meiosis_repair_does_not_infer_mutation(self):
        original = next(row for row in self.multisource
                        if row["id"] == "disciplinegen_biology_26fdde9159c8433d")
        revised = focus_multisource(original)
        self.assertIn("Do not infer a mutation", revised["prompt_text"])
        self.assertEqual(len(revised["expected_narrative_order"]), 3)

    def test_disciplinegen_factual_repairs(self):
        cases = {row["id"]: row for row in self.multisource}
        cube = focus_multisource(cases["disciplinegen_physics_3df388cfbe3545a0"])
        self.assertIn("+L/2", cube["prompt_text"])
        self.assertNotIn("x = L, y = L", cube["prompt_text"])
        music = focus_multisource(cases["disciplinegen_music_6a04a0734f94075b"])
        self.assertIn("1½+½+2=4", music["prompt_text"])
        hydrazide = focus_multisource(cases["disciplinegen_chemistry_4f1bae22d9795083"])
        self.assertIn("para-methoxyphenyl", hydrazide["prompt_text"])
        self.assertNotIn("\"]", hydrazide["prompt_text"])

    def test_long_source_is_not_silently_truncated(self):
        original = next(row for row in self.multisource
                        if len(row["source"].get("original_annotation", "")) > 300
                        and row["id"] != "disciplinegen_biology_26fdde9159c8433d"
                        and row["id"] not in DISCIPLINEGEN_FACT_REPAIRS)
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
