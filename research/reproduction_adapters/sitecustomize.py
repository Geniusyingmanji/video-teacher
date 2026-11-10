"""Opt-in local model adapter; preserve author prompts and log every chat call.

Enabled only with REPRO_CHAT_LOG and REPRO_LOCAL_PORTS. This is an explicit
backbone replacement, never a claim of original-provider reproduction.
"""
import itertools
import json
import os
from pathlib import Path
import threading
import uuid


if os.environ.get('REPRO_CHAT_LOG') and os.environ.get('REPRO_LOCAL_PORTS'):
    import openai
    from openai.resources.chat.completions import Completions

    _original = Completions.create
    _ports = itertools.cycle(os.environ['REPRO_LOCAL_PORTS'].split(','))
    _lock = threading.Lock()
    _directory = Path(os.environ['REPRO_CHAT_LOG'])
    _directory.mkdir(parents=True, exist_ok=True)

    def create(self, *args, **kwargs):
        with _lock:
            port = next(_ports)
        ident = uuid.uuid4().hex
        original_model = kwargs.get('model')
        kwargs['model'] = 'qwen3.8-27b'
        kwargs['extra_body'] = {**(kwargs.get('extra_body') or {}),
                               'chat_template_kwargs': {'enable_thinking': False}}
        if 'max_tokens' not in kwargs and 'max_completion_tokens' not in kwargs:
            kwargs['max_tokens'] = 8192
        base = f'http://127.0.0.1:{port}/v1'
        (_directory/(ident+'.request.json')).write_text(json.dumps({
            'original_model': original_model, 'base_url': base, 'request': kwargs},
            ensure_ascii=False, default=str, indent=2)+'\n')
        client = openai.OpenAI(base_url=base, api_key='local', timeout=600, max_retries=1)
        try:
            response = _original(client.chat.completions, *args, **kwargs)
        except Exception as exc:
            (_directory/(ident+'.error.txt')).write_text(repr(exc))
            client.close()
            raise
        if kwargs.get('stream'):
            def chunks():
                try:
                    with (_directory/(ident+'.chunks.jsonl')).open('w') as handle:
                        for chunk in response:
                            handle.write(chunk.model_dump_json()+'\n')
                            handle.flush()
                            yield chunk
                finally:
                    response.close()
                    client.close()
            return chunks()
        (_directory/(ident+'.response.json')).write_text(response.model_dump_json(indent=2)+'\n')
        client.close()
        return response

    Completions.create = create
