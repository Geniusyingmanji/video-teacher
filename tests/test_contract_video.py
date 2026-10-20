import copy
import unittest
from pathlib import Path

from generation.teaching_contract import ContractError, load_contracts, validate_contract


ROOT = Path(__file__).resolve().parent.parent


class AnimatedContractTruthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts = load_contracts(ROOT / "data/teaching_contracts/examples.jsonl")

    def test_wrong_final_derivative_is_rejected(self):
        contract = copy.deepcopy(self.contracts["math_prob_02"])
        contract["beat"]["post_state"]["final_derivative"] = "3x² + 3"
        with self.assertRaisesRegex(ContractError, "failed"):
            validate_contract(contract, {"id": "math_prob_02"}, 832, 480, 5)

    def test_ray_must_reach_focus(self):
        contract = copy.deepcopy(self.contracts["phys_exp_02"])
        contract["beat"]["post_state"]["outgoing_endpoints"][0][0] = 0.75
        with self.assertRaisesRegex(ContractError, "failed"):
            validate_contract(contract, {"id": "phys_exp_02"}, 832, 480, 5)

    def test_electron_transfer_count_is_fixed(self):
        contract = copy.deepcopy(self.contracts["chem_exp_01"])
        contract["beat"]["post_state"]["valence_electrons"] = [1, 7]
        with self.assertRaises(ContractError):
            validate_contract(contract, {"id": "chem_exp_01"}, 832, 480, 5)


if __name__ == "__main__":
    unittest.main()
