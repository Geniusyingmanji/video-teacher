"""Probe what image generation deployments Azure has available.

Tries the same Azure endpoints used by gpt55.py (keyless auth via Azure CLI
token) and attempts a minimal images.generate() call against likely deployment
names. Saves the first successful image to /tmp.
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.judges.gpt55 import make_client


CANDIDATES = [
    ("https://t2vgoaigpt4o3.openai.azure.com/", "gpt-image-1"),
    ("https://t2vgoaigpt4o3.openai.azure.com/", "dall-e-3"),
    ("https://t2vgoaigpt4o3.openai.azure.com/", "dalle3"),
    ("https://t2vgoaigpt4o.openai.azure.com/", "gpt-image-1"),
    ("https://t2vgoaigpt4o.openai.azure.com/", "dall-e-3"),
]


def try_one(endpoint: str, deployment: str) -> tuple[bool, str]:
    try:
        client = make_client(endpoint=endpoint, api_version="2025-01-01-preview")
        resp = client.images.generate(
            model=deployment,
            prompt="A simple chalkboard with the equation 2x+5=17 written clearly in white chalk. "
                   "Clean educational opening frame, sharp text, high resolution.",
            size="1024x1024",
            n=1,
        )
        # Try to get b64 or url
        data = resp.data[0]
        if getattr(data, "b64_json", None):
            blob = base64.b64decode(data.b64_json)
            out = Path(f"/tmp/azure_test_{deployment}.png")
            out.write_bytes(blob)
            return True, f"b64 -> {out} ({len(blob)} bytes)"
        if getattr(data, "url", None):
            return True, f"url -> {data.url[:80]}..."
        return True, f"unknown response: {data}"
    except Exception as e:
        msg = str(e)[:300].replace("\n", " ")
        return False, msg


def main() -> None:
    for endpoint, dep in CANDIDATES:
        print(f"[probe] endpoint={endpoint} deployment={dep}")
        ok, info = try_one(endpoint, dep)
        marker = "OK" if ok else "FAIL"
        print(f"  -> {marker}: {info}")
        if ok:
            print(f"\n[probe] SUCCESS — endpoint={endpoint} deployment={dep}")
            return
    print("\n[probe] no working deployment found")


if __name__ == "__main__":
    main()
