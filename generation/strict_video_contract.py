"""Lossless task propagation and explicit five-second Code2Video prompts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
import os
import base64
import uuid

VERSION = 'strict-five-seconds-v2'


def make_contract(case: dict, source_image: Path | None = None) -> dict:
    return {'version': VERSION, 'duration_seconds': 5, 'fps': 15, 'frame_count': 75,
            'task': case, 'source_image': str(source_image.resolve()) if source_image else None,
            'field_precedence': ('task.prompt_text and current expected_concepts, expected_visual_elements, '
                                 'expected_narrative_order and discipline_specific_rubric define the current task. '
                                 'original_prompt_text, source.original_instruction and old narrative_beats are provenance, '
                                 'not replacement instructions. Old expected_frame_range values refer to historical sampled '
                                 'frames, not the 75 rendered frames. Use source_image only when it is non-null.'),
            'rules': ['Preserve every instruction and prohibition in task.prompt_text.',
                      'Show every required concept, visual element and narrative step.',
                      'Use one scene; show initial state, the requested change, then hold the result.',
                      'Never substitute an easier question or omit constraints to fit the duration.',
                      'When source_image is non-null, the source is a locked background, not an inspiration to redraw.',
                      'When source_image is non-null, edits must stay inside declared edit rectangles covering at most 25% of the canvas.',
                      'When source_image is null, create a standalone diagram and never reference a nonexistent source image.']}


def contract_text(contract: dict) -> str:
    return '\nAUTHORITATIVE TASK CONTRACT (applies to this stage and every repair):\n' + json.dumps(contract, ensure_ascii=False)


def contract_hash(contract: dict) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def outline_prompt(contract: dict) -> str:
    return ('Plan exactly ONE scene for a video of exactly FIVE SECONDS, never minutes. '
            'Return only JSON: {"topic":str,"target_audience":str,"sections":'
            '[{"id":"section_1","title":str,"content":str,"example":str}]}. '
            'Include the original task constraints, correct answer and every required step in the section. '
            'Do not invent unsupported answers. '
            + ('There is NO source image for this current task. Draw standalone visuals. ' if not contract['source_image'] else '')
            + contract_text(contract))


def storyboard_prompt(contract: dict, outline) -> str:
    return ('Return only JSON with one section: {"sections":[{"id":"section_1","title":str,'
            '"lecture_lines":[str],"animations":[str]}],"source_edit_regions":[[x0,y0,x1,y1]]}. '
            'Design an initial state, at most three meaningful animation steps, and final hold. '
            'All phases together last exactly 5 seconds. Use normalized canvas coordinates for edit rectangles '
            '(origin top left, values 0..1). For source-image tasks identify small rectangles covering only '
            'the requested changed labels or marks; union area must not exceed 0.25. '
            'The renderer supplies the original source background, holds it for 1 second before your animations '
            'and holds the final result for 1 second. Do not redraw, move, recolor, hide or replace the source. '
            'When source_image is null there is NO source image: draw standalone visuals and source_edit_regions MUST be empty. '
            'Carry ALL source task restrictions and expected visual/narrative elements into animations. '
            + contract_text(contract) + '\nOUTLINE:\n' + str(outline))


def code_prompt(contract: dict, section, base_class: str, note: str = '') -> str:
    scene = section.id.title().replace('_', '') + 'Scene'
    return ('Write complete runnable Manim CE v0.19 Python code only. ' + note
            + f'\nDefine {scene}(TeachingScene) with construct(self). Include this base class:\n'
            + base_class + '\nUse at most three meaningful animation steps. Keep all content readable. '
            'Use real Manim CE primitives such as Text, Circle, Line, Arrow, VGroup and Dot; '
            'never invent classes such as Check. Draw checkmarks from two Line objects. '
            'Use short readable on-screen labels instead of copying lecture paragraphs onto the canvas. '
            'Pass animations or .animate builders to self.play(), never eager mobject mutations. '
            'Set explicit short run_time values; no loops with many tiny animations or per-frame updaters. '
            'The runtime allocates exactly 75 frames to the full scene and adds a one-second final hold. '
            'For source tasks it also adds a one-second initial hold with the original source already displayed. '
            'In source tasks draw ONLY requested changes in the declared edit rectangles; do not call '
            'setup_layout, add an image, clear the scene or draw a new diagram. '
            'Use ordinary positioning matching the actual source; no forced grid. '
            'Respect scientific units, correct answers, task prohibitions and narration requirements. '
            + contract_text(contract) + '\nSTORYBOARD SECTION:\n'
            + json.dumps(vars(section), ensure_ascii=False))


def validate_regions(regions: list, required: bool = False) -> list:
    if not isinstance(regions, list) or (required and not regions):
        raise ValueError('source task needs explicit edit rectangles')
    area = 0
    for r in regions:
        if not isinstance(r, list) or len(r) != 4 or any(type(v) not in (int, float) for v in r):
            raise ValueError('invalid edit rectangle')
        x0, y0, x1, y1 = r
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError('edit rectangle outside canvas')
        area += (x1-x0)*(y1-y0)
    if area > .25:
        raise ValueError('source edit rectangles cover more than 25% of canvas')
    return regions


def install_prompts(agent_module, contract: dict):
    agent_module.get_prompt1_outline = lambda **kwargs: outline_prompt(contract)
    agent_module.get_prompt2_storyboard = lambda **kwargs: storyboard_prompt(contract, kwargs['outline'])
    agent_module.get_prompt3_code = lambda regenerate_note, section, base_class: code_prompt(contract, section, base_class, regenerate_note)


@dataclass
class ContractAPI:
    contract: dict
    output: Path

    def __call__(self, prompt, max_tokens=4096):
        from openai import OpenAI
        current = dict(self.contract)
        storyboard = self.output / 'storyboard.json'
        if storyboard.exists():
            current['allowed_source_edit_regions'] = json.loads(storyboard.read_text()).get('source_edit_regions', [])
        text = str(prompt) + contract_text(current)
        content = [{'type': 'text', 'text': text}]
        if current.get('source_image'):
            data = base64.b64encode(Path(current['source_image']).read_bytes()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}})
        logs = self.output / 'requests'
        logs.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4().hex
        (logs / f'{name}.prompt.txt').write_text(text)
        result = OpenAI(base_url=os.environ.get('LOCAL_BASE_URL', 'http://127.0.0.1:8000/v1'),
                        api_key=os.environ.get('LOCAL_API_KEY', 'local'), timeout=600, max_retries=1).chat.completions.create(
            model=os.environ.get('LOCAL_MODEL', 'qwen3.8-27b'),
            messages=[{'role': 'user', 'content': content}], max_tokens=max_tokens, temperature=.3,
            extra_body={'chat_template_kwargs': {'enable_thinking': False}})
        (logs / f'{name}.response.json').write_text(result.model_dump_json())
        if result.choices[0].finish_reason == 'length':
            raise RuntimeError('Model output truncated; task not accepted')
        return result, result.usage.model_dump() if result.usage else {}


def install_renderer(agent_module, contract_path: Path):
    import sys
    run = agent_module.subprocess.run
    renderer = Path(__file__).with_name('strict_manim.py')
    def strict_run(command, *args, **kwargs):
        if isinstance(command, list) and command and Path(command[0]).name == 'manim':
            code = Path(kwargs.get('cwd', '.')) / command[-2]
            command = [sys.executable, str(renderer), '--code', str(code),
                       '--scene', command[-1], '--contract', str(contract_path)]
        return run(command, *args, **kwargs)
    agent_module.subprocess.run = strict_run
