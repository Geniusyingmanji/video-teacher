import tempfile
import unittest
from pathlib import Path

from generation.source_geometry import canvas_box, resolve_source
from generation.strict_video_contract import validate_regions
from generation.quality_gate import assess


class GeometryTests(unittest.TestCase):
    def test_letterbox_landscape_portrait_and_pixel_bounds(self):
        self.assertEqual(canvas_box([0, 0, 200, 100], (200, 100), (400, 400)), [0, .25, 1, .75])
        self.assertEqual(canvas_box([0, 0, 100, 200], (100, 200), (400, 400)), [.25, 0, .75, 1])
        with self.assertRaises(ValueError):
            canvas_box([0, 0, 101, 200], (100, 200))
        self.assertEqual(validate_regions([[20, 30, 40, 50]], True, (100, 200)), [[20, 30, 40, 50]])
        with self.assertRaises(ValueError):
            validate_regions([[0, 0, 100, 200]], True, (100, 200))

    def test_casefold_requires_unambiguous_asset(self):
        case = {'id': 'fixture', 'prompt_text': 'Label supplied image',
                'source': {'source_id': 'ABC', 'source_image_path': 'original.png'}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'grade_abc.png'
            path.touch()
            self.assertEqual(resolve_source(case, directory), path)
            (Path(directory)/'grade_ABC.png').touch()
            with self.assertRaises(ValueError):
                resolve_source(case, directory)

    def test_quality_rejects_render_only_and_preservation_failure(self):
        generation = {'complete': True, 'timing': {'valid': True}}
        self.assertFalse(assess(generation, {})['passed'])
        evaluation = {'scoring': {'valid': True, 'strict_pass': True},
                      'axes': {axis: {'criteria': [dict(id=key, applicable=True, score=4, evidence_frames=[1])
                                                   for key in keys]} for axis, keys in (
                          ('conceptual_correctness', ['steps', 'final_state', 'core_fact', 'no_contradiction']),
                          ('pedagogical_clarity', ['readability', 'takeaway']))},
                      'supplementary': {'teaching_engagement': {'valid': True, 'score': 0}}}
        self.assertTrue(assess(generation, evaluation)['passed'])
        generation['strict_diagnostics'] = {'source_preservation': {'valid': True,
                                                                  'pre_encoding': {'valid': False}}}
        self.assertFalse(assess(generation, evaluation)['passed'])
        evaluation['scoring']['strict_pass'] = False
        evaluation['supplementary']['teaching_engagement']['score'] = 100
        self.assertFalse(assess(generation, evaluation)['passed'])
