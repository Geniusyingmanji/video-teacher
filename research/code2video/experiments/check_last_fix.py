"""Regression: a single permitted fix must be rendered before returning failure."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code2Video/src'))
from agent import TeachingVideoAgent, RunConfig


def no_api(*args, **kwargs):
    raise RuntimeError('Regression check does not call a model')


if __name__ == '__main__':
    agent = TeachingVideoAgent(0, 'Final fix validation',
        folder=ROOT / 'Code2Video/src/CASES/VIDEOTEACHER-regression',
        cfg=RunConfig(api=no_api, use_assets=False, use_feedback=False))
    code = 'from manim import *\nclass Section1Scene(Scene):\n    def construct(self):\n        self.add(Circle(include_tips=False))\n        self.wait(0.1)\n'
    agent.section_codes['section_1'] = code
    (agent.output_dir / 'section_1.py').write_text(code)
    fixes = []
    def fix(section_id, current, error, output_dir):
        assert 'include_tips' in error
        fixes.append(section_id)
        return current.replace('Circle(include_tips=False)', 'Circle()')
    agent.scope_refine_fixer = SimpleNamespace(fix_code_smart=fix)
    assert agent.debug_and_fix_code('section_1', max_fix_attempts=1)
    assert len(fixes) == 1
    assert Path(agent.section_videos['section_1']).is_file()
    print('PASS: one fix followed by a successful real Manim render')
