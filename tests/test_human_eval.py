import importlib.util
import argparse
import json
import tempfile
import unittest
import math
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "human_eval.py"
SPEC = importlib.util.spec_from_file_location("human_eval", MODULE)
human_eval = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(human_eval)


class HumanEvalStatsTest(unittest.TestCase):
    def test_ordinal_alpha_is_one_for_identical_raters(self):
        alpha = human_eval.krippendorff_alpha_ordinal([[1, 1, 1], [3, 3, 3], [5, 5, 5]])
        self.assertAlmostEqual(alpha, 1.0)

    def test_spearman_handles_ties_and_monotonic_data(self):
        self.assertAlmostEqual(human_eval.spearman([1, 2, 2, 5], [1, 3, 3, 4]), 1.0)

    def test_bootstrap_handles_constant_samples_without_crashing(self):
        point, low, high = human_eval.bootstrap_spearman([2] * 8, [3] * 8, seed=1, draws=50)
        self.assertTrue(math.isnan(point))
        self.assertTrue(math.isnan(low))
        self.assertTrue(math.isnan(high))

    def test_stratified_sample_is_deterministic_and_bounded(self):
        rows = [
            {"id": str(i), "discipline": "d" + str(i % 2), "task_type": "t" + str(i % 2), "difficulty": "k12"}
            for i in range(10)
        ]
        first = human_eval.stratified_sample(rows, 6, 42)
        second = human_eval.stratified_sample(rows, 6, 42)
        self.assertEqual([r["id"] for r in first], [r["id"] for r in second])
        self.assertEqual(len({r["id"] for r in first}), 6)

    def test_export_and_analyse_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts = root / "prompts.jsonl"; manifest = root / "manifest.jsonl"; judge = root / "judge.jsonl"
            cases = [{"id": f"c{i}", "discipline": "math", "task_type": "explanation", "difficulty": "k12", "prompt_text": "teach"} for i in range(4)]
            prompts.write_text("\n".join(map(json.dumps, cases)) + "\n")
            manifest.write_text("\n".join(json.dumps({"id": f"c{i}", "status": "ok", "video_path": f"c{i}.mp4"}) for i in range(4)) + "\n")
            judge.write_text("\n".join(json.dumps({"id": f"c{i}", "conceptual_correctness": {"score": i + 1}}) for i in range(4)) + "\n")
            session = root / "session"
            human_eval.export(argparse.Namespace(prompts=str(prompts), manifest=str(manifest), judge=str(judge), out=str(session), n_cases=4, raters=2, seed=7))
            assignments = human_eval.read_jsonl(session / "assignments.jsonl")
            rater_one = human_eval.read_jsonl(session / "raters" / "rater_01.jsonl")
            study_manifest = json.loads((session / "study_manifest.json").read_text())
            self.assertEqual(len(rater_one), 4)
            self.assertEqual({row["rater_id"] for row in rater_one}, {"rater_01"})
            self.assertEqual(study_manifest["rater_assignment_files"], [
                "raters/rater_01.jsonl", "raters/rater_02.jsonl",
            ])
            responses = [{"assignment_id": a["assignment_id"], "rater_id": a["rater_id"], "scores": {"conceptual_correctness": int(a["case_id"][1:]) + 1}} for a in assignments]
            human_eval.write_jsonl(session / "responses.jsonl", responses)
            output = root / "report.md"
            human_eval.analyse(argparse.Namespace(assignments=str(session / "assignments.jsonl"), responses=str(session / "responses.jsonl"), judge=str(judge), out=str(output), seed=7))
            self.assertIn("1.000", output.read_text())
            report = json.loads(output.with_suffix(".json").read_text())
            self.assertIsNone(report["dimensions"]["narrative_structure"]["ordinal_alpha"])

    def test_analyse_rejects_boolean_and_float_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assignments = root / "assignments.jsonl"
            responses = root / "responses.jsonl"
            judge = root / "judge.jsonl"
            human_eval.write_jsonl(assignments, [{
                "assignment_id": "a1", "rater_id": "r1", "case_id": "c1",
                "dimensions": ["conceptual_correctness", "visual_quality"],
            }])
            human_eval.write_jsonl(responses, [{
                "assignment_id": "a1", "rater_id": "r1",
                "scores": {"conceptual_correctness": True, "visual_quality": 3.0},
            }])
            human_eval.write_jsonl(judge, [{
                "id": "c1", "conceptual_correctness": {"score": 1},
                "visual_quality": {"score": 3},
            }])
            output = root / "report.md"
            human_eval.analyse(argparse.Namespace(
                assignments=str(assignments), responses=str(responses), judge=str(judge),
                out=str(output), seed=7,
            ))
            report = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual(len(report["rejected"]), 2)
            self.assertEqual(report["dimensions"]["conceptual_correctness"]["n_videos"], 0)


if __name__ == "__main__":
    unittest.main()
