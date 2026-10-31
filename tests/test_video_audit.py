import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import imageio.v3 as iio
import numpy as np

from eval.frame_extractor import extract_frames, sample_frame_indices
from eval.run_eval import evaluate_one
from scripts.audit_generated_videos import inspect_video


class VideoAuditTest(unittest.TestCase):
    def test_short_video_sampling_and_duration_gate(self):
        root = Path(__file__).parent / "_video_audit_test_output"
        root.mkdir(exist_ok=True)
        try:
            path = root / "sample.mp4"
            video = np.stack([np.full((64, 96, 3), index * 20, dtype=np.uint8)
                              for index in range(10)])
            iio.imwrite(path, video, fps=10, codec="libx264")

            frames = extract_frames(path, n=3, resize_max=48)
            self.assertEqual(len(frames), 3)
            self.assertEqual(len(extract_frames(path, resize_max=48)), 2)
            self.assertEqual(frames[0].size, (48, 32))
            self.assertLess(np.asarray(frames[0]).mean(), np.asarray(frames[-1]).mean())

            result = inspect_video(path, root / "audit", target_duration_s=5)
            self.assertEqual(result["flags"], ["under_target_duration"])
            self.assertEqual(len(result["sample_times_s"]), 6)
            self.assertTrue(Path(result["contact_sheet"]).is_file())
            self.assertEqual(len(list(Path(result["evidence_dir"]).glob("*.png"))), 6)
            self.assertEqual(len(list(Path(result["layout_overlay_dir"]).glob("*.png"))), 6)
            self.assertTrue(result["layout_review_required"])
            long_result = inspect_video(path, root / "long_audit", target_duration_s=None)
            self.assertEqual(long_result["flags"], [])
        finally:
            shutil.rmtree(root)

    def test_layout_judges_receive_detail_frames(self):
        from PIL import Image

        class Judge:
            def __init__(self):
                self.widths = []

            def score(self, _case, frames):
                self.widths.append(frames[0].width)
                return {"score": 3, "binary": "PASS"}

        core, layout = Judge(), Judge()
        with patch("eval.run_eval.extract_frames", return_value=[Image.new("RGB", (832, 480))]) as mocked:
            result = evaluate_one(
                {"id": "sample"}, "unused.mp4", 2, 384,
                {"conceptual_correctness": core, "pedagogical_clarity": layout},
                {"conceptual_correctness": 1, "pedagogical_clarity": 1},
                detail_frame_max_px=832,
            )
        self.assertEqual(result["aggregate_score"], 3)
        self.assertEqual(core.widths, [384])
        self.assertEqual(layout.widths, [832])
        mocked.assert_called_once_with("unused.mp4", sample_fps=2, resize_max=832)

    def test_fixed_rate_sampling_depends_on_duration(self):
        self.assertEqual(sample_frame_indices(49, 16, 2), [0, 8, 16, 24, 32, 40, 48])
        self.assertEqual(sample_frame_indices(121, 24, 2), list(range(0, 121, 12)))
        with self.assertRaisesRegex(ValueError, "source FPS"):
            sample_frame_indices(49, 0, 2)

    def test_adaptive_sampling_catches_unscheduled_scene_change(self):
        from scripts.audit_generated_videos import adaptive_frame_numbers

        root = Path(__file__).parent / "_adaptive_audit_test_output"
        root.mkdir(exist_ok=True)
        try:
            path = root / "scene.mp4"
            frames = np.zeros((100, 64, 96, 3), dtype=np.uint8)
            frames[40:55] = 255
            iio.imwrite(path, frames, fps=10, codec="libx264")
            cap = cv2.VideoCapture(str(path))
            try:
                chosen = adaptive_frame_numbers(cap, 100, 10, {0, 25, 50, 65, 75, 98})
            finally:
                cap.release()
            self.assertIn(40, chosen)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
