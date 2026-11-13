"""Immutable protocol snapshots and verified input inventories for local runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import ROOT, write_json


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def freeze_run(out, config):
    out = Path(out)
    # Include protocol subpackages, not only top-level modules.
    sources = {p.relative_to(ROOT/'localbench').as_posix():p.read_bytes()
               for p in (ROOT/'localbench').rglob('*.py')}
    hashes = {name:hashlib.sha256(content).hexdigest() for name,content in sources.items()}
    config = {**config, 'source_hashes':hashes}
    prior = out/'run_config.json'
    if prior.exists() and json.loads(prior.read_text()) != config:
        raise ValueError('run inputs/configuration/source changed; choose a fresh output directory')
    for name, content in sources.items():
        path = out/'source_snapshot'/name
        if path.exists() and path.read_bytes() != content:
            raise ValueError('source snapshot changed; choose a fresh output directory')
    for name, content in sources.items():
        path = out/'source_snapshot'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    write_json(prior, config)
    return config


def evaluation_inventory(run, cases):
    jobs = []
    seen = set()
    for case in run['cases']:
        id_ = case['id']
        if id_ not in cases:
            raise ValueError(f'unknown evaluation case {id_}')
        for artifact in case.get('artifacts', []):
            if not artifact.get('complete'):
                continue
            mode = artifact['mode']
            if not mode or Path(mode).name != mode or mode in {'.','..'} or Path(id_).name != id_ or id_ in {'.','..'}:
                raise ValueError('case/mode must be a single path component')
            if (id_,mode) in seen:
                raise ValueError(f'duplicate evaluation case/mode: {id_}/{mode}')
            seen.add((id_,mode))
            actual = file_hash(artifact['video_path'])
            if artifact.get('sha256') != actual:
                raise ValueError(f'video hash mismatch: {id_}/{mode}')
            jobs.append((id_,artifact))
    if not jobs:
        raise ValueError('no completed videos to evaluate')
    return jobs
