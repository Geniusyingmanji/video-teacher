import unittest
from html.parser import HTMLParser
from pathlib import Path

import cv2
from PIL import Image, ImageChops

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
        for case in manifest["contracts"]["cases"]:
            self.assertEqual(case["frame_count"], 120)
            self.assertEqual(case["duration_s"], 5.0)
            capture = cv2.VideoCapture(str(out / case["video"]))
            self.assertTrue(capture.isOpened())
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 120)
            capture.release()
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


if __name__ == "__main__":
    unittest.main()
