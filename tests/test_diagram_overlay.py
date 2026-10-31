import unittest

import numpy as np
from PIL import Image

from generation.runners.diagram_overlay_runner import render_frames


class DiagramOverlayTest(unittest.TestCase):
    def test_source_pixels_stay_fixed_outside_reviewed_box(self):
        source = Image.new("RGB", (100, 60), "white")
        frames = render_frames(source, [[0.2, 0.2, 0.8, 0.8]], 8, (100, 60))
        self.assertEqual(frames.shape, (8, 60, 100, 3))
        self.assertTrue(np.array_equal(frames[0], np.asarray(source)))
        self.assertTrue(np.array_equal(frames[-1, 0, 0], np.asarray(source)[0, 0]))
        self.assertFalse(np.array_equal(frames[-1], frames[0]))


if __name__ == "__main__":
    unittest.main()
