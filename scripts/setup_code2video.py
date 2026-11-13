#!/usr/bin/env python3
"""Download only hash-pinned upstream generation sources, outside this repository."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from localbench.common import ROOT
from localbench.code2video_source import default_source_dir, source_lock, verify_source


def setup(destination):
    destination = Path(destination).expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError('store upstream sources outside this repository')
    lock = source_lock()
    def fetch(item):
        name, expected = item
        path = destination/name
        if path.is_symlink(): raise ValueError('refusing symlink source: '+name)
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('existing source differs; refusing overwrite: '+name)
            return
        url = 'https://raw.githubusercontent.com/showlab/Code2Video/'+lock['commit']+'/'+name
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('upstream download hash mismatch: '+name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(content)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, lock['files'].items()))
    verify_source(destination)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=default_source_dir())
    args = parser.parse_args()
    print(setup(args.out))
