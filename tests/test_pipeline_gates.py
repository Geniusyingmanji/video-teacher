import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.pipeline_artifacts import check_artifacts
from scripts.pipeline_preflight import ROOT, check


class PipelineGateTest(unittest.TestCase):
    def test_real_pilot_preflight_reports_partial_shared_quiz(self):
        report = check(ROOT / "data/prompts/pilot_v0_1.jsonl",
                       ROOT / "data/first_frames",
                       ROOT / "data/teachquiz/pilot_v0_1_quiz.jsonl",
                       ROOT / "models/nonexistent-wan",
                       ROOT / "models/nonexistent-student", check_runtime=False)
        self.assertEqual(report["prompt_count"], 60)
        self.assertEqual(report["first_frame_count"], 60)
        self.assertEqual(report["shared_quiz_count"], 10)
        self.assertFalse(report["ready"])

    def test_artifact_gate_uses_latest_attempt_and_rejects_errors(self):
        prompts = [{"id": "a"}, {"id": "b"}]
        records = [{"id": "a", "status": "ok", "video_path": "a.mp4"},
                   {"id": "a", "status": "error"},
                   {"id": "b", "status": "ok", "video_path": "b.mp4", "video_sha256": "valid"}]
        with patch.object(Path, "is_file", return_value=True), patch(
                "scripts.pipeline_artifacts.file_sha256", return_value="valid"):
            report = check_artifacts(prompts, records, "generation")
        self.assertEqual(report["failed"], ["a"])
        self.assertFalse(report["complete"])
        self.assertFalse(check_artifacts(prompts, [{"id": "a", "pre": {}, "post_video": {}},
                                                    {"id": "b", "error": "failure"}],
                                         "teachquiz")["complete"])
        complete = [{"id": cid, "pre": {"score": 0.1}, "post_video": {"score": 0.3},
                     "random_video": {"score": 0.1}} for cid in ("a", "b")]
        self.assertTrue(check_artifacts(prompts, complete, "teachquiz")["complete"])


if __name__ == "__main__":
    unittest.main()
