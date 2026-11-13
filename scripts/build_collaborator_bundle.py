#!/usr/bin/env python3
"""Create a local, relocatable collaborator bundle using an explicit file allowlist."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from localbench.common import public_case, read_jsonl
from localbench.rubric import VERSION as RUBRIC_VERSION


def build(destination):
    files = {ROOT/name for name in ('teacher.py', 'AGENTS.md', 'PAPER_PLAN.md', 'requirements.txt', 'requirements-tts.txt')}
    files.update(p for p in (ROOT/'localbench').rglob('*') if p.is_file() and p.suffix in {'.py', '.md'})
    files.update((ROOT/'tests').glob('test_localbench*.py'))
    files.update((ROOT/'configs').glob('*.json'))
    files.update((ROOT/'docs').glob('*.md'))
    files.update((ROOT/'scripts').glob('*.py'))
    files.add(ROOT/'tests/fixtures/layout_language_overflow.jpg')
    files.update(ROOT/'data'/name for name in ('source_tasks.jsonl', 'tasks.jsonl', 'tasks.summary.json', 'development_membership.json'))
    files.update((ROOT/'data/reference_corrections').glob('*.json'))
    # Source metadata is compact; media must be selected from current task inputs.
    # Do not bundle duplicate before/ copies, target images, or unrelated samples.
    files.update(p for p in (ROOT/'data/sources').rglob('*') if p.is_file() and p.suffix.lower() in {'.json', '.jsonl', '.pgn'})
    rows = read_jsonl(ROOT/'data/tasks.jsonl')
    for row in rows:
        for attachment in public_case(row).get('public_attachments', []):
            if not attachment.get('local_path'):
                raise ValueError('missing public image: '+row['id'])
            path = Path(attachment['local_path']).resolve()
            path.relative_to(ROOT/'data/sources/grade/selected_assets/image/before')
            files.add(path)
        # Preserve explicitly declared input images for generated source tasks.
        # These remain source assets; this does not change generator input routing.
        source = row.get('source', {})
        if source.get('local_before_path'):
            relative = Path(source['local_before_path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('unsafe source input path')
            path = (ROOT/relative).resolve()
            path.relative_to(ROOT/'data/sources/disciplinegen/generated_sports')
            if path.suffix.lower() not in {'.png', '.jpg', '.jpeg'} or 'editing' not in path.parts:
                raise ValueError('expected a declared source input image')
            files.add(path)
    blobs = {}
    for path in sorted(files):
        if not path.is_file() or path.is_symlink(): raise ValueError('missing or symlinked bundle input')
        relative = str(path.relative_to(ROOT))
        if relative.startswith(('results/', 'dist/', '.git/', '.venv/', '.local-cache/', '.config/')):
            raise ValueError('unsafe bundle member')
        if path.suffix.lower() in {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.wav', '.mp3', '.aiff', '.flac', '.m4a'}:
            raise ValueError('video/audio outputs do not belong in the code bundle')
        blobs[relative] = path.read_bytes()
    blobs['README.md'] = (ROOT/'README.md').read_bytes()
    manifest = {'format': 'collaborator-bundle-v1', 'cases': len(rows),
                'rubric_version': RUBRIC_VERSION,
                'media_scope': 'Only declared task input images and one layout test fixture; no experiment video/audio, target images, runtime cache or model weights.',
                'source_images': sum(name.startswith('data/sources/') and Path(name).suffix.lower() in {'.png','.jpg','.jpeg'} for name in blobs),
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in blobs.items()}}
    blobs['BUNDLE-MANIFEST.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists(): raise ValueError('bundle already exists; choose a fresh path')
    with tarfile.open(destination, 'w:gz') as tar:
        for name, data in sorted(blobs.items()):
            info = tarfile.TarInfo('video-teacher/'+name); info.size = len(data); info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    print(json.dumps({'bundle': str(destination.resolve()), 'files': len(blobs), 'cases': len(rows),
                      'source_images': manifest['source_images'], 'bytes': destination.stat().st_size,
                      'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    build(p.parse_args().out)
