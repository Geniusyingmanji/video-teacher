"""Versioned task propagation and duration-aware Code2Video teaching prompts."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from dataclasses import dataclass
import os
import base64
import uuid
from generation.source_geometry import rectangle_candidates
from generation.lesson_spec import CONTRACT_VERSION, LESSON_CONTRACTS, contract_version, duration_spec, is_lesson, validate_timeline

VERSION = 'strict-five-seconds-v5'


def make_contract(case: dict, source_image: Path | None = None) -> dict:
    contract = {'version': contract_version(case), **duration_spec(case),
            'task': case, 'source_image': str(source_image.resolve()) if source_image else None,
            'field_precedence': ('task.prompt_text and current expected_concepts, expected_visual_elements, '
                                 'expected_narrative_order and discipline_specific_rubric define the current task. '
                                 'original_prompt_text, source.original_instruction and old narrative_beats are provenance, '
                                 'not replacement instructions. Old expected_frame_range values refer to historical sampled '
                                 'frames, not current rendered frames. revision_provenance is archival, not current instructions. Use source_image only when it is non-null.'),
            'rules': ['Preserve every instruction and prohibition in task.prompt_text.',
                      'Show every required concept, visual element and narrative step.',
                      'Use one scene; show initial state, the requested change, then hold the result.',
                      'Never substitute an easier question or omit constraints to fit the duration.',
                      'When source_image is non-null, the source is a locked background, not an inspiration to redraw.',
                      'When source_image is non-null, edits must stay inside declared edit rectangles covering at most 25% of the canvas.',
                      'When source_image is null, create a standalone diagram and never reference a nonexistent source image.']}
    from generation.task_requirements import requirements
    contract['requirements'] = requirements(case)[1:]  # full prompt already lives in task.prompt_text
    if is_lesson(case):
        contract['task'] = {k:v for k,v in case.items() if k!='revision_provenance'}
        contract['task']['revision_provenance'] = {k:v for k,v in case.get('revision_provenance',{}).items() if k!='original_case'}
        contract['rules'][2] = 'Use one continuous scene with clearly separated teaching chapters and persistent object identities.'
        # The source remains immutable in its viewport; explanatory diagrams have a separate area.
        if source_image:
            contract['source_viewport'] = [0, 0, 1, .60]
            contract['teaching_panel'] = [0, .65, 1, 1]
        contract['pacing'] = {'max_wait_s': 8, 'max_time_rescale': 1.02,
                              'minimum_chapters': 3, 'maximum_chapter_s': 30}
    if source_image:
        from PIL import Image
        with Image.open(source_image) as image:
            contract['source_size_pixels'] = list(image.size)
        import math
        viewport = contract.get('source_viewport', [0,0,1,1])
        contract['source_stroke_inset_pixels'] = max(3, math.ceil(3/min(854*(viewport[2]-viewport[0])/contract['source_size_pixels'][0],480*(viewport[3]-viewport[1])/contract['source_size_pixels'][1])))
        contract['source_sha256'] = hashlib.sha256(source_image.read_bytes()).hexdigest()
        contract['source_rectangle_candidates'] = rectangle_candidates(source_image)
        contract['source_coordinate_space'] = 'original_image_pixels_top_left'
    return contract


def contract_text(contract: dict) -> str:
    from generation.repair_feedback import compact
    current = dict(contract)
    if 'quality_feedback' in current:
        current['quality_feedback'] = compact(current['quality_feedback'])
    return '\nAUTHORITATIVE TASK CONTRACT (applies to this stage and every repair):\n' + json.dumps(current, ensure_ascii=False)


def contract_hash(contract: dict) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def outline_prompt(contract: dict) -> str:
    if contract['version'] in LESSON_CONTRACTS:
        return ('Plan a paced teaching lesson of exactly '+str(contract['duration_seconds'])+' seconds. '
                'Return JSON {"topic":str,"target_audience":str,"sections":[{"id":"section_1","title":str,"content":str,"example":str}]}. '
                'Use ONE continuous Manim scene organized into several teaching chapters: question, '
                'visual explanation and operations, verification, recap. Specify real instructional content for the full budget; '
                'do not stretch an atomic five-second reveal. Never invent facts or new problems. '+contract_text(contract))
    return ('Plan exactly ONE scene for a video of exactly FIVE SECONDS, never minutes. '
            'Return only JSON: {"topic":str,"target_audience":str,"sections":'
            '[{"id":"section_1","title":str,"content":str,"example":str}]}. '
            'Include the original task constraints, correct answer and every required step in the section. '
            'Do not invent unsupported answers. '
            + ('There is NO source image for this current task. Draw standalone visuals. ' if not contract['source_image'] else '')
            + contract_text(contract))


def storyboard_prompt(contract: dict, outline) -> str:
    if contract['version'] in LESSON_CONTRACTS:
        return ('Return JSON {"sections":[{"id":"section_1","title":str,"lecture_lines":[str],"animations":[str]}],'
                '"teaching_timeline":[{"id":str,"start_s":number,"end_s":number,"goal":str,"visible_evidence":str,"requirement_ids":[str],"narration":str}],'
                '"source_edit_regions":[[x0,y0,x1,y1]],"source_operations":[object]}. '
                f'Total duration is exactly {contract["duration_seconds"]} seconds, including one-second initial source hold if applicable and one-second final hold. '
                f'Use {max(3,math.ceil(contract["duration_seconds"]/20))}..18 consecutive chapters of 3..30 seconds covering the ENTIRE timeline, without gaps. '
                'Every chapter needs a DISTINCT goal and distinct visible evidence, mapped to the exact IDs in requirements '
                '(the full prompt uses ID prompt). All requirement IDs must be covered across the timeline. '
                'Each chapter must visibly teach a specific part of the unchanged question, with legible captions, '
                'inspectable operations, and a result check. Distinguish input objects, intermediate states and final result. '
                'No empty waits over 8 seconds, repeated loops or slowing a short reveal to fill time. '
                'Include exact per-action durations and natural reading pauses in animations. '
                'When audio_narration_required is true, each chapter also needs its ACTUAL spoken narration in narration_language. '
                'Write substantive explanations, not stage directions or a list of labels. Aim for 3..4 Chinese characters per second '
                'or 2..2.5 English words per second; allow pauses and fit speech inside each chapter. '
                'Spoken claims and animation order must agree, including givens, key operations, reasons and verification. '
                'For standalone tasks source_edit_regions and source_operations must be empty. '
                'For source tasks keep the complete original fixed in source_viewport, use original IMAGE PIXELS '
                'for boxes and helper operations, never do coordinate conversion yourself. '
                'Specify source_operations as [{id:str,kind:text|curve|highlight,step:int,box:[x0,y0,x1,y1],reason:str,text:str,points:[[x,y]]}]. '
                'Steps are 1..18; only originally requested changes belong in source_edit_regions, whose union is at most 25% of the source. '
                'Preserve all original prohibitions and objects in the reference viewport. Explanatory captions and extra teaching diagrams '
                'must be in the lower teaching_panel, never on the reference. Plan source text large enough to render at least 16 pixels. '
                +contract_text(contract)+'\nOUTLINE:\n'+str(outline))
    return ('Return only JSON with one section: {"sections":[{"id":"section_1","title":str,'
            '"lecture_lines":[str],"animations":[str]}],"source_edit_regions":[[x0,y0,x1,y1]]}. '
            'Design an initial state, at most three meaningful animation steps, and final hold. '
            'All phases together last exactly 5 seconds. Use ORIGINAL IMAGE PIXELS for edit rectangles '
            '(origin top left, x in 0..source width, y in 0..source height). Never use normalized canvas '
            'coordinates or guess letterbox offsets. For source-image tasks identify small rectangles covering only '
            'the requested changed labels or marks; union area must not exceed 25% of source width times source height. '
            'Use source_rectangle_candidates when they identify the requested answer boxes, and copy their exact pixel boxes. '
            'The renderer supplies the original source background, holds it for 1 second before your animations '
            'and holds the final result for 1 second. Do not redraw, move, recolor, hide or replace the source. '
            'When source_image is null there is NO source image: draw standalone visuals and source_edit_regions MUST be empty. '
            'For source tasks ALSO return source_operations: [{id:string,kind: text|curve|highlight,step:1|2|3,box:[x0,y0,x1,y1],reason:string,text:string (text only),points:[[x,y],...] (curve only)}]. '
            'Every required answer or path MUST have its own operation at the correct target. All operations will be executed exactly as declared, grouped into at most three reveal steps. '
            'Curve points must stay at least source_stroke_inset_pixels inside their box. Text boxes must allow at least 16 rendered pixels. '
            'Do not choose answer-box candidates belonging to axis labels or unrelated targets; inspect the image. '
            'For a graph conversion draw the actual curve in source coordinates. Split a long curved path into 2..12 short curve operations with narrow boxes following each segment, all at the same step; never authorize the full plot bounding box or copy small tick-label boxes.  For symmetry preserve the original and draw the correctly reflected construction. '
            'For board moves inspect actual blockers and represent all legal destinations, not an invented board. Mark destinations with small inset highlight rectangles near their centers rather than authorizing full board cells; never cover pieces. '
            'Carry ALL source task restrictions and expected visual/narrative elements into animations. '
            + contract_text(contract) + '\nOUTLINE:\n' + str(outline))


def code_prompt(contract: dict, section, base_class: str, note: str = '') -> str:
    scene = section.id.title().replace('_', '') + 'Scene'
    if contract['version'] in LESSON_CONTRACTS:
        return ('Write complete runnable Manim CE v0.19 Python code only. '+note+
                f'\nDefine {scene}(TeachingScene) with construct(self). Include this base class:\n'+base_class+
                '\nAuthor the FULL lesson at its natural pace using explicit run_time and self.wait durations. '
                f'Target {contract["duration_seconds"]} seconds including runtime-added one-second final hold '
                'and one-second initial source hold when source_image is present. '
                'Runtime permits only 2% timing correction; a five-second scene will be REJECTED instead of stretched. '
                'Call self.begin_teaching_step(chapter_id) at each teaching_timeline chapter boundary, including the first chapter. '
                'The first boundary is after the runtime initial source hold when applicable; remaining boundaries must match start_s. '
                'Follow the chapter narration in teaching_timeline: show each referred object and operation at the corresponding time. '
                'Do not synthesize, attach or play audio from generated Python; the trusted runtime attaches narration afterward. '
                'Every chapter needs visible task-relevant explanation or an inspectable operation. '
                'Use 1..3 second transitions, short captions, settled states and waits no longer than 8 seconds. '
                'Do not simulate teaching with repeated highlights, decorative movement or duplicated footage. '
                'Clear old captions before new captions, track original object identities and slot occupancy after every manipulation. '
                'Keep equations, units, answers and all original prohibitions correct. Use only real Manim primitives. '
                'Pass animations to self.play, never eager mutations. Preserve random seeds between rendering passes. '
                'For source tasks the runtime draws the locked original in the upper viewport; never add another image, clear, shift or redraw it. '
                'Use self.source_text/curve/highlight with declared ORIGINAL pixel boxes for source changes. '
                'Use self.teaching_caption(text) for explanations in the lower panel; it returns a Text mobject to animate. '
                'Other explanatory geometry must fit ENTIRELY within teaching_panel. Source protection checks every rendered frame. '
                'For standalone diagrams use the full canvas with separate title, diagram and caption areas. '
                +contract_text(contract)+'\nSTORYBOARD SECTION:\n'+json.dumps(vars(section),ensure_ascii=False))
    return ('Write complete runnable Manim CE v0.19 Python code only. ' + note
            + f'\nDefine {scene}(TeachingScene) with construct(self). Include this base class:\n'
            + base_class + '\nUse at most three meaningful animation steps. Keep all content readable. '
            'Before finalizing, list every required entity/value and ensure ALL are visibly present. '
            'For standalone diagrams use the full width, avoid dense lecture bullets. Keep labels in separate rows or outside the diagram with leader lines; at least 0.15 Manim units between labels. Use diagram height at least 3 Manim units, high-contrast strokes at least 3 pixels, and at most one short caption. Explicitly animate every required directional flow with moving markers or arrows; labels alone cannot demonstrate flow. '
            'Never place two labels on the same side of adjacent segments without checking their bounding boxes. '
            'For sorting move the original number objects along distinct arc trajectories between slots; do not morph or cross-fade digits in place. '
            'For scientific structures preserve verified assets and do not redraw an approximation. '
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
            'For source tasks use ONLY self.source_text(text, pixel_box, replace=True), '
            'self.source_curve(pixel_points, pixel_box), or self.source_highlight(pixel_box) '
            'to create overlays, then animate those returned mobjects. These helpers perform exact image-to-canvas '
            'conversion and check frozen source edit boxes. Do not create or position Text/Line/Rectangle/Circle '
            'directly for a source overlay; never move, scale or shift a returned overlay. '
            'Use the original source-pixel boxes declared in source_edit_regions. '
            'Respect scientific units, correct answers, task prohibitions and narration requirements. '
            + contract_text(contract) + '\nSTORYBOARD SECTION:\n'
            + json.dumps(vars(section), ensure_ascii=False))


def region_union_area(regions):
    """Exact rectangle union; overlapping edits must not double-count pixels."""
    xs = sorted({r[i] for r in regions for i in (0, 2)})
    area = 0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((y0, y1) for x0, y0, x1, y1 in regions if x0 < right and x1 > left)
        end, height = float('-inf'), 0
        for low, high in intervals:
            height += max(0, high - max(low, end))
            end = max(end, high)
        area += (right-left)*height
    return area


def validate_regions(regions: list, required: bool = False, source_size=None) -> list:
    if not isinstance(regions, list) or (required and not regions):
        raise ValueError('source task needs explicit edit rectangles')
    width, height = source_size or (1, 1)
    for r in regions:
        if not isinstance(r, list) or len(r) != 4 or any(type(v) not in (int, float) for v in r):
            raise ValueError('invalid edit rectangle')
        x0, y0, x1, y1 = r
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError('edit rectangle outside canvas')
    if region_union_area(regions) > .25*width*height:
        raise ValueError('source edit rectangles cover more than 25% of canvas')
    return regions


def install_prompts(agent_module, contract: dict):
    from generation.scene_base import BASE
    agent_module.base_class = BASE
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
        from generation.repair_feedback import compact
        from generation.prompt_budget import request_budget
        text = str(prompt)
        if 'AUTHORITATIVE TASK CONTRACT' not in text:
            text += contract_text(current)
        diagnostics = self.output / 'strict_diagnostics.json'
        if diagnostics.exists():
            text += '\nPREVIOUS ACTUAL RENDER DIAGNOSTICS (fix their cause, never widen target boxes):\n' + json.dumps(compact(json.loads(diagnostics.read_text())), ensure_ascii=False)
        content = [{'type': 'text', 'text': text}]
        if current.get('source_image'):
            data = base64.b64encode(Path(current['source_image']).read_bytes()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}})
        for frame in current.get('quality_feedback', {}).get('review_frames', [])[:3]:
            data = base64.b64encode(Path(frame).read_bytes()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + data}})
        logs = self.output / 'requests'
        logs.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4().hex
        if text.startswith('Plan a paced teaching lesson'):
            max_tokens=min(max_tokens,2048)
        elif self.contract['version'] in LESSON_CONTRACTS and text.startswith('Return JSON {"sections"'):
            max_tokens=min(max_tokens,6000)
        max_tokens, budget = request_budget(text, max_tokens, len(content)-1)
        (logs / f'{name}.prompt.txt').write_text(text)
        (logs / f'{name}.budget.json').write_text(json.dumps(budget, indent=2))
        structured = {}
        if text.startswith('Plan a paced teaching lesson'):
            from eval.judges.structured_json import obj, array, response_format
            string={'type':'string','minLength':1,'maxLength':200}
            structured['response_format']=response_format('lesson_outline',{
                'topic':string,'target_audience':string,
                'sections':array(obj({'id':{'type':'string','enum':['section_1']},'title':string,
                                      'content':{'type':'string','minLength':1,'maxLength':4000},
                                      'example':{'type':'string','minLength':1,'maxLength':800}}),minItems=1,maxItems=1)})
        elif self.contract['version'] in LESSON_CONTRACTS and text.startswith('Return JSON {"sections"'):
            from eval.judges.structured_json import obj, array, response_format
            string={'type':'string','minLength':1,'maxLength':900}
            number={'type':'number'}
            box=array(number,minItems=4,maxItems=4)
            common={'id':string,'step':{'type':'integer','minimum':1,'maximum':18},'box':box,'reason':string}
            operations={'anyOf':[
                obj({**common,'kind':{'type':'string','enum':['text']},'text':string}),
                obj({**common,'kind':{'type':'string','enum':['curve']},'points':array(array(number,minItems=2,maxItems=2),minItems=2,maxItems=96)}),
                obj({**common,'kind':{'type':'string','enum':['highlight']}})]}
            source=bool(current.get('source_image'))
            required_ids=['prompt']+[r['id'] for r in current['requirements']]
            structured['response_format']=response_format('lesson_storyboard',{
                'sections':array(obj({'id':{'type':'string','enum':['section_1']},'title':string,
                    'lecture_lines':array(string,maxItems=12),'animations':array(string,minItems=3,maxItems=60)}),minItems=1,maxItems=1),
                'teaching_timeline':array(obj({'id':string,'start_s':number,'end_s':number,'goal':string,'visible_evidence':string,
                    'requirement_ids':array({'type':'string','enum':required_ids},minItems=1),
                    **({'narration':{'type':'string','minLength':1,'maxLength':1600}} if current['task'].get('audio_narration_required') else {})}),
                    minItems=max(3,math.ceil(current['duration_seconds']/20)),maxItems=18),
                'source_edit_regions':array(box,minItems=1 if source else 0,maxItems=32 if source else 0),
                'source_operations':array(operations,minItems=1 if source else 0,maxItems=32 if source else 0)})
        result = OpenAI(base_url=os.environ.get('LOCAL_BASE_URL', 'http://127.0.0.1:8000/v1'),
                        api_key=os.environ.get('LOCAL_API_KEY', 'local'), timeout=600, max_retries=1).chat.completions.create(
            model=os.environ.get('LOCAL_MODEL', 'qwen3.8-27b'),
            messages=[{'role': 'user', 'content': content}], max_tokens=max_tokens, temperature=.3,
            extra_body={'chat_template_kwargs': {'enable_thinking': False}}, **structured)
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
