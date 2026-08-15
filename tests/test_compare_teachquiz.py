import unittest

from scripts.compare_teachquiz import compare, paired_stats, validate_comparable


def protocol(**overrides):
    value = {
        "student": "qwen",
        "quiz_sha256": "frozen",
        "probe_origin": "frozen_shared",
        "cross_model_comparable": True,
        "random_control": "seeded_matched",
        "random_seed": 7,
        "match_priority": ["discipline", "task_type", "difficulty"],
        "max_baseline_score": 0.8,
        "n_frames": 8,
        "frame_max_px": 384,
        "max_questions": None,
    }
    value.update(overrides)
    return value


class CompareTeachQuizTest(unittest.TestCase):
    def test_rejects_protocol_difference(self):
        with self.assertRaisesRegex(ValueError, "random_seed"):
            validate_comparable(protocol(), protocol(random_seed=8))

    def test_rejects_model_specific_probes(self):
        with self.assertRaisesRegex(ValueError, "frozen_shared"):
            validate_comparable(
                protocol(probe_origin="model_specific", cross_model_comparable=False),
                protocol(),
            )

    def test_joint_valid_comparison_uses_shared_valid_intersection(self):
        left = {
            "a": {"normalized_gain": 0.8, "valid": True},
            "b": {"normalized_gain": 0.4, "valid": True},
            "c": {"normalized_gain": 0.6, "valid": True},
            "left-only": {"normalized_gain": 1.0, "valid": True},
        }
        right = {
            "a": {"normalized_gain": 0.3, "valid": True},
            "b": {"normalized_gain": 0.1, "valid": False},
            "c": {"normalized_gain": 0.2, "valid": True},
        }
        result = compare(
            left, right, valid_only=True, metric="normalized_gain", seed=1, draws=100
        )
        self.assertEqual(result["case_ids"], ["a", "c"])

    def test_constant_differences_have_json_safe_undefined_effect(self):
        result = paired_stats([0.25, 0.25], seed=1, draws=100)
        self.assertEqual(result["mean_difference"], 0.25)
        self.assertIsNone(result["paired_standardized_effect"])

    def test_draw_count_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "draws"):
            paired_stats([0.1, 0.2], seed=1, draws=0)


if __name__ == "__main__":
    unittest.main()
