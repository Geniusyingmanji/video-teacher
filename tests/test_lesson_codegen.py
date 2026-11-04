import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from generation.lesson_codegen import is_code_request, validate_code
from generation.lesson_spec import VERSION
from generation.strict_video_contract import ContractAPI, make_contract, storyboard_prompt


class LessonCodegenTests(unittest.TestCase):
    def test_preflight_reports_multiple_real_failures_together(self):
        code = '''from manim import *
class Section1Scene(Scene):
 def begin_teaching_step(self, chapter_id): pass
 def construct(self):
  triangle = Polygon([0,0], [1,0], [0,1])
  check = Checkmark()
  angle = angle_between(UP, RIGHT)
  pass
'''
        with self.assertRaises(ValueError) as failure:
            validate_code(code)
        for finding in ('redefine runtime method', 'two-coordinate', 'Checkmark', 'angle_between', 'unfinished'):
            self.assertIn(finding, str(failure.exception))

    def test_preflight_accepts_real_geometry_without_rewriting_code(self):
        code = '''from manim import *
class Section1Scene(Scene):
 def construct(self):
  self.begin_teaching_step("chapter_1")
  triangle = Polygon([0,0,0], [1,0,0], [0,1,0])
  arc = AngleFromThreePoints(*triangle.get_vertices())
  self.play(Create(triangle), Create(arc), run_time=2)
'''
        self.assertIsNone(validate_code(code))

    def test_code_and_repair_enable_reasoning_with_sufficient_output_budget(self):
        case = {'id': 'fixture', 'lesson_version': VERSION, 'target_duration_s': 60,
                'prompt_text': 'Show a triangle.', 'audio_narration_required': True}
        contract = make_contract(case)
        prompts = [('Write complete runnable Manim CE v0.19 Python code only.', True),
                   ('You are an expert Manim developer.\n**Current Code:**\ninvalid', True),
                   (storyboard_prompt(contract, {}), False),
                   ('Rewrite ONLY the spoken narration.', False)]
        for prompt, thinking in prompts:
            self.assertEqual(is_code_request(prompt), thinking)
            with tempfile.TemporaryDirectory() as directory, patch('openai.OpenAI') as client, \
                    patch('generation.prompt_budget.request_budget', side_effect=lambda text,tokens,images: (tokens, {})) as budget:
                response = client.return_value.chat.completions.create.return_value
                response.choices = [SimpleNamespace(finish_reason='stop')]
                response.usage = None
                response.model_dump_json.return_value = '{}'
                ContractAPI(contract, Path(directory))(prompt, max_tokens=4096)
                arguments = client.return_value.chat.completions.create.call_args.kwargs
                self.assertEqual(arguments['extra_body']['chat_template_kwargs']['enable_thinking'], thinking)
                self.assertEqual(arguments.get('reasoning_effort'), 'medium' if thinking else None)
                self.assertEqual(budget.call_args.args[1], 16384 if thinking else 4096)
                provenance = json.loads(next((Path(directory)/'requests').glob('*.budget.json')).read_text())
                self.assertEqual(provenance['enable_thinking'], thinking)
