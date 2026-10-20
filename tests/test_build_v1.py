import unittest
from html.parser import HTMLParser
from pathlib import Path
import json

import cv2
import numpy as np
from PIL import Image, ImageChops

from generation.contract_video import _checked_video
from generation.teaching_contract import ContractError
from scripts.build_v1 import ROOT, build


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "img"}:
            attributes = dict(attrs)
            self.paths.append(attributes.get("href") or attributes.get("src"))


class LocalV1Test(unittest.TestCase):
    def test_offline_build_links_only_existing_artifacts(self):
        out = ROOT / "results/v1"
        manifest = build(ROOT, out)
        self.assertEqual(manifest["prompts"]["count"], 60)
        self.assertEqual(len(manifest["prompts"]["disciplines"]), 12)
        self.assertEqual(manifest["contracts"]["count"], 3)
        audit_rows = [json.loads(line) for line in
                      (out / manifest["contracts"]["audit_path"])
                      .read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(audit_rows), 3)
        self.assertTrue(all(row["status"] == "pass" and row["frames_checked"] == 120
                            for row in audit_rows))
        generation_rows = [json.loads(line) for line in
                           (out / manifest["contracts"]["generation_manifest_path"])
                           .read_text(encoding="utf-8").splitlines()]
        eval_rows = [json.loads(line) for line in
                     (out / manifest["contracts"]["eval_prompts_path"])
                     .read_text(encoding="utf-8").splitlines()]
        self.assertEqual({row["id"] for row in generation_rows},
                         {case["id"] for case in manifest["contracts"]["cases"]})
        self.assertTrue(all(row["status"] == "ok" and Path(row["video_path"]).is_file()
                            for row in generation_rows))
        self.assertEqual({row["id"] for row in eval_rows}, {row["id"] for row in generation_rows})
        self.assertTrue(all(row["prompt_text"] != row["original_prompt_text"]
                            and row["audio_narration_required"] is False for row in eval_rows))
        for case in manifest["contracts"]["cases"]:
            self.assertEqual(case["frame_count"], 120)
            self.assertEqual(case["duration_s"], 5.0)
            self.assertEqual(case["frames_checked"], 120)
            self.assertLess(case["worst_frame_mean_error"], 15)
            capture = cv2.VideoCapture(str(out / case["video"]))
            self.assertTrue(capture.isOpened())
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 120)
            ok_first, first = capture.read()
            capture.set(cv2.CAP_PROP_POS_FRAMES, 48)
            ok_middle, middle = capture.read()
            capture.set(cv2.CAP_PROP_POS_FRAMES, 119)
            ok_last, last = capture.read()
            capture.release()
            self.assertTrue(ok_first and ok_middle and ok_last)
            self.assertGreater(float(np.mean(cv2.absdiff(first, middle))), 0.2)
            self.assertGreater(float(np.mean(cv2.absdiff(middle, last))), 0.2)
            with Image.open(out / case["setup"]) as setup, Image.open(out / case["result"]) as result:
                self.assertIsNotNone(ImageChops.difference(setup, result).getbbox())
        self.assertEqual(len(manifest["evidence_arms"]), 7)
        self.assertTrue(all(arm["consistent"] for arm in manifest["evidence_arms"]))
        self.assertEqual(manifest["probes"]["5B"]["pilot_overlap"], 60)
        self.assertEqual(manifest["probes"]["1.3B"]["pilot_overlap"], 60)
        parser = _Links()
        parser.feed((out / "index.html").read_text(encoding="utf-8"))
        missing = [path for path in parser.paths if not (out / path).is_file()]
        self.assertEqual(missing, [])

    def test_video_check_rejects_visual_mismatch(self):
        video = ROOT / "results/v1/videos/phys_exp_02.mp4"
        blank = np.zeros((480, 832, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ContractError, "differs from checked state"):
            _checked_video(video, [blank] * 120, 48, 24)


if __name__ == "__main__":
    unittest.main()
