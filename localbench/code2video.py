"""Official Code2Video planning/coding/repair with explicit benchmark adaptations."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import shutil
import threading

import imageio_ffmpeg
from PIL import Image

from .code2video_runtime import DockerRenderer, VERSION
from .code2video_source import load_definitions, verify_source
from .common import digest, public_case, write_json
from .native_pipeline import metadata
from .pipeline import run_command, synthesize
from .provenance import file_hash
from .scene import validate_plan
from .timing import normalize_plan_timing

STORYBOARD_CONTRACT = '''\nBenchmark delivery adaptation:
Use 4..8 ordered sections with IDs section_1, section_2, ... . Preserve the outline order.
In addition to the original storyboard fields, each section MUST have duration_s (4..24)
and narration (English, 5..70 words, roughly 2 spoken words/second). The section durations
must sum to the public target_duration_s. Narration explains the planned animations and
solution steps; lecture_lines remain short on-screen bullets, not the whole spoken script.
Public task images are allowed inputs, not decorative references. Preserve their givens.
If the task requires showing the original image, use its supplied /work/input_XX.png path
with Manim ImageMobject. This permitted input overrides the generic no-image instruction.
Do not add unrelated material to fill time. No external asset downloads.'''


def image_part(path):
    return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,'+
            base64.b64encode(Path(path).read_bytes()).decode()}}


def critic_evidence(video, directory, count):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    reader = imageio_ffmpeg.read_frames(str(video), pix_fmt='rgb24')
    meta = next(reader)
    indices = sorted({round((meta['duration']*meta['fps']-1)*(.03+.94*i/(count-1))) for i in range(count)})
    records = []
    for index, raw in enumerate(reader):
        if index not in indices: continue
        path = directory/f'frame_{index:06d}.png'
        im = Image.frombytes('RGB', meta['size'], raw); im.thumbnail((960, 540)); im.save(path)
        records.append({'time_s': index/meta['fps'], 'path': str(path.resolve()), 'sha256': file_hash(path)})
    if len(records) != len(indices): raise ValueError('Code2Video critic could not decode planned frames')
    write_json(directory/'frames.json', records)
    return records


def storyboard_plan(agent, case):
    sections = agent.sections
    expected = [f'section_{i+1}' for i in range(len(sections))]
    if not 4 <= len(sections) <= 8 or [s.id for s in sections] != expected:
        raise ValueError('Code2Video requires 4..8 ordered, unique section_1..section_8 IDs')
    data = agent.enhanced_storyboard['sections']
    scenes = []
    for section, row in zip(sections, data):
        for field in ('lecture_lines', 'animations'):
            values = getattr(section, field)
            if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError('Code2Video needs nonempty textual '+field)
        scenes.append({'title': section.title[:55], 'duration_s': row['duration_s'],
                       'narration': row['narration'], 'caption': section.lecture_lines[0][:100],
                       'primitives': [{'type': 'text', 'x': .5, 'y': .5, 'text': 'Manim section'}]})
    plan = normalize_plan_timing({'case_id': case['id'], 'scenes': scenes}, case['target_duration_s'])
    validate_plan(plan, case)
    return plan


def assemble(agent, plan, audio, directory):
    """Preserve every section, original order and actual speed; no padding/trimming."""
    normalized = []
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for index, (section, scene) in enumerate(zip(agent.sections, plan['scenes'])):
        video = Path(agent.section_videos[section.id])
        meta = metadata(video)
        if abs(meta['duration']-scene['duration_s']) > .2:
            raise ValueError('Code2Video section duration differs from measured narration slot: '+section.id)
        # Attach each measured audio slot to its own section. This avoids drift
        # accumulating into later sections when a Manim frame rounds the duration.
        slot = directory/'narration'/f'scene_{index:02d}'/'slot.wav'
        output = directory/f'narrated_{section.id}.mp4'
        run_command([ffmpeg, '-y', '-loglevel', 'error', '-i', str(video), '-i', str(slot),
                     '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                     '-b:a', '96k', '-movflags', '+faststart', str(output)])
        normalized.append(output)
    concat = directory/'section_concat.txt'
    concat.write_text(''.join("file '"+str(p.resolve()).replace("'", "'\\''")+"'\n" for p in normalized))
    output = directory/'code2video.mp4'
    run_command([ffmpeg, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat),
                 '-c', 'copy', '-movflags', '+faststart', str(output)])
    meta = metadata(output, decode=True)
    if abs(meta['duration']-sum(s['duration_s'] for s in plan['scenes'])) > .5:
        raise ValueError('Code2Video complete video duration differs from the public target')
    return {'mode': 'code2video', 'complete': True, 'video_path': str(output.resolve()),
            'sha256': file_hash(output), 'duration_s': meta['duration'],
            'frame_count': meta['frame_count'], 'fps': meta['fps'], 'size': meta['size']}


def generate_code2video(case, out, client, settings, tts):
    from .scientific_audit import validate_public
    validate_public(public_case(case))
    directory = (Path(out)/case['id']).resolve(); directory.mkdir(parents=True, exist_ok=True)
    verify_source(settings['upstream']['source_dir'])
    public = public_case(case)
    write_json(directory/'public_input.json', public)
    write_json(directory/'adapter.json', settings)
    # Only public inputs enter the mounted workspace or generation messages.
    brief = copy.deepcopy(public); images = []
    for index, attachment in enumerate(brief.get('public_attachments', [])):
        source = Path(attachment['local_path'])
        target = directory/f'input_{index:02d}.png'
        with Image.open(source) as im: im.convert('RGB').save(target)
        images.append(image_part(target))
        attachment['local_path'] = '/work/'+target.name
    context = '\nPUBLIC BENCHMARK TASK:\n'+json.dumps(brief, ensure_ascii=False)
    requests = []; guard = threading.Lock(); critic_errors = []
    def invoke(prompt, max_tokens=10000):
        with guard: index = len(requests); requests.append(index)
        messages = [{'role': 'user', 'content': [{'type': 'text', 'text': prompt+context}, *images]}]
        response = client.chat(messages, purpose=f'code2video:{case["id"]}:request_{index:04d}',
                               max_tokens=min(max_tokens, settings['max_code_tokens']), json_mode=False)
        write_json(directory/'requests'/f'{index:04d}.json', {'prompt': prompt, 'response': response})
        # The authoritative usage is the shared client ledger, including repairs/critic.
        return response, {}
    ns = load_definitions(settings['upstream']['source_dir'])
    def upstream_log(*values, **kwargs):
        with guard:
            with (directory/'upstream.log').open('a', encoding='utf-8') as stream:
                print(*values, file=stream)
    ns['print'] = upstream_log
    renderer = DockerRenderer(directory, settings)
    ns['subprocess'] = renderer
    base_outline = ns['get_prompt1_outline']; base_storyboard = ns['get_prompt2_storyboard']
    ns['get_prompt1_outline'] = lambda knowledge_point, reference_image_path=None: (
        base_outline(knowledge_point, duration=case['target_duration_s']/60,
                     reference_image_path=reference_image_path)+STORYBOARD_CONTRACT)
    ns['get_prompt2_storyboard'] = lambda **kw: base_storyboard(**kw)+STORYBOARD_CONTRACT
    grid = Path(settings['upstream']['source_dir'])/'assets/reference/GRID.png'
    critic_calls = []
    def critique(prompt, video_path, image_path):
        index = len(critic_calls); critic_calls.append(index)
        destination = directory/'critic'/f'{index:04d}'
        records = critic_evidence(video_path, destination, settings['critic_frames'])
        content = [{'type': 'text', 'text': prompt+context+
                    '\nThe following are timestamped frames of the actual rendered section, followed by the official grid reference.'}]
        for record in records:
            content += [{'type': 'text', 'text': f'Video time {record["time_s"]:.3f}s'}, image_part(record['path'])]
        content += [{'type': 'text', 'text': 'Official layout grid reference'}, image_part(grid)]
        raw = client.chat([{'role': 'user', 'content': content}],
                          purpose=f'code2video:{case["id"]}:critic_{index:04d}', max_tokens=3000)
        write_json(destination/'response.json', raw)
        layout = raw.get('layout', {})
        if type(layout.get('has_issues')) is not bool or not isinstance(layout.get('improvements'), list):
            raise ValueError('Code2Video critic returned invalid layout feedback')
        if any(not isinstance(r, dict) or not all(isinstance(r.get(k), str) for k in ('problem', 'solution'))
               for r in layout['improvements']):
            raise ValueError('Code2Video critic returned invalid improvements')
        if layout['has_issues'] and not layout['improvements']:
            raise ValueError('Code2Video critic reported issues without actionable feedback')
        return json.dumps(raw)
    ns['request_gemini_video_img'] = critique
    official = ns['TeachingVideoAgent']
    class AdaptedAgent(official):
        def __init__(self):
            # Upstream constructor assumes CASES, its own reference database and
            # a module-global API. Replace only those environment bindings.
            self.idx = case['id']; self.learning_topic = context
            self.folder = str(directory.parent); self.output_dir = directory
            self.use_feedback = True; self.use_assets = False; self.API = invoke
            self.feedback_rounds = settings['feedback_rounds']; self.iconfinder_api_key = ''
            self.max_code_token_length = settings['max_code_tokens']
            self.max_fix_bug_tries = settings['max_fix_attempts']
            self.max_regenerate_tries = settings['max_regenerate_attempts']
            self.max_feedback_gen_code_tries = settings['max_feedback_attempts']
            self.max_mllm_fix_bugs_tries = settings['max_fix_attempts']
            self.scope_refine_fixer = ns['ScopeRefineFixer'](invoke, self.max_code_token_length)
            self.extractor = ns['GridPositionExtractor']()
            self.KNOWLEDGE2PATH = {context: images and 'input_00.png' or None}
            self.knowledge_ref_img_folder = directory; self.GRID_IMG_PATH = grid
            self.outline = self.enhanced_storyboard = None
            self.sections = []; self.section_codes = {}; self.section_videos = {}; self.video_feedbacks = {}
            self.token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

        def get_mllm_feedback(self, section, video_path, round_number=1):
            feedback = super().get_mllm_feedback(section, video_path, round_number)
            if (feedback.raw_response or '').startswith('Error:'):
                critic_errors.append({'section': section.id, 'round': round_number,
                                      'status': 'critic_error', 'error': feedback.raw_response})
                raise ValueError('Code2Video critic failed; do not interpret as no issues')
            write_json(directory/'feedback'/f'{section.id}_{round_number}.json', feedback.__dict__)
            return feedback

        def optimize_with_feedback(self, section, feedback):
            # A failed refinement must retain matching source and media, not a
            # modified source file paired with an earlier successful render.
            if not feedback.has_issues or not feedback.suggested_improvements:
                return super().optimize_with_feedback(section, feedback)
            code = self.section_codes[section.id]
            previous = Path(self.section_videos[section.id])
            saved = directory/f'retained_{section.id}.mp4'
            if previous.resolve() != saved.resolve(): shutil.copyfile(previous, saved)
            try:
                ok = super().optimize_with_feedback(section, feedback)
            except Exception:
                self.section_codes[section.id] = code
                (directory/f'{section.id}.py').write_text(code)
                self.section_videos[section.id] = str(saved)
                raise
            if not ok:
                self.section_codes[section.id] = code
                (directory/f'{section.id}.py').write_text(code)
                self.section_videos[section.id] = str(saved)
            return ok
    agent = AdaptedAgent()
    try:
        agent.generate_outline()
        # Validate IDs before upstream code paths can use them as filenames.
        agent.generate_storyboard()
        plan = storyboard_plan(agent, case)
        audio, _ = synthesize(plan, directory/'narration', tts=tts)
        write_json(directory/'narration_plan.json', plan)
        for section, scene in zip(agent.sections, plan['scenes']):
            renderer.durations[section.id] = scene['duration_s']
            section.animations = [*section.animations,
                f'DELIVERY TIMING: construct() lasts exactly {scene["duration_s"]:.6f} seconds. '
                'Set run_time and waits accordingly. External narration is attached after rendering; do not generate audio. '
                f'Animate in this spoken order: {scene["narration"]}']
        agent.generate_codes()
        if any(s.id not in agent.section_codes for s in agent.sections):
            raise ValueError('Code2Video did not generate all section programs')
        # Outer CLI limits parallel lessons. Keep sections sequential to avoid
        # upstream process workers losing callbacks, state and shared budgets.
        for section in agent.sections:
            if not agent.render_section(section):
                raise ValueError('Code2Video section failed: '+section.id)
        if critic_errors:
            raise ValueError('Code2Video mandatory critic stage incomplete')
        artifact = assemble(agent, plan, audio, directory)
        result = {'id': case['id'], 'status': 'rendered', 'artifacts': [artifact],
                  'public_input_hash': digest(public), 'framework': 'official_code2video_adapted',
                  'adapter_version': VERSION, 'upstream_commit': settings['upstream']['commit'],
                  'private_reference_used_for_generation': False, 'section_order': [s.id for s in agent.sections]}
        write_json(directory/'manifest.json', result)
        return result
    finally:
        write_json(directory/'framework_status.json', {'critic_errors': critic_errors,
                   'planned_sections': [s.id for s in agent.sections],
                   'rendered_sections': list(agent.section_videos), 'transport_requests': len(requests),
                   'critic_requests': len(critic_calls), 'usage_source': 'shared api/usage.jsonl'})
