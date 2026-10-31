import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from generation.runners.provenance import can_resume, input_sha256


class GenerationProvenanceTest(unittest.TestCase):
    def test_resume_requires_matching_inputs_and_intact_video(self):
        args = SimpleNamespace(model_path="models/wan", height=480, width=832,
                               num_frames=121, steps=30, guidance_scale=5.0,
                               seed=42, fps=24, dtype="bfloat16")
        case = {"id": "example", "prompt_text": "Show the ray moving"}
        first_frame = Path("first.png")
        video = Path("video.mp4")
        with patch("generation.runners.provenance.file_sha256", side_effect=lambda p: {
                first_frame: "frame-a", video: "video-a"}[p]), patch.object(Path, "is_file", return_value=True):
            fingerprint = input_sha256(case, args, first_frame)
            record = {"status": "ok", "input_sha256": fingerprint,
                      "video_sha256": "video-a"}
            self.assertTrue(can_resume(record, video, fingerprint))
            self.assertFalse(can_resume({"status": "ok"}, video, fingerprint))
            self.assertNotEqual(fingerprint, input_sha256({**case, "video_prompt": "other"}, args, first_frame))
            args.fps = 16
            self.assertNotEqual(fingerprint, input_sha256(case, args, first_frame))
            args.fps = 24
            args.negative_prompt = "extra hands"
            self.assertNotEqual(fingerprint, input_sha256(case, args, first_frame))
        with patch("generation.runners.provenance.file_sha256", return_value="frame-b"):
            self.assertNotEqual(fingerprint, input_sha256(case, args, first_frame))
        with patch("generation.runners.provenance.file_sha256", return_value="corrupted"), patch.object(Path, "is_file", return_value=True):
            self.assertFalse(can_resume(record, video, fingerprint))


if __name__ == "__main__":
    unittest.main()
