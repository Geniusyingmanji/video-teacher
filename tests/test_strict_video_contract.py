import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from generation.strict_video_contract import make_contract, outline_prompt, storyboard_prompt, code_prompt, validate_regions
from generation.strict_manim import allocate_frames, inspect_exact, SourceFrameGuard


class ContractTests(unittest.TestCase):
    def test_lossless_task_and_seconds(self):
        case = {'id': 'test', 'prompt_text': 'Keep original diagram. Do not diagnose a rhythm.',
                'expected_visual_elements': ['25 mm/s'], 'discipline_specific_rubric': ['150/min']}
        contract = make_contract(case)
        from types import SimpleNamespace
        section = SimpleNamespace(id='section_1', title='Test', lecture_lines=[], animations=[])
        for prompt in (outline_prompt(contract), storyboard_prompt(contract, {}), code_prompt(contract, section, '')):
            self.assertIn(case['prompt_text'], prompt)
            self.assertIn('25 mm/s', prompt)
            self.assertIn('150/min', prompt)
            self.assertNotIn('5 minutes', prompt)
        self.assertEqual(contract['frame_count'], 75)
        self.assertIn('NO source image', outline_prompt(contract))
        self.assertIn('provenance', contract['field_precedence'])

    def test_regions_cannot_authorize_entire_source(self):
        for invalid in ([], [[0, 0, 1, 1]], [[-.1, 0, .1, .1]], [[0, 0, float('nan'), .1]]):
            with self.assertRaises(ValueError):
                validate_regions(invalid, required=True)
        self.assertEqual(validate_regions([[.4, .4, .6, .6]], True), [[.4, .4, .6, .6]])

    def test_exact_integer_frame_budget(self):
        self.assertEqual(sum(allocate_frames([.1, .3, 12])), 75)
        with self.assertRaises(ValueError):
            allocate_frames([1]*76)

    def test_pre_encoding_rejects_even_one_outside_pixel(self):
        import numpy as np
        guard = SourceFrameGuard([[.4, .4, .6, .6]])
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        guard.check(frame, 15)
        frame[50, 50] = 255
        guard.check(frame)
        self.assertTrue(guard.report()['valid'])
        frame[10, 10] = 1
        guard.check(frame)
        self.assertFalse(guard.report()['valid'])
        self.assertEqual(guard.report()['max_changed_pixels'], 1)

    def test_real_render_and_preserved_source(self):
        try:
            import manim
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest('Manim rendering environment required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new('RGB', (854, 480), 'white')
            ImageDraw.Draw(image).rectangle((30, 30, 160, 160), fill='blue')
            source = root / 'source.png'
            image.save(source)
            contract = root / 'contract.json'
            contract.write_text(json.dumps(make_contract({'id': 'fixture', 'prompt_text': 'Fill the answer box.'}, source)))
            (root / 'storyboard.json').write_text(json.dumps({'source_edit_regions': [[342, 192, 512, 288]]}))
            code = root / 'section_1.py'
            code.write_text('from manim import *\nclass Section1Scene(Scene):\n'
                            ' def construct(self):\n'
                            '  self.play(FadeIn(self.source_text("TEST", [342,192,512,288])), run_time=.3)\n'
                            '  self.wait(.2)\n')
            env = dict(os.environ)
            env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
            command = [sys.executable, '-m', 'generation.strict_manim', '--code', str(code),
                       '--scene', 'Section1Scene', '--contract', str(contract)]
            completed = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stderr[-4000:])
            data = json.loads((root / 'strict_diagnostics.json').read_text())
            self.assertTrue(data['timing']['valid'])
            self.assertTrue(data['source_preservation']['valid'])
            self.assertEqual(data['source_preservation']['pre_encoding']['checked_frames'], 75)
            self.assertEqual(sum(data['event_frames']), 75)
            # A global alteration must be rejected, even though encoding succeeds.
            code.write_text('from manim import *\nclass Section1Scene(Scene):\n'
                            ' def construct(self):\n'
                            '  self.play(FadeIn(Rectangle(width=14, height=8, fill_color=RED, fill_opacity=1)))\n')
            completed = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(json.loads((root / 'strict_diagnostics.json').read_text())['source_preservation']['valid'])


if __name__ == '__main__':
    unittest.main()
