import copy
import base64
import io
import json
import unittest
from pathlib import Path

from PIL import Image

from generation.interactive_lesson import compile_lesson
from generation.teaching_contract import ContractError, load_contracts


ROOT = Path(__file__).resolve().parent.parent


class InteractiveLessonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / "data/interactive/convex_lens.json").read_text(encoding="utf-8"))
        cls.contracts = load_contracts(ROOT / "data/teaching_contracts/examples.jsonl")

    def test_three_branches_compile_to_distinct_verified_results(self):
        lesson = compile_lesson(self.spec, self.contracts)
        self.assertEqual(lesson["reference_variant_id"], "baseline")
        self.assertEqual(len(lesson["variants"]), 3)
        self.assertEqual(len({v["result_image"] for v in lesson["variants"]}), 3)
        for variant in lesson["variants"]:
            self.assertNotEqual(variant["setup_image"], variant["result_image"])
            self.assertEqual(len(variant["animation_images"]), 6)
            self.assertNotEqual(variant["animation_images"][0], variant["result_image"])
            self.assertEqual(variant["animation_images"][-1], variant["result_image"])
        for variant, focus_x in zip(lesson["variants"], (0.68, 0.82, 0.92)):
            image = Image.open(io.BytesIO(base64.b64decode(
                variant["result_image"].split(",", 1)[1]
            )))
            red, green, blue = image.getpixel((round(focus_x * 832), 240))
            self.assertLess(red, 70)
            self.assertLess(green, 100)
            self.assertLess(blue, 130)

    def test_invalid_ray_endpoint_rejected_before_export(self):
        spec = copy.deepcopy(self.spec)
        spec["variants"][0]["overrides"]["beat.post_state.outgoing_endpoints"][1][1] = 0.6
        with self.assertRaisesRegex(ContractError, "failed"):
            compile_lesson(spec, self.contracts)

    def test_invariant_change_requires_consistent_updates(self):
        spec = copy.deepcopy(self.spec)
        del spec["variants"][0]["overrides"]["invariants.focus"]
        with self.assertRaisesRegex(ContractError, "invariant"):
            compile_lesson(spec, self.contracts)

    def test_variants_cannot_rewrite_checks(self):
        spec = copy.deepcopy(self.spec)
        spec["variants"][0]["overrides"]["checks.0"] = {}
        with self.assertRaisesRegex(ContractError, "cannot edit"):
            compile_lesson(spec, self.contracts)


if __name__ == "__main__":
    unittest.main()
