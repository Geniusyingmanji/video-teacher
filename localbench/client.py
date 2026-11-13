"""OpenAI-compatible transport, bounded concurrency, persistent call/token caps.

Credentials are loaded from environment or a private file outside the checkout.
No automatic upgrades to more expensive models, and no secret-bearing logs.
"""
from __future__ import annotations

import fcntl
import json
import os
import threading
import time
from pathlib import Path

import httpx

from .common import digest, parse_json, write_json


class BudgetExceeded(RuntimeError):
    pass


class MatrixClient:
    def __init__(self, run_dir, model='qwen3.5-flash', concurrency=4,
                 max_calls=80, max_tokens_total=350_000, cache_sources=(),
                 endpoint=None, api_key=None, timeout=100, semaphore=None,
                 json_format=True, extra_body=None):
        explicit_endpoint = endpoint is not None
        credential_file = Path(os.environ.get('VIDEO_TEACHER_CREDENTIALS',
                                  str(Path.home() / '.config/video-teacher/matrix.json')))
        credential = (json.loads(credential_file.read_text())
                      if (api_key is None or endpoint is None) and credential_file.exists() else {})
        self.key = api_key if api_key is not None else os.environ.get('MATRIX_API_KEY') or credential.get('api_key')
        self.endpoint = endpoint or os.environ.get('MATRIX_CHAT_URL') or credential.get('endpoint')
        if not self.key or not self.endpoint:
            raise ValueError('Set MATRIX_API_KEY and MATRIX_CHAT_URL, or private credential file')
        self.model = model
        self.cache_namespace = self.endpoint if explicit_endpoint else None
        self.json_format = json_format
        self.extra_body = extra_body or {}
        if set(self.extra_body) & {'model', 'messages', 'stream', 'max_tokens'}:
            raise ValueError('extra_body cannot override model/messages/stream/max_tokens')
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cache = self.run_dir / 'api_cache'
        self.cache.mkdir(exist_ok=True)
        self.ledger = self.run_dir / 'usage.jsonl'
        self.sem = semaphore or threading.BoundedSemaphore(concurrency)
        self._locks_guard=threading.Lock()
        self._cache_locks={}
        self.max_calls, self.max_tokens_total = max_calls, max_tokens_total
        self.cache_sources=[Path(p) for p in cache_sources]
        if any(not (p/'api_cache').is_dir() for p in self.cache_sources):
            raise ValueError('cache source must be an existing run with api_cache')
        self.http = httpx.Client(timeout=httpx.Timeout(timeout, connect=20))

    def _record(self, row, reserve=False):
        with self.ledger.open('a+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            rows = [json.loads(x) for x in f if x.strip()]
            starts = {x['request_id']: x for x in rows if x['event'] == 'start'}
            ends = {x['request_id']: x for x in rows if x['event'] == 'end'}
            consumed = sum(ends.get(k, {}).get('charged_tokens', v['reservation'])
                           for k, v in starts.items())
            if reserve and (len(starts) >= self.max_calls or
                            consumed + row['reservation'] > self.max_tokens_total):
                raise BudgetExceeded(f'run budget reached: {len(starts)} calls, {consumed} tokens/reserved')
            f.seek(0, 2)
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            f.flush()
            fcntl.flock(f, fcntl.LOCK_UN)

    def chat(self, messages, *, purpose, max_tokens=3000, model=None, json_mode=True):
        model = model or self.model
        body = {'model': model, 'messages': messages, 'max_tokens': max_tokens,
                'temperature': 0.2, 'stream': False}
        if json_mode and self.json_format:
            body['response_format'] = {'type': 'json_object'}
        if model.startswith('qwen'):
            body['enable_thinking'] = False
        body.update(self.extra_body)
        key = digest({'endpoint': self.cache_namespace, 'request': body}) if self.cache_namespace else digest(body)
        cache_path = self.cache / (key + '.json')
        if cache_path.exists():
            raw = json.loads(cache_path.read_text())
            self._record({'event':'cache_reuse','cache_kind':'local','request_hash':key,'model':model,
                          'source':str(self.run_dir.resolve()),'purpose':purpose,'time':time.time()})
            return parse_json(raw['content']) if json_mode else raw['content']
        # Binary media receives a conservative reservation independent of base64 length.
        text_chars = 0
        media = 0
        for message in messages:
            content = message['content']
            if isinstance(content, str):
                text_chars += len(content)
            else:
                for part in content:
                    if part['type'] == 'text':
                        text_chars += len(part['text'])
                    else:
                        media += 1
        reservation = max_tokens + text_chars // 2 + media * 1800
        with self._locks_guard:
            cache_lock=self._cache_locks.setdefault(key,threading.Lock())
        with cache_lock, self.sem:
            if cache_path.exists():
                raw=json.loads(cache_path.read_text())
                self._record({'event':'cache_reuse','cache_kind':'local','request_hash':key,'model':model,
                              'source':str(self.run_dir.resolve()),'purpose':purpose,'time':time.time()})
                return parse_json(raw['content']) if json_mode else raw['content']
            for source in self.cache_sources:
                candidate=source/'api_cache'/cache_path.name
                if not candidate.is_file():continue
                raw=json.loads(candidate.read_text())
                if raw.get('request_hash')!=key or raw.get('model')!=model:
                    raise ValueError('external cache request/model mismatch')
                parsed=parse_json(raw['content']) if json_mode else raw['content']
                write_json(cache_path,raw)
                self._record({'event':'cache_reuse','cache_kind':'external','request_hash':key,'model':model,
                              'source':str(source.resolve()),'purpose':purpose,'time':time.time()})
                return parsed
            for attempt in range(4):
                request_id = f'{key[:12]}-{time.time_ns()}'
                self._record({'event': 'start', 'request_id': request_id,
                              'model': model, 'purpose': purpose, 'reservation': reservation,
                              'time': time.time()}, reserve=True)
                started = time.monotonic()
                usage, payload, response = {}, None, None
                try:
                    response = self.http.post(self.endpoint, headers={'Authorization': 'Bearer ' + self.key}, json=body)
                    if response.status_code != 200:
                        raise RuntimeError(f'provider HTTP {response.status_code}')
                    payload = response.json()
                    usage = payload.get('usage') or {}
                    choice = payload['choices'][0]
                    content = choice['message'].get('content')
                    usage = payload.get('usage') or {}
                    if not isinstance(content, str) or not content.strip():
                        raise ValueError('provider returned empty/non-text content')
                    if choice.get('finish_reason') == 'length':
                        raise ValueError('provider truncated completion')
                    parsed = parse_json(content) if json_mode else content
                    self._record({'event': 'end', 'request_id': request_id,
                                  'status': 'ok', 'charged_tokens': usage.get('total_tokens', reservation),
                                  'usage': usage, 'seconds': round(time.monotonic() - started, 3)})
                    raw = {'content': content, 'usage': usage, 'model': model,
                           'returned_model': payload.get('model'), 'purpose': purpose,
                           'request_hash': key, 'finish_reason': choice.get('finish_reason')}
                    write_json(cache_path, raw)
                    return parsed
                except Exception as exc:
                    if payload is not None:
                        # Preserve provider-reported usage even when its text fails our parser.
                        # No headers, credentials, or request media are saved here.
                        write_json(self.run_dir/'invalid_responses'/(request_id+'.json'),
                                   {'model': model, 'purpose': purpose, 'usage': usage,
                                    'choices': payload.get('choices', []),
                                    'error_type': type(exc).__name__})
                    self._record({'event': 'end', 'request_id': request_id,
                                  'status': 'error', 'error_type': type(exc).__name__,
                                  'http_status':response.status_code if response is not None else None,
                                  'charged_tokens': usage.get('total_tokens', reservation), 'usage': usage,
                                  'seconds': round(time.monotonic() - started, 3)})
                    # Do not retry input errors or truncated/invalid responses automatically.
                    retryable = isinstance(exc, httpx.TransportError) or str(exc) in {
                        'provider HTTP 429', 'provider HTTP 500', 'provider HTTP 502', 'provider HTTP 503'}
                    rate_limited=response is not None and response.status_code==429
                    if not retryable or attempt >= (3 if rate_limited else 1):
                        raise
                    delay=retry_delay(response,attempt) if rate_limited else 1
                    self._record({'event':'retry_wait','request_id':request_id,'seconds':delay,
                                  'reason':'rate_limit' if rate_limited else 'transient_transport','time':time.time()})
                    # Bound each individual wait while respecting a longer Retry-After.
                    remaining=delay
                    while remaining>0:
                        interval=min(60,remaining);time.sleep(interval);remaining-=interval


def retry_delay(response,attempt):
    """Honor standard Retry-After; back off 20/40/60 seconds when absent/invalid."""
    from datetime import datetime,timezone
    from email.utils import parsedate_to_datetime
    raw=response.headers.get('Retry-After','')
    try:seconds=float(raw)
    except ValueError:
        try:seconds=(parsedate_to_datetime(raw)-datetime.now(timezone.utc)).total_seconds()
        except (ValueError,TypeError,OverflowError):seconds=0
    if seconds>0:return min(seconds,300)
    return min(60,20*(attempt+1))
