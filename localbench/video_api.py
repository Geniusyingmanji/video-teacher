"""Explicit asynchronous video protocols, durable task receipts, and bounded polling.

Protocol fixtures verify recovery; a configured service still needs a live smoke test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse, quote

import httpx

from .common import digest, write_json
from .provenance import file_hash


@dataclass
class VideoService:
    model: str
    url: str
    query_url: str
    api_key: str = field(repr=False)
    protocol: str = 'ark'
    max_shot_seconds: int = 10
    resolution: str = '480p'
    parameters: dict = field(default_factory=dict)
    poll_seconds: float = 5
    timeout_seconds: float = 600

    def __post_init__(self):
        if self.protocol not in {'ark', 'wan', 'wan3'}:
            raise ValueError('video protocol must be ark, wan, or wan3')
        if not self.model or not self.api_key or '{task_id}' not in self.query_url:
            raise ValueError('video model/key and query_url with {task_id} are required')
        for url in (self.url, self.query_url):
            parsed = urlparse(url)
            if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('video submit/query URLs must be explicit HTTPS URLs without credentials')
        if urlparse(self.url).netloc != urlparse(self.query_url).netloc:
            raise ValueError('video submit/query must share the credential host')
        if type(self.max_shot_seconds) is not int or not 4 <= self.max_shot_seconds <= 30:
            raise ValueError('max_shot_seconds must be an integer 4..30 supported by the model')
        if not 1 <= self.poll_seconds <= 30 or not 1 <= self.timeout_seconds <= 1800:
            raise ValueError('video polling interval 1..30s and timeout 1..1800s required')
        if set(self.parameters) & {'duration', 'model', 'input', 'content', 'resolution', 'size', 'ratio'}:
            raise ValueError('video parameters cannot override task identity, media, duration, or resolution')

    def public(self):
        return {k: v for k, v in vars(self).items() if k != 'api_key'}

    def request(self, prompt, duration, image_url=None):
        if not 2 <= duration <= self.max_shot_seconds:
            raise ValueError('shot duration outside configured model bounds')
        if self.protocol == 'ark':
            content = [{'type': 'text', 'text': prompt}]
            if image_url:
                content.append({'type': 'image_url', 'image_url': {'url': image_url}, 'role': 'first_frame'})
            return {'model': self.model, 'content': content, 'duration': duration,
                    'resolution': self.resolution, 'ratio': '16:9', **self.parameters}
        inputs = {'prompt': prompt}
        parameters = {'duration': duration, **self.parameters}
        if self.protocol == 'wan3':
            parameters.update(resolution=self.resolution, ratio='16:9')
            if image_url:
                inputs['media'] = [{'type': 'first_frame', 'url': image_url}]
        else:
            if image_url:
                raise ValueError('legacy wan text-to-video does not accept source images; configure an image-capable protocol')
            parameters['size'] = {'480p': '832*480', '720p': '1280*720', '1080p': '1920*1080'}[self.resolution]
        return {'model': self.model, 'input': inputs, 'parameters': parameters}


def video_service_from(config):
    values = dict(config or {})
    values['api_key'] = values.get('api_key') or os.environ.get(values.pop('api_key_env', 'VIDEO_TEACHER_VIDEO_API_KEY'), '')
    try:
        return VideoService(**values)
    except TypeError as exc:
        raise ValueError('video configuration requires model, full submit url, query_url, and protocol') from exc


class VideoAPI:
    def __init__(self, service, ledger_client, *, max_seconds=120):
        if not math.isfinite(max_seconds) or max_seconds <= 0:
            raise ValueError('positive native-video seconds budget required')
        self.service, self.ledger = service, ledger_client
        self.max_seconds = max_seconds
        self.lock = threading.Lock()
        self.http = httpx.Client(timeout=httpx.Timeout(60, connect=20))

    def close(self):
        self.http.close()

    def _reserve(self, body, receipt, path):
        with self.lock:
            records = [json.loads(l) for l in self.ledger.ledger.read_text().splitlines()] if self.ledger.ledger.exists() else []
            used = sum(r.get('video_seconds', 0) for r in records if r['event'] == 'start')
            seconds = body.get('duration', body.get('parameters', {}).get('duration'))
            if used + seconds > self.max_seconds:
                raise ValueError(f'native video duration budget reached: {used}/{self.max_seconds}s')
            rid = 'video-'+digest(body)[:12]+'-'+str(time.time_ns())
            self.ledger._record({'event': 'start', 'request_id': rid, 'model': self.service.model,
                'purpose': 'native_video_submit', 'reservation': 0, 'video_seconds': seconds,
                'time': time.time()}, reserve=True)
            receipt.update(request_id=rid, state='submitting')
            write_json(path, receipt)  # Crash/timeout after this point must not create a duplicate paid task.

    def generate(self, prompt, duration, directory, image_url=None):
        directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
        path = directory/'task.json'; output = directory/'clip.mp4'
        body = self.service.request(prompt, duration, image_url)
        identity = digest({'service': self.service.public(), 'body': body})
        receipt = json.loads(path.read_text()) if path.exists() else {'request_hash': identity, 'state': 'new'}
        if receipt['request_hash'] != identity:
            raise ValueError('native task inputs changed; use a new directory')
        if receipt.get('state') == 'downloaded':
            if not output.exists() or file_hash(output) != receipt['sha256']:
                raise ValueError('downloaded clip changed or disappeared')
            return output
        if receipt.get('state') in {'submitting', 'submission_unknown'}:
            raise RuntimeError('submission outcome unknown; recover task ID from provider before resuming, no automatic resubmit')
        if receipt.get('state') == 'failed':
            raise RuntimeError('provider task failed; inspect saved receipt, no automatic paid resubmit')
        headers = {'Authorization': 'Bearer '+self.service.api_key}
        if self.service.protocol != 'ark': headers['X-DashScope-Async'] = 'enable'
        if receipt['state'] == 'new':
            with self.ledger.sem:
                self._reserve(body, receipt, path)
                try:
                    response = self.http.post(self.service.url, headers=headers, json=body)
                    response.raise_for_status()
                    raw = response.json()
                    task_id = raw.get('id') if self.service.protocol == 'ark' else raw.get('output', {}).get('task_id')
                    if not isinstance(task_id, str) or not task_id:
                        raise ValueError('video submission returned no task ID')
                    receipt.update(state='pending', task_id=task_id)
                    write_json(path, receipt)
                except Exception as exc:
                    receipt.update(state='submission_unknown', error_type=type(exc).__name__)
                    write_json(path, receipt)
                    self._finish_usage(receipt, status='error')
                    raise RuntimeError('video submission failed or outcome unknown; see task receipt') from exc
        deadline = time.monotonic()+self.service.timeout_seconds
        while True:
            query = self.service.query_url.replace('{task_id}', quote(receipt['task_id'], safe=''))
            with self.ledger.sem:
                response = self.http.get(query, headers=headers)
                response.raise_for_status()
                raw = response.json()
            info = raw if self.service.protocol == 'ark' else raw.get('output', {})
            status = info.get('status', info.get('task_status', '')).lower()
            receipt['provider_status'] = status
            write_json(path, receipt)
            if status in {'succeeded', 'success'}:
                url = info.get('content', {}).get('video_url') or info.get('video_url')
                if not isinstance(url, str) or urlparse(url).scheme != 'https':
                    raise ValueError('completed video task has no HTTPS media URL')
                usage = raw.get('usage') or {}
                self._finish_usage(receipt, status='ok', usage=usage)
                # CDN downloads never carry provider Authorization headers.
                temp = output.with_suffix('.part')
                with self.http.stream('GET', url, follow_redirects=True) as stream:
                    stream.raise_for_status()
                    size = 0
                    with temp.open('wb') as f:
                        for chunk in stream.iter_bytes():
                            size += len(chunk)
                            if size > 512*1024*1024: raise ValueError('video download exceeds 512 MB limit')
                            f.write(chunk)
                temp.replace(output)
                receipt.update(state='downloaded', sha256=file_hash(output), bytes=size)
                write_json(path, receipt)
                return output
            if status in {'failed', 'canceled', 'cancelled', 'expired', 'unknown'}:
                receipt.update(state='failed', error_code=(info.get('error') or {}).get('code'))
                write_json(path, receipt)
                self._finish_usage(receipt, status='error', usage=raw.get('usage'))
                raise RuntimeError('native video task '+status)
            if status not in {'pending', 'running', 'queued', 'processing'}:
                raise ValueError('unrecognized video task status: '+status)
            if time.monotonic() >= deadline:
                raise TimeoutError('video task still pending; resume reuses its task ID')
            time.sleep(min(self.service.poll_seconds, max(0, deadline-time.monotonic())))

    def _finish_usage(self, receipt, *, status, usage=None):
        # Same request ID makes repeat queries idempotent in the accounting summary.
        self.ledger._record({'event': 'end', 'request_id': receipt['request_id'],
            'status': status, 'usage': usage or {}, 'charged_tokens': (usage or {}).get('total_tokens', 0)})
