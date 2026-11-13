"""Explicit collaborator service configuration and shared model-call budgeting."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import threading
from urllib.parse import urlparse

from .client import MatrixClient


def chat_url(url):
    url = url.rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('service URL must be an absolute HTTP(S) URL')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('put credentials in the API key field, not the URL')
    if parsed.path.endswith('/chat/completions'):
        return url
    if parsed.path in ('', '/'):
        return url+'/v1/chat/completions'
    return url+'/chat/completions'


@dataclass
class Service:
    model: str
    url: str
    api_key: str = field(repr=False)
    json_format: bool = True
    extra_body: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.model or not self.api_key:
            raise ValueError('model and API key must be nonempty')
        self.url = chat_url(self.url)

    def public(self):
        return {'model': self.model, 'url': self.url, 'json_format': self.json_format,
                'extra_body': self.extra_body}


def service_from(config, *, fallback=None):
    if config is None:
        if fallback is None:
            raise ValueError('missing model service configuration')
        return fallback
    unknown = set(config)-{'model', 'url', 'api_key', 'api_key_env', 'json_format', 'extra_body'}
    if unknown:
        raise ValueError('unknown service configuration keys: '+', '.join(sorted(unknown)))
    key = config.get('api_key') or os.environ.get(config.get('api_key_env', 'VIDEO_TEACHER_API_KEY'))
    if not key and fallback:
        # Reuse a key only for the same endpoint. Never send it to a new host.
        candidate = chat_url(config.get('url', fallback.url))
        if candidate == fallback.url:
            key = fallback.api_key
    model = config.get('model', fallback.model if fallback else '')
    default_json = (fallback.json_format if fallback and model == fallback.model
                    else not (model.lower().startswith('qwen') and 'omni' in model.lower()))
    return Service(model,
                   config.get('url', fallback.url if fallback else ''), key or '',
                   config.get('json_format', default_json), config.get('extra_body', {}))


class ServicePool:
    """One semaphore and persistent ledger cover generation, judges, and audio."""
    def __init__(self, out, *, concurrency=8, max_calls=1000, max_tokens=15_000_000):
        self.out = out
        self.sem = threading.BoundedSemaphore(concurrency)
        self.concurrency, self.max_calls, self.max_tokens = concurrency, max_calls, max_tokens
        self.clients = []

    def client(self, service):
        client = MatrixClient(self.out, model=service.model, endpoint=service.url,
                              api_key=service.api_key, concurrency=self.concurrency,
                              semaphore=self.sem, max_calls=self.max_calls,
                              max_tokens_total=self.max_tokens,
                              json_format=service.json_format, extra_body=service.extra_body)
        self.clients.append(client)
        return client

    def close(self):
        for client in self.clients:
            client.http.close()


class JudgeClient:
    def __init__(self, visual, audio):
        self.visual, self.audio = visual, audio
        self.model = visual.model
        self.audio_model = audio.model if audio else None

    def chat(self, messages, **kwargs):
        has_audio = any(isinstance(m.get('content'), list) and
                        any(p.get('type') == 'input_audio' for p in m['content']) for m in messages)
        if has_audio:
            if self.audio is None:
                raise ValueError('No audio-capable judge configured; set audio_judge model/url/API key')
            kwargs.pop('model', None)
            return self.audio.chat(messages, **kwargs)
        return self.visual.chat(messages, **kwargs)
