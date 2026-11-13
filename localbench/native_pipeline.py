"""Full lessons from API-generated shots and a shared measured narration track."""
from __future__ import annotations

import base64
import concurrent.futures
import json
import math
import mimetypes
from pathlib import Path

import imageio_ffmpeg

from .common import digest, public_case, write_json
from .pipeline import run_command, synthesize
from .provenance import file_hash
from .scene import validate_plan
from .timing import normalize_plan_timing

SYSTEM = '''Plan a complete English narrated educational lesson using only the public task.
Return JSON {case_id, scenes:[{title,duration_s,narration,caption,visual_prompt}]}.
Use 4..8 scenes, each 4..24 seconds, sum exactly to target_duration_s.
Each narration has 5..70 words; aim at 2 spoken words/second. Titles <=65 characters,
captions <=120 characters. Explain all requested concepts or solution steps in order.
visual_prompt describes the actual diagram/action needed during that narration, including
literal labels, quantities, relations, layout, and consistent colors. Each prompt is 20..1800
characters. Keep a consistent educational visual style. No hidden answers are provided.
The supplied source image, if any, is the public task input; preserve its relevant givens.
Do not invent dimensions or replace source data. Do not add unrelated material to fill time.'''


def metadata(path, *, decode=False):
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
    meta = next(reader)
    if decode: meta['frame_count'] = sum(1 for _ in reader)
    else: reader.close()
    return meta


def generate_native(case, out, client, api, tts):
    directory = Path(out)/case['id']; directory.mkdir(parents=True, exist_ok=True)
    public = public_case(case)
    write_json(directory/'public_input.json', public)
    content = [{'type': 'text', 'text': json.dumps(public, ensure_ascii=False)}]
    image_url = None
    if public.get('public_attachments'):
        p = Path(public['public_attachments'][0]['local_path'])
        image_url = 'data:'+(mimetypes.guess_type(p)[0] or 'image/png')+';base64,'+base64.b64encode(p.read_bytes()).decode()
        content.append({'type': 'image_url', 'image_url': {'url': image_url}})
    plan_path = directory/'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    else:
        messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': content}]
        for attempt in range(3):
            try:
                plan = client.chat(messages, purpose='native_lesson_plan:'+case['id'], max_tokens=6000)
                write_json(directory/f'plan_raw_{attempt}.json', plan)
                for scene in plan['scenes']:
                    # Only these fields are accepted; no model-authored local paths/state.
                    for key in list(scene):
                        if key not in {'title', 'duration_s', 'narration', 'caption', 'visual_prompt'}: scene.pop(key)
                    if not isinstance(scene.get('visual_prompt'), str) or not 20 <= len(scene['visual_prompt']) <= 1800:
                        raise ValueError('each scene needs a 20..1800 character visual_prompt')
                    scene['primitives'] = [{'type': 'text', 'x': .5, 'y': .5, 'text': 'native video'}]
                plan = normalize_plan_timing(plan, case['target_duration_s'])
                validate_plan(plan, case)
                break
            except (ValueError, KeyError, TypeError) as exc:
                if attempt == 2: raise
                messages.append({'role': 'user', 'content': 'Return a complete corrected JSON plan. '+str(exc)[:400]})
        write_json(plan_path, plan)
    audio, _ = synthesize(plan, directory, tts=tts)
    write_json(plan_path, plan)
    jobs = []
    for index, scene in enumerate(plan['scenes']):
        count = math.ceil(scene['duration_s']/api.service.max_shot_seconds)
        seconds = scene['duration_s']/count
        for part in range(count):
            prompt = (f'Educational lesson: {public["prompt_text"]}\n'
                      f'Scene {index+1}/{len(plan["scenes"])}, segment {part+1}/{count}.\n'
                      f'What the narration explains: {scene["narration"]}\n'
                      f'Visual scene: {scene["visual_prompt"]}\n'
                      'Generate the requested visual demonstration. Narration is supplied separately; no music required.')
            jobs.append({'index': len(jobs), 'scene': index, 'duration_s': seconds,
                         'requested_seconds': max(4, math.ceil(seconds)), 'prompt': prompt})
    write_json(directory/'shot_plan.json', jobs)
    def generate(job):
        path = api.generate(job['prompt'], job['requested_seconds'], directory/'shots'/f'{job["index"]:03d}', image_url)
        meta = metadata(path)
        if meta['duration']+.05 < job['duration_s']:
            raise ValueError('provider clip is shorter than the narration slot; refusing to loop or stretch it')
        return {**job, 'path': str(path.resolve()), 'sha256': file_hash(path), 'returned_duration_s': meta['duration']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
        clips = list(workers.map(generate, jobs))
    write_json(directory/'clips.json', clips)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    normalized = []
    for clip in clips:
        dest = directory/f'shot_{clip["index"]:03d}.mp4'
        run_command([ffmpeg, '-y', '-loglevel', 'error', '-i', clip['path'], '-t', str(clip['duration_s']),
                     '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24',
                     '-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', str(dest)])
        normalized.append(dest)
    concat = directory/'shot_concat.txt'
    concat.write_text(''.join("file '"+str(p.resolve()).replace("'", "'\\''")+"'\n" for p in normalized))
    output = directory/'native.mp4'
    run_command([ffmpeg, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat),
                 '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                 '-b:a', '96k', '-movflags', '+faststart', str(output)])
    meta = metadata(output, decode=True)
    if abs(meta['duration']-case['target_duration_s']) > .5:
        raise ValueError('native assembled lesson duration differs from target')
    artifact = {'mode': 'native', 'complete': True, 'video_path': str(output.resolve()), 'sha256': file_hash(output),
                'duration_s': meta['duration'], 'frame_count': meta['frame_count'], 'fps': meta['fps'], 'size': meta['size']}
    result = {'id': case['id'], 'status': 'rendered', 'artifacts': [artifact], 'public_input_hash': digest(public),
              'method': 'planned_native_shots_with_shared_tts', 'private_reference_used_for_generation': False,
              'audio_policy': 'native clip audio discarded; identical external narration protocol for code/native paths',
              'video_service': api.service.public(), 'shots': len(clips)}
    write_json(directory/'manifest.json', result)
    return result
