"""Preserve renderer failures when the upstream agent returns no video."""
from pathlib import Path


def render_failure(output_dir):
    logs = []
    for path in sorted(Path(output_dir).glob('section_*_render.log'))[:8]:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 8000))
            tail = stream.read().decode('utf-8', errors='replace')
        logs.append({'path': str(path), 'tail': tail})
    error = 'Video generation returned no complete video; inspect preserved section render logs.'
    if logs:
        lines = [line.strip() for line in logs[-1]['tail'].splitlines() if line.strip()]
        if lines:
            error += ' Last render diagnostic: ' + lines[-1][-1200:]
    return error, logs
