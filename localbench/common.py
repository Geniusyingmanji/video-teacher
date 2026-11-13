from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FIELDS = ('id', 'discipline', 'subdomain', 'task_type', 'prompt_text',
                 'pedagogical_target_audience', 'target_duration_s',
                 'audio_narration_required', 'narration_language')


def public_case(case):
    """Generation never receives the benchmark's private reference fields."""
    result={k: case[k] for k in PUBLIC_FIELDS if k in case}
    if case.get('source',{}).get('source_image_path'):
        from .assets import asset_path
        source=case['source']
        path=asset_path(source) if source.get('dataset')=='GRADE' else None
        result['public_attachments']=[{'role':'source_image','declared_source_path':source['source_image_path'],
                                       'local_path':str(path) if path and path.is_file() else None}]
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def parse_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        if start < 0:
            raise
        result, end = json.JSONDecoder().raw_decode(text[start:])
        if text[start + end:].strip():
            raise ValueError('unexpected trailing model response')
        return result
