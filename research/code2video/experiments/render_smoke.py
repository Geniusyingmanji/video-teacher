"""Offline fixture: exercise upstream render workers and merge; no LLM generation."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code2Video' / 'src'))
from agent import TeachingVideoAgent, RunConfig, Section


def no_api(*args, **kwargs):
    raise RuntimeError('Offline fixture must not call an API')


if __name__ == '__main__':
    case = json.loads((ROOT.parents[1] / 'data/prompts/pilot_v0_1.jsonl').read_text().splitlines()[0])
    agent = TeachingVideoAgent(0, 'Derivative as tangent slope',
        folder=ROOT / 'Code2Video/src/CASES/VIDEOTEACHER-offline',
        cfg=RunConfig(api=no_api, use_assets=False, use_feedback=False,
                      max_fix_bug_tries=1, max_regenerate_tries=1))
    for index in (1, 2):
        sid = f'section_{index}'
        code = f'''from manim import *
class Section{index}Scene(Scene):
    def construct(self):
        title = Text("Derivative = tangent slope", font_size=32).to_edge(UP)
        axes = Axes(x_range=[-2, 2, 1], y_range=[-1, 4, 1], x_length=7, y_length=4,
                    tips=False).shift(DOWN * .35)
        labels = axes.get_axis_labels(Text("x", font_size=22), Text("y", font_size=22))
        curve = axes.plot(lambda x: x*x, x_range=[-1.8, 1.8], color=BLUE)
        equation = Text("f(x) = x²;  f'(x) = 2x", font_size=24).to_edge(DOWN)
        point_x = ValueTracker({-1 if index == 1 else 0})
        dot = always_redraw(lambda: Dot(axes.c2p(point_x.get_value(), point_x.get_value()**2), color=YELLOW))
        tangent = always_redraw(lambda: Line(
            axes.c2p(point_x.get_value()-.55, point_x.get_value()**2 - 2*point_x.get_value()*.55),
            axes.c2p(point_x.get_value()+.55, point_x.get_value()**2 + 2*point_x.get_value()*.55),
            color=YELLOW))
        self.add(title, axes, labels, curve, equation)
        self.play(FadeIn(dot), Create(tangent), run_time=1)
        self.play(point_x.animate.set_value({0 if index == 1 else 1}), run_time=3, rate_func=linear)
        self.wait(1)
'''
        agent.sections.append(Section(sid, 'Tangent slope', [], []))
        agent.section_codes[sid] = code
        (agent.output_dir / f'{sid}.py').write_text(code)
    videos = agent.render_all_sections(max_workers=2)
    result = {'mode': 'offline_handwritten_fixture', 'source_case': case,
              'expected_sections': 2, 'rendered_sections': len(videos), 'videos': videos}
    if len(videos) == 2:
        result['merged_video'] = agent.merge_videos()
    (ROOT / 'experiments' / os.getenv('SMOKE_RESULT', 'render_result.json')).write_text(
        json.dumps(result, indent=2, ensure_ascii=False))
    if len(videos) != 2 or not result.get('merged_video'):
        raise SystemExit(1)
