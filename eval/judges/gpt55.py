"""Thin key-less Azure OpenAI client for GPT-5.5 / GPT-5.4.

Auth pattern mirrors IdeaEvolving/agent/llm_client.py: shell out to
`az account get-access-token` and cache the bearer token until ~5 minutes
before expiry. No SDK install or API key needed.

Usage:
    from eval.judges.gpt55 import chat
    reply = chat([{"role": "user", "content": "ping"}])
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from openai import AzureOpenAI, OpenAI


AZURE_DEFAULT_SCOPE = "https://cognitiveservices.azure.com/.default"

_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: dict[str, dict[str, Any]] = {}


def _decode_token_expiry(token: str) -> int:
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        return int(data.get("exp", 0))
    except Exception:
        return 0


def _get_azure_cli_token(resource: str) -> str:
    with _TOKEN_LOCK:
        now = int(time.time())
        cached = _TOKEN_CACHE.setdefault(resource, {"token": "", "expires_on": 0})
        token = str(cached.get("token") or "")
        expires_on = int(cached.get("expires_on") or 0)
        if token and expires_on - now > 300:
            return token

        env = os.environ.copy()
        try:
            raw = subprocess.check_output(
                [
                    "az",
                    "account",
                    "get-access-token",
                    "--resource",
                    resource,
                    "-o",
                    "json",
                ],
                text=True,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"az get-access-token failed: {exc.output.strip() if exc.output else exc}"
            ) from exc
        data = json.loads(raw)
        new_token = data.get("accessToken") or ""
        if not new_token:
            raise RuntimeError("az returned empty access token")
        new_expires = int(data.get("expires_on") or _decode_token_expiry(new_token) or now + 3000)
        cached["token"] = new_token
        cached["expires_on"] = new_expires
        return new_token


def make_token_provider(scope: str = AZURE_DEFAULT_SCOPE):
    resource = scope[:-len("/.default")] if scope.endswith("/.default") else scope

    def _provider() -> str:
        return _get_azure_cli_token(resource)

    return _provider


def make_client(
    endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    scope: str = AZURE_DEFAULT_SCOPE,
    timeout: float = 300.0,
) -> AzureOpenAI:
    endpoint = endpoint or os.environ.get(
        "AZURE_OPENAI_ENDPOINT", "https://t2vgoaigpt4o3.openai.azure.com/"
    )
    api_version = api_version or os.environ.get(
        "AZURE_OPENAI_API_VERSION", "2025-01-01-preview"
    )
    http_client = httpx.Client(trust_env=False, timeout=httpx.Timeout(timeout))
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        azure_ad_token_provider=make_token_provider(scope),
        max_retries=3,
        http_client=http_client,
    )


def judge_config() -> dict[str, str]:
    """Public, secret-free identity of the configured vision judge."""
    if os.environ.get("VIDEO_TEACHER_API_KEY"):
        base_url = os.environ.get("VIDEO_TEACHER_BASE_URL", "").strip()
        model = os.environ.get("VIDEO_TEACHER_MODEL", "").strip()
        if not base_url or not model:
            raise ValueError("VIDEO_TEACHER_BASE_URL and VIDEO_TEACHER_MODEL are required with VIDEO_TEACHER_API_KEY")
        return {"provider": "openai_compatible", "base_url": base_url.rstrip("/"), "model": model}
    return {"provider": "azure_cli", "endpoint": os.environ.get(
        "AZURE_OPENAI_ENDPOINT", "https://t2vgoaigpt4o3.openai.azure.com/").rstrip("/"),
        "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        "model": os.environ.get("VIDEO_TEACHER_MODEL", "gpt-5.5")}


def configured_client():
    config = judge_config()
    if config["provider"] == "openai_compatible":
        return OpenAI(api_key=os.environ["VIDEO_TEACHER_API_KEY"],
                      base_url=config["base_url"], timeout=300.0, max_retries=3)
    return make_client()


def chat(
    messages: list[dict[str, Any]],
    model: str = "gpt-5.5",
    *,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    response_format: Optional[dict[str, str]] = None,
    client: Optional[AzureOpenAI] = None,
    max_retries: int = 6,
    **kwargs: Any,
) -> str:
    import random
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
    client = client or configured_client()
    model = os.environ.get("VIDEO_TEACHER_MODEL", model)
    extra: dict[str, Any] = {}
    if response_format is not None:
        extra["response_format"] = response_format
    extra.update(kwargs)
    if judge_config()["provider"] == "openai_compatible":
        extra.setdefault("temperature", temperature)
    if os.environ.get("VIDEO_TEACHER_ENABLE_THINKING") == "false":
        body = extra.setdefault("extra_body", {})
        body.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
    delay = 10.0
    for attempt in range(max_retries):
        try:
            # gpt-5.5 reasoning models often use max_completion_tokens instead.
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_tokens,
                **extra,
            )
            if getattr(completion.choices[0], 'finish_reason', None) == 'length':
                raise ValueError('Judge output truncated; no score accepted')
            return completion.choices[0].message.content or ""
        except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError):
            if attempt == max_retries - 1:
                raise
            jitter = random.uniform(0.8, 1.2)
            wait = delay * jitter
            print(f"[gpt55] 429 rate limit on attempt {attempt+1}, sleeping {wait:.1f}s ...")
            time.sleep(wait)
            delay = min(delay * 2, 120.0)
    return ""


if __name__ == "__main__":
    print("[smoke test] GPT-5.5 keyless ping ...")
    reply = chat([{"role": "user", "content": "Say 'ok' and nothing else."}], max_tokens=128)
    print("Reply:", repr(reply))
    assert reply.strip().lower().startswith("ok"), f"unexpected reply: {reply!r}"
    print("[smoke test] OK")
