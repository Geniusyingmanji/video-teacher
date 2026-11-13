"""Pinned, external Code2Video source snapshot and isolated definition loading."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import types
import uuid

from .common import ROOT
from .provenance import file_hash

LOCK_PATH = ROOT/'configs/code2video.upstream.json'


def source_lock():
    return json.loads(LOCK_PATH.read_text())


def default_source_dir():
    return Path.home()/'.cache/video-teacher/code2video'/source_lock()['commit']


def verify_source(directory):
    directory = Path(directory).expanduser().resolve()
    lock = source_lock()
    for name, expected in lock['files'].items():
        path = directory/name
        if not path.is_file() or path.is_symlink() or file_hash(path) != expected:
            raise ValueError('Code2Video source missing or changed: '+name+'; run scripts/setup_code2video.py')
    return {**lock, 'source_dir': str(directory)}


def load_definitions(directory):
    """Keep official definitions; bypass upstream provider SDKs, CLI and host Manim imports.

    Each run has its own module globals, so transports/prompts cannot leak between
    concurrent cases. No generated Python is loaded in the orchestrator.
    """
    verify_source(directory)
    name = '_video_teacher_code2video_'+uuid.uuid4().hex
    module = types.ModuleType(name)
    sys.modules[name] = module
    ns = module.__dict__
    try:
        for filename in ('prompts/base_class.py', 'prompts/stage1.py', 'prompts/stage2.py',
                         'prompts/stage3.py', 'prompts/stage4.py', 'src/utils.py',
                         'src/scope_refine.py', 'src/agent.py'):
            path = Path(directory)/filename
            tree = ast.parse(path.read_text(), filename=str(path))
            if filename == 'src/utils.py':
                names = {'extract_json_from_markdown', 'extract_answer_from_response', 'replace_base_class'}
                tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
            elif filename == 'src/agent.py':
                classes = {'Section', 'TeachingOutline', 'VideoFeedback', 'RunConfig', 'TeachingVideoAgent'}
                tree.body = [node for node in tree.body if
                             isinstance(node, ast.ClassDef) and node.name in classes or
                             isinstance(node, ast.Import) or
                             isinstance(node, ast.ImportFrom) and node.module in
                             {'typing', 'dataclasses', 'pathlib', 'concurrent.futures'}]
            exec(compile(tree, str(path), 'exec'), ns)
    finally:
        # Dataclasses need this registration during construction, not a persistent
        # global module that retains clients and their credentials after the run.
        sys.modules.pop(name, None)
    return ns
