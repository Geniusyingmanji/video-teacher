#!/usr/bin/env python3
"""Validate an unpacked collaborator bundle with the current Python environment.

No model calls or dependency installation. This checks relocation and offline
preflight; it does not replace a fresh Linux install and live video smoke test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import tempfile


def validate(bundle, output):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('validation receipt already exists; choose a new path')
    stage = Path(tempfile.mkdtemp(prefix='video-teacher-bundle-'))
    secrets = [v.encode() for k, v in os.environ.items()
               if k.startswith('VIDEO_TEACHER_') and ('KEY' in k or 'TOKEN' in k) and len(v) >= 12]
    seen = set()
    with tarfile.open(bundle) as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or '..' in name.parts
                    or len(name.parts) < 2 or name.parts[0] != 'video-teacher'
                    or name.parts[1] in {'results', 'dist', '.git', '.venv', '.local-cache'}
                    or name.suffix.lower() in {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.wav', '.mp3', '.aiff', '.flac', '.m4a'}
                    or str(name) in seen):
                raise ValueError('invalid or duplicate bundle member')
            seen.add(str(name))
            blob = archive.extractfile(member).read()
            if any(secret in blob for secret in secrets):
                raise ValueError('configured secret found in bundle; value withheld')
            destination = stage.joinpath(*name.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)
    app = stage/'video-teacher'
    manifest = json.loads((app/'BUNDLE-MANIFEST.json').read_text())
    expected = {'video-teacher/'+name for name in manifest['files']}
    if seen != expected | {'video-teacher/BUNDLE-MANIFEST.json'}:
        raise ValueError('archive inventory differs from manifest')
    for name, meta in manifest['files'].items():
        blob = (app/name).read_bytes()
        if len(blob) != meta['bytes'] or hashlib.sha256(blob).hexdigest() != meta['sha256']:
            raise ValueError('manifest hash/size mismatch: '+name)
    env = {k: v for k, v in os.environ.items() if not k.startswith('VIDEO_TEACHER_')}
    # Avoid accidentally importing the developer checkout through an ambient path.
    env.pop('PYTHONPATH', None)
    env.update(VIDEO_TEACHER_API_KEY='offline-placeholder-not-a-secret',
               VIDEO_TEACHER_CREDENTIALS='/nonexistent-ambient-credentials-forbidden')
    offline_tests = '''import socket, pytest
def forbidden(*args, **kwargs):
    raise AssertionError('offline tests attempted network')
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
raise SystemExit(pytest.main(['tests', '-q']))
'''
    with (stage/'tests.log').open('w') as log:
        tests = subprocess.run([sys.executable, '-c', offline_tests],
                               cwd=app, env=env, stdout=log, stderr=subprocess.STDOUT)
    code = '''import sys, httpx, socket
from pathlib import Path
from localbench.run import main
from localbench.common import ROOT, read_jsonl, public_case
assert ROOT.resolve() == Path.cwd().resolve(), 'imported wrong checkout'
for row in read_jsonl(ROOT/'data/tasks.jsonl'):
    for attachment in public_case(row).get('public_attachments', []):
        Path(attachment['local_path']).resolve().relative_to(ROOT.resolve())
        assert Path(attachment['local_path']).is_file()
def forbidden(*args, **kwargs):
    raise AssertionError('doctor attempted network')
httpx.Client.request = forbidden
socket.socket.connect = forbidden
sys.argv = ['teacher.py','doctor','--suite','all','--model','qwen3.8-flash','--url','https://example.test/v1']
raise SystemExit(main())
'''
    doctor = subprocess.run([sys.executable, '-c', code], cwd=app, env=env,
                            capture_output=True, text=True)
    (stage/'doctor.log').write_text(doctor.stdout+doctor.stderr)
    receipt = {
        'bundle': str(bundle), 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
        'stage': str(stage), 'platform': platform.platform(), 'system': platform.system(),
        'python': sys.version, 'interpreter': sys.executable,
        'validation_scope': 'relocated package with existing interpreter; no fresh dependency installation or live model test',
        'manifest_hashes_match': True, 'environment_secret_values_checked': len(secrets),
        'environment_secrets_absent': True if secrets else None,
        'cases': manifest['cases'], 'source_images': manifest['source_images'],
        'tests_network_blocked': True, 'tests_exit': tests.returncode, 'tests_log': str(stage/'tests.log'),
        'doctor_exit': doctor.returncode, 'doctor_network_blocked': True,
        'doctor_log': str(stage/'doctor.log'),
        'passed': tests.returncode == doctor.returncode == 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print((stage/'tests.log').read_text()[-1800:])
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['passed'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(validate(args.bundle, args.out))
