import copy
import unittest
from pathlib import Path

from PIL import ImageChops

from generation.contract_frame import render_first_frame
from generation.teaching_contract import load_contracts


ROOT = Path(__file__).resolve().parent.parent


class ContractFrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts = load_contracts(ROOT / "data/teaching_contracts/examples.jsonl")

    def test_all_examples_render_at_video_aspect_ratio(self):
        for contract in self.contracts.values():
            with self.subTest(case=contract["id"]):
                image = render_first_frame(contract)
                self.assertEqual(image.size, (832, 480))
                self.assertIsNotNone(ImageChops.difference(
                    image, image.copy().convert("RGB").point(lambda _: 255)
                ).getbbox())

    def test_drawing_reads_knowledge_state(self):
        original = self.contracts["chem_exp_01"]
        changed = copy.deepcopy(original)
        changed["beat"]["pre_state"]["valence_electrons"][0] = 2
        a = render_first_frame(original)
        b = render_first_frame(changed)
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_setup_and_result_are_distinct(self):
        lens = self.contracts["phys_exp_02"]
        a = render_first_frame(lens, phase="setup")
        b = render_first_frame(lens, phase="result")
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())


if __name__ == "__main__":
    unittest.main()
