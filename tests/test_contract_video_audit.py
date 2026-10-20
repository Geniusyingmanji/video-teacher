import unittest

import cv2
import numpy as np

from eval.contract_video_audit import audit_contract_video
from generation.contract_video import compile_contract_video_plan
from generation.teaching_contract import load_contracts
from scripts.build_v1 import CONTRACTS, PROMPTS, ROOT, read_jsonl


class ContractVideoAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contracts(ROOT / CONTRACTS)["math_prob_02"]
        cls.case = read_jsonl(ROOT / PROMPTS, "id")["math_prob_02"]
        cls.plan = compile_contract_video_plan(cls.contract, cls.case)
        cls.out = ROOT / "results/v1/videos"
        cls.out.mkdir(parents=True, exist_ok=True)

    def _write_and_audit(self, name, frame):
        path = self.out / name
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24,
                                 (832, 480))
        self.assertTrue(writer.isOpened())
        try:
            for _ in self.plan["frames"]:
                writer.write(frame)
        finally:
            writer.release()
        try:
            return audit_contract_video(path, self.contract, self.case)
        finally:
            path.unlink(missing_ok=True)

    def test_static_setup_is_missing_result_with_timestamp(self):
        result = self._write_and_audit("_audit_static_setup.mp4", self.plan["setup_frame"])
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["reason"], "result_remains_at_setup")
        self.assertEqual(result["frames_checked"], 120)
        self.assertGreater(result["phase_failures"]["result"], 0)
        self.assertTrue(any(item["phase"] == "result" and item["time_s"] >= 4
                            for item in result["evidence"]))

    def test_blank_video_is_wrong(self):
        blank = np.zeros_like(self.plan["setup_frame"])
        result = self._write_and_audit("_audit_blank.mp4", blank)
        self.assertEqual(result["status"], "wrong")
        self.assertGreater(result["phase_failures"]["setup"], 0)
        self.assertGreater(result["phase_failures"]["result"], 0)

    def test_missing_file_is_unobservable(self):
        result = audit_contract_video(self.out / "_nonexistent_audit.mp4",
                                      self.contract, self.case)
        self.assertEqual(result["status"], "unobservable")
        self.assertEqual(result["reason"], "video_cannot_open")


if __name__ == "__main__":
    unittest.main()
