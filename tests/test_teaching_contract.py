import copy
import json
import unittest
from pathlib import Path

from generation.teaching_contract import (
    ContractError, RefinementExhausted, load_contracts, prepare_cases,
    refine_contract, validate_contract,
)


ROOT = Path(__file__).resolve().parent.parent


class TeachingContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts = load_contracts(ROOT / "data/teaching_contracts/examples.jsonl")
        cls.prompts = {
            row["id"]: row for row in (
                json.loads(line) for line in
                (ROOT / "data/prompts/pilot_v0_1.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }

    def test_three_disciplines_compile_without_video_generation(self):
        cases = [self.prompts[case_id] for case_id in self.contracts]
        compiled = prepare_cases(cases, self.contracts, 832, 480, 121, 24)
        self.assertEqual(len(compiled), 3)
        for case in compiled:
            self.assertEqual(len(case["teaching_contract_sha256"]), 64)
            self.assertIn("ONE observable step", case["video_prompt"])
            self.assertNotIn("Generate a video", case["video_prompt"])
        self.assertEqual(cases[0].get("video_prompt"), None)

    def test_rejects_state_change_disagreement_and_false_domain_check(self):
        contract = copy.deepcopy(self.contracts["phys_exp_02"])
        case = self.prompts["phys_exp_02"]
        contract["beat"]["changes"] = ["ray_stage"]
        with self.assertRaisesRegex(ContractError, "declared changes"):
            validate_contract(contract, case, 832, 480, 121 / 24)
        contract = copy.deepcopy(self.contracts["phys_exp_02"])
        contract["beat"]["pre_state"]["focus"]["y"] = 300
        contract["beat"]["post_state"]["focus"]["y"] = 300
        contract["invariants"]["focus"]["y"] = 300
        with self.assertRaisesRegex(ContractError, "equals failed"):
            validate_contract(contract, case, 832, 480, 121 / 24)

    def test_rejects_overlapping_or_tiny_text_and_wrong_duration(self):
        contract = copy.deepcopy(self.contracts["math_prob_02"])
        case = self.prompts["math_prob_02"]
        contract["layout"][1]["rect"] = contract["layout"][0]["rect"]
        with self.assertRaisesRegex(ContractError, "layout overlap"):
            validate_contract(contract, case, 832, 480, 121 / 24)
        contract = copy.deepcopy(self.contracts["math_prob_02"])
        contract["layout"][0]["font_px"] = 8
        with self.assertRaisesRegex(ContractError, "minimum readable size"):
            validate_contract(contract, case, 832, 480, 121 / 24)
        contract = copy.deepcopy(self.contracts["math_prob_02"])
        with self.assertRaisesRegex(ContractError, "differs from requested"):
            validate_contract(contract, case, 832, 480, 49 / 24)

    def test_rejects_low_contrast_text(self):
        contract = copy.deepcopy(self.contracts["math_prob_02"])
        contract["layout"][0]["color"] = "#eeeeee"
        with self.assertRaisesRegex(ContractError, "contrast"):
            validate_contract(contract, self.prompts["math_prob_02"], 832, 480, 121 / 24)

    def test_schema_is_not_tied_to_subject_or_case_id(self):
        contract = {
            "id": "new_history_case", "target_duration_s": 5,
            "learning_objective": "Place two historical events in order",
            "beat": {
                "claim": "Move the second event to its correct later position",
                "pre_state": {"first_year": 1914, "second_year": 1914, "scale": "years"},
                "post_state": {"first_year": 1914, "second_year": 1918, "scale": "years"},
                "changes": ["second_year"],
                "visible_evidence": ["1914 appears before 1918 on one axis"],
            },
            "invariants": {"first_year": 1914, "scale": "years"},
            "checks": [{"type": "greater_than", "left": {"path": "post.second_year"},
                        "right": {"path": "post.first_year"}}],
            "layout": [
                {"id": "title", "kind": "text", "text": "Timeline", "font_px": 28,
                 "rect": [0.05, 0.05, 0.95, 0.16]},
                {"id": "timeline", "kind": "diagram", "rect": [0.06, 0.3, 0.94, 0.83]},
            ],
        }
        case = {"id": "new_history_case", "discipline": "history", "prompt_text": "old long prompt"}
        # Generic state, assertion, and layout checks work for a new domain.
        validate_contract(contract, case, 832, 480, 121 / 24)

    def test_bounded_revision_repairs_layout_and_records_attempts(self):
        initial = copy.deepcopy(self.contracts["math_prob_02"])
        correct_rect = initial["layout"][1]["rect"]
        initial["layout"][1]["rect"] = initial["layout"][0]["rect"]

        def revise(draft, reason, round_number):
            self.assertIn("overlap", reason)
            self.assertEqual(round_number, 2)
            draft["layout"][1]["rect"] = correct_rect
            return draft

        accepted, attempts = refine_contract(
            initial, self.prompts["math_prob_02"], 832, 480, 121 / 24,
            revise, max_rounds=2,
        )
        self.assertEqual(accepted["layout"][1]["rect"], correct_rect)
        self.assertEqual([a["status"] for a in attempts], ["rejected", "accepted"])
        self.assertNotEqual(attempts[0]["sha256"], attempts[1]["sha256"])

    def test_revision_cannot_change_frozen_truth(self):
        initial = copy.deepcopy(self.contracts["phys_exp_02"])
        initial["layout"][0]["font_px"] = 8

        def revise(draft, _reason, _round):
            draft["layout"][0]["font_px"] = 27
            draft["beat"]["post_state"]["axis_y"] = 300
            return draft

        with self.assertRaises(RefinementExhausted) as caught:
            refine_contract(initial, self.prompts["phys_exp_02"], 832, 480,
                            121 / 24, revise, max_rounds=3)
        self.assertEqual(len(caught.exception.attempts), 2)
        self.assertIn("frozen", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
