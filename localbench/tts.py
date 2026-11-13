"""Portable narration backends with explicit voices and bounded execution."""
from __future__ import annotations

import asyncio
import importlib.util
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg


def resolve_tts(config=None):
    config = dict(config or {})
    backend = config.get('backend', 'auto')
    if backend == 'auto':
        backend = 'say' if shutil.which('say') else 'espeak' if (shutil.which('espeak-ng') or shutil.which('espeak')) else 'edge'
    if backend not in {'say', 'espeak', 'edge'}:
        raise ValueError('TTS backend must be auto, say, espeak, or edge')
    if backend == 'say' and not shutil.which('say'):
        raise ValueError('macOS say unavailable; select edge or install espeak-ng')
    if backend == 'espeak' and not (shutil.which('espeak-ng') or shutil.which('espeak')):
        raise ValueError('install espeak-ng or select the edge TTS backend')
    if backend == 'edge' and importlib.util.find_spec('edge_tts') is None:
        raise ValueError('install requirements-tts.txt for Edge TTS, or install espeak-ng for offline narration')
    defaults = {'say': 'Samantha', 'espeak': 'en-us', 'edge': 'en-US-AriaNeural'}
    return {'backend': backend, 'voice': config.get('voice') or defaults[backend],
            'sample_rate': 24000, 'network_required': backend == 'edge'}


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{Path(args[0]).name} narration failed: {result.stderr[-600:]}')


def synthesize_speech(text_path, output, rate, config):
    backend, voice = config['backend'], config['voice']
    if backend == 'say':
        raw = output.with_suffix('.aiff')
        command(['say', '-v', voice, '-r', str(rate), '-f', str(text_path), '-o', str(raw)])
    elif backend == 'espeak':
        raw = output.with_name('espeak_raw.wav')
        executable = shutil.which('espeak-ng') or shutil.which('espeak')
        command([executable, '-v', voice, '-s', str(rate), '-f', str(text_path), '-w', str(raw)])
    else:
        import edge_tts
        raw = output.with_suffix('.mp3')
        # The actual duration is measured by the common scheduler afterwards.
        percent = round((rate/155-1)*100)
        async def run():
            await asyncio.wait_for(edge_tts.Communicate(text_path.read_text(), voice,
                                   rate=f'{percent:+d}%').save(str(raw)), timeout=90)
        asyncio.run(run())
    command([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(raw),
             '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(output)])
