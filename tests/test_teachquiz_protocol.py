import random
import tempfile
import unittest
from pathlib import Path

from eval.dimensions.learning_gain import learning_gain
from eval.run_teachquiz import (
    build_aggregate,
    choose_random_manifest,
    validate_quiz_rows,
    ensure_protocol,
)


class TeachQuizProtocolTest(unittest.TestCase):
    def test_reports_raw_control_adjusted_and_legacy_gain(self):
        result = learning_gain(
            pre_score=0.25, post_score=0.75, random_score=0.5
        )
        self.assertEqual(result["raw_gain"], 0.5)
        self.assertEqual(result["control_adjusted_gain"], 0.25)
        self.assertEqual(result["learning_gain"], 0.25)
        self.assertEqual(result["normalized_gain"], 0.5)

    def test_control_prefers_metadata_match_and_is_order_stable(self):
        prompts = {
            "target": {"discipline": "math", "task_type": "explanation", "difficulty": "k12"},
            "exact": {"discipline": "math", "task_type": "explanation", "difficulty": "k12"},
            "wrong_task": {"discipline": "math", "task_type": "problem_solving", "difficulty": "k12"},
            "wrong_subject": {"discipline": "physics", "task_type": "explanation", "difficulty": "k12"},
        }
        manifest = [{"id": key, "status": "ok"} for key in prompts]
        first = choose_random_manifest(manifest, "target", random.Random(7), prompts)
        second = choose_random_manifest(list(reversed(manifest)), "target", random.Random(7), prompts)
        self.assertEqual(first["id"], "exact")
        self.assertEqual(first["id"], second["id"])

    def test_aggregate_includes_new_gain_metrics(self):
        rows = [{
            "id": "x", "valid": True, "positive_gain": True,
            "discipline": "math", "task_type": "explanation",
            "pre": {"score": 0.0}, "post_video": {"score": 1.0},
            "random_video": {"score": 0.5}, "learning_gain": 0.5,
            "raw_gain": 1.0, "control_adjusted_gain": 0.5,
            "normalized_gain": 1.0,
        }]
        overall = build_aggregate(rows)["overall"]
        self.assertEqual(overall["raw_gain"], 1.0)
        self.assertEqual(overall["control_adjusted_gain"], 0.5)

    def test_quiz_validation_rejects_duplicate_question_ids(self):
        rows = [
            {"case_id": "a", "quiz": [{"id": "q", "choices": ["x", "y"], "answer": "A"}]},
            {"case_id": "b", "quiz": [{"id": "q", "choices": ["x", "y"], "answer": "B"}]},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate question id"):
            validate_quiz_rows(rows)

    def test_resume_rejects_changed_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "protocol.json"
            ensure_protocol(path, {"quiz_sha256": "first", "student": "learner"})
            ensure_protocol(path, {"quiz_sha256": "first", "student": "learner"})
            with self.assertRaisesRegex(RuntimeError, "quiz_sha256"):
                ensure_protocol(path, {"quiz_sha256": "second", "student": "learner"})


if __name__ == "__main__":
    unittest.main()
