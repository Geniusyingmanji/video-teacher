import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from eval import benchmark_operators as op
from eval import benchmark_scoring as scoring
from eval import compare_benchmark_v2 as comparison
from eval import benchmark_video_rubric as video_rubric
from eval import run_benchmark_v2 as runner


class ScoringPolicyTests(unittest.TestCase):
    def setUp(self):
        self.axes = {a: 80 for names in scoring.GROUPS.values() for a in names}

    def test_equal_categories_and_strict_gate(self):
        self.axes.update({a: 100 for a in scoring.VIDEO_AXES})
        self.axes.update({a: 60 for a in scoring.TEACHING_AXES})
        result = scoring.score_case(self.axes)
        self.assertEqual(result["score"], 80)
        self.assertFalse(result["strict_pass"])

    def test_missing_nan_bool_and_required_audio_invalidate(self):
        for bad in (None, float("nan"), True, -1, 101):
            axes = dict(self.axes, visual_quality=bad)
            self.assertFalse(scoring.score_case(axes)["valid"])
        audio_missing = scoring.score_case(self.axes, narration_required=True,
                                           narration_detected=False)
        self.assertTrue(audio_missing["valid"])
        self.assertEqual(audio_missing["score"], 40)
        self.assertFalse(audio_missing["strict_pass"])
        self.assertFalse(scoring.score_case(self.axes, narration_required=True,
                                            narration_detected=None)["valid"])

    def test_incomplete_run_has_no_ranking(self):
        valid = {"id": "a", "axes": {a: {"score": v} for a, v in self.axes.items()},
                 "scoring": scoring.score_case(self.axes)}
        invalid = {"id": "b", "axes": {}, "scoring": scoring.score_case({})}
        rep = scoring.aggregate([valid, invalid])
        self.assertIsNone(rep["ranking_score"])
        self.assertFalse(rep["ranking_publishable"])
        self.assertEqual(rep["n_failed"], 1)

    def test_visible_intrusion_and_wrong_text_cannot_average_away(self):
        axes = dict(self.axes)
        axes["visual_quality"] = 95
        axes["conceptual_correctness"] = 90
        results = {
            "visual_quality": {"criteria": [{"id": "artifact_control", "applicable": True,
                                               "score": 2, "evidence_frames": [2],
                                               "finding": "unrelated hand covers the diagram"}]},
            "conceptual_correctness": {"criteria": [{"id": "symbols", "applicable": True,
                                                       "score": 1, "evidence_frames": [3],
                                                       "finding": "equation mutates"}]},
        }
        defects = scoring.evidence_defects(results)
        scored = scoring.score_case(axes, defects=defects)
        self.assertEqual(len(defects), 2)
        self.assertEqual(scored["score"], 50)
        self.assertEqual(scored["axis_scores_after_caps"]["visual_quality"], 40)
        self.assertFalse(scored["strict_pass"])

    def test_freeze_gate_is_task_aware(self):
        self.assertEqual(scoring.evidence_defects({}, expected_steps=1,
                                                   freeze_seconds=2), [])
        defects = scoring.evidence_defects({}, expected_steps=4,
                                            freeze_seconds=2)
        self.assertEqual(defects[0]["reason"], "requested_multistep_action_frozen")

    def test_paired_comparison_requires_same_cases_and_version(self):
        left = [{"id": "a", "version": scoring.VERSION,
                 "case_sha256": "same", "evaluation_config": {"sample_fps": 2},
                 "scoring": {"valid": True, "score": 75}}]
        right = [{"id": "a", "version": scoring.VERSION,
                  "case_sha256": "same", "evaluation_config": {"sample_fps": 2},
                  "scoring": {"valid": True, "score": 70}}]
        result = comparison.compare(left, right, iterations=100, seed=1)
        self.assertEqual(result["mean_left_minus_right"], 5)
        self.assertIsNone(result["paired_bootstrap_95_ci"])
        with self.assertRaises(ValueError):
            comparison.compare(left, right + [{"id": "b", "version": scoring.VERSION,
                                               "scoring": {"valid": True, "score": 70}}])
        with self.assertRaises(ValueError):
            comparison.compare(left, [dict(right[0], version="obsolete")])
        with self.assertRaises(ValueError):
            comparison.compare(left, [dict(right[0], case_sha256="different")])


class OperatorTests(unittest.TestCase):
    def test_video_rubric_rejects_missing_evidence_and_separates_scores(self):
        rows = [{"id": key, "applicable": True, "score": 4,
                 "evidence_frames": [1], "finding": "visible"}
                for key, _ in video_rubric.RUBRIC["signal_quality"]]
        self.assertEqual(video_rubric.validate_result("signal_quality", {"criteria": rows}, 1)["score"], 75)
        rows[0]["evidence_frames"] = []
        with self.assertRaises(ValueError):
            video_rubric.validate_result("signal_quality", {"criteria": rows}, 1)

    def test_static_requested_diagram_is_not_frozen_failure(self):
        frames = [np.full((144, 256, 3), 120, dtype=np.uint8) for _ in range(30)]
        still = op.temporal_consistency(frames, 30, expected_steps=1)
        changing = op.temporal_consistency(frames, 30, expected_steps=4)
        self.assertEqual(still["score"], 100)
        self.assertLess(changing["score"], still["score"])

    def test_signal_metrics_are_finite_and_explainable(self):
        frame = np.full((144, 256, 3), 128, dtype=np.uint8)
        result = op.signal_quality([frame] * 3)
        self.assertEqual(result["focus_score"], 100)
        self.assertIn("clipped_fraction_p90", result)

    def test_evaluate_writes_evidence_and_score(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]) as tmp:
            path = str(Path(tmp) / "clip.avi")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (256, 144))
            self.assertTrue(writer.isOpened())
            for i in range(12):
                frame = np.full((144, 256, 3), 100 + i, dtype=np.uint8)
                writer.write(frame)
            writer.release()
            fake = {"score": 4, "binary": "PASS", "criteria": [{"id": "x", "evidence_frames": [1]}]}
            with patch.object(runner, "extract_frames", return_value=[object()] * 100), \
                 patch.object(runner, "DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: fake})()
                                                      for a in runner.DIMENSIONS}), \
                 patch.object(runner, "VIDEO_DIMENSIONS", {a: type("Judge", (), {"score": lambda self, c, f: {"score": 75}})()
                                                            for a in runner.VIDEO_DIMENSIONS}):
                row = runner.evaluate({"id": "x", "expected_narrative_order": ["step"]},
                                      {"status": "ok", "video_path": path})
            self.assertTrue(row["scoring"]["valid"])
            self.assertEqual(row["axes"]["conceptual_correctness"]["score"], 75)
            self.assertEqual(row["sampled_frame_count"], 24)
            self.assertEqual(row["judge_frame_indices_in_sample"][0], 0)
            self.assertEqual(row["judge_frame_indices_in_sample"][-1], 99)
            self.assertEqual(len(row["video_sha256"]), 64)
            self.assertTrue(runner.reusable(row, {"id": "x", "expected_narrative_order": ["step"]},
                                            {"status": "ok", "video_path": path}, 2.0, 832))
            self.assertFalse(runner.reusable(row, {"id": "x", "expected_narrative_order": ["changed"]},
                                             {"status": "ok", "video_path": path}, 2.0, 832))


if __name__ == "__main__":
    unittest.main()
