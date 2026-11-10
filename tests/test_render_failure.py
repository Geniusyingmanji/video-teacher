from pathlib import Path
import tempfile
import unittest

from generation.render_failure import render_failure
from generation.repair_feedback import feedback_for


class RenderFailureTests(unittest.TestCase):
    def test_swallowed_render_exception_reaches_next_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'section_1_render.log'
            path.write_text('progress\n' * 4000 +
                            "TypeError: Mobject.__init__() got an unexpected keyword argument 'origin'\n")
            error, logs = render_failure(directory)
            feedback = feedback_for({'error': error, 'render_failure_logs': logs}, {})
            self.assertIn("unexpected keyword argument 'origin'", feedback['generation_error'])
            self.assertEqual(logs[0]['path'], str(path))
            self.assertLessEqual(len(logs[0]['tail'].encode()), 8000)
            self.assertEqual(path.read_text().count('progress'), 4000)

    def test_missing_logs_remain_an_unknown_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            error, logs = render_failure(directory)
            self.assertEqual(logs, [])
            self.assertIn('no complete video', error)
            self.assertNotIn('TypeError', error)
