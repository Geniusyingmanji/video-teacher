"""Credential-free, network-disabled Manim execution for the official adapter."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from .code2video_source import default_source_dir, verify_source
from .common import write_json
from .native_pipeline import metadata

VERSION = 'official-code2video-adapter-v1'
DEFAULT_IMAGE = 'manimcommunity/manim:v0.19.0'


def inspect_image(image):
    if not shutil.which('docker'):
        raise ValueError('Code2Video needs Docker; install/start Docker and pull '+image)
    result = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
                            capture_output=True, text=True, timeout=20)
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise ValueError('Code2Video Docker image unavailable; pull '+image)
    return value


def settings_from(raw, config_dir):
    if raw is None: raw = {}
    if not isinstance(raw, dict): raise ValueError('code2video configuration must be an object')
    allowed = {'source_dir', 'docker_image', 'feedback_rounds', 'critic_frames', 'max_code_tokens',
               'max_fix_attempts', 'max_regenerate_attempts', 'max_feedback_attempts', 'render_timeout_s'}
    if set(raw)-allowed: raise ValueError('unknown code2video settings: '+', '.join(sorted(set(raw)-allowed)))
    path = Path(raw.get('source_dir', default_source_dir())).expanduser()
    if not path.is_absolute(): path = Path(config_dir)/path
    source = verify_source(path)
    values = {'feedback_rounds': 2, 'critic_frames': 8, 'max_code_tokens': 10000,
              'max_fix_attempts': 3, 'max_regenerate_attempts': 3,
              'max_feedback_attempts': 3, 'render_timeout_s': 180}
    limits = {'feedback_rounds': (1, 5), 'critic_frames': (4, 32), 'max_code_tokens': (1024, 32768),
              'max_fix_attempts': (1, 10), 'max_regenerate_attempts': (1, 10),
              'max_feedback_attempts': (1, 5), 'render_timeout_s': (30, 600)}
    for key, default in list(values.items()):
        val = raw.get(key, default); low, high = limits[key]
        if type(val) is not int or not low <= val <= high: raise ValueError('invalid code2video '+key)
        values[key] = val
    image = raw.get('docker_image', DEFAULT_IMAGE)
    if not isinstance(image, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_./:@-]+', image):
        raise ValueError('invalid code2video Docker image')
    return {**values, 'version': VERSION, 'upstream': source, 'docker_image': image,
            'docker_image_id': inspect_image(image), 'critic_model_policy': 'same_as_generator',
            'audio_policy': 'shared_tts_from_storyboard_before_codegen',
            'asset_policy': 'public_task_images_only', 'quality': '480p15',
            'adaptations': ['public_full_task_and_images', 'target_duration_and_narration',
                            'shared_budgeted_chat_transport', 'sampled_frames_and_official_grid_critic',
                            'container_render_and_section_order', 'strict_failure_and_media_validation']}


class DockerRenderer:
    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, directory, settings):
        self.directory = Path(directory).resolve()
        self.settings = settings
        self.durations = {}
        self.calls = 0

    def run(self, cmd, *, cwd, timeout, **unused):
        if Path(cwd).resolve() != self.directory:
            raise ValueError('Code2Video renderer cwd must be the public case workspace')
        if not cmd or cmd[0] not in {'manim', 'python'}:
            raise ValueError('unexpected upstream subprocess')
        self.calls += 1
        container = 'video-teacher-c2v-'+uuid.uuid4().hex
        # Containers see only the public case workspace, never API keys or task references.
        args = ['docker', 'run', '--rm', '--name', container, '--network', 'none', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--read-only', '--tmpfs', '/tmp:rw,size=512m',
                '--memory', '2g', '--cpus', '2', '--pids-limit', '256', '--user', f'{os.getuid()}:{os.getgid()}',
                '-e', 'HOME=/tmp', '-e', 'XDG_CACHE_HOME=/tmp/cache', '-v', str(self.directory)+':/work:rw',
                '-w', '/work', '--entrypoint', cmd[0], self.settings['docker_image_id'], *cmd[1:]]
        expected = None
        if cmd[0] == 'manim':
            if len(cmd) != 4 or cmd[1] != '-ql' or not re.fullmatch(r'section_[1-8]\.py', cmd[2]):
                raise ValueError('unexpected Manim render command')
            scene = cmd[3]
            if scene != Path(cmd[2]).stem.title().replace('_', '')+'Scene':
                raise ValueError('unexpected Manim scene')
            expected = self.directory/'media/videos'/Path(cmd[2]).stem/'480p15'/(scene+'.mp4')
            expected.unlink(missing_ok=True)
            args += ['--disable_caching']
        try:
            result = subprocess.run(args, capture_output=True, text=True,
                                    timeout=max(30, min(timeout, self.settings['render_timeout_s'])))
        except subprocess.TimeoutExpired:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=20)
            raise
        if result.returncode == 0 and expected:
            try:
                target = self.durations[Path(cmd[2]).stem]
                meta = metadata(expected)
                if abs(meta['duration']-target) > .2:
                    raise ValueError(f'section duration must be {target:.6f}s, got {meta["duration"]}s; '
                                     'adjust animation run_time/wait within the planned narration slot')
            except (ValueError, OSError, KeyError, RuntimeError) as exc:
                result = subprocess.CompletedProcess(args, 1, result.stdout, 'ValueError: '+str(exc))
        write_json(self.directory/'render_logs'/f'{self.calls:04d}.json',
                   {'command': cmd, 'returncode': result.returncode,
                    'stdout': result.stdout[-5000:], 'stderr': result.stderr[-5000:]})
        return result
