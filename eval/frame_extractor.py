"""Frame extraction for video evaluation.

Extracts N evenly-spaced frames from an MP4 and returns them as PIL.Image
list. Used by every dimension judge.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image


def extract_frames(
    video_path: str | Path,
    n: int = 8,
    resize_max: int = 512,
) -> list[Image.Image]:
    """Sample N evenly-spaced frames from video_path. Returns PIL.Images.

    resize_max: if > 0, resize longest side to this many pixels (saves judge tokens).
    """
    if n <= 0:
        raise ValueError("n must be positive")
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open video: {video_path}")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            raise RuntimeError(f"empty video: {video_path}")
        idx = (list(range(total)) if n >= total else
               np.linspace(0, total - 1, num=n).round().astype(int).tolist())
        frames: list[Image.Image] = []
        for i in idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"cannot decode frame {i}: {video_path}")
            img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            if resize_max > 0 and max(img.size) > resize_max:
                scale = resize_max / max(img.size)
                new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            frames.append(img)
        return frames
    finally:
        cap.release()


def frame_to_data_url(img: Image.Image, fmt: str = "JPEG", quality: int = 80) -> str:
    buf = BytesIO()
    if fmt.upper() == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buf, format=fmt, quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode()
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"


def frames_as_multimodal_content(
    frames: list[Image.Image],
    text: str,
) -> list[dict]:
    """Build the OpenAI-style content list for a vision message."""
    content: list[dict] = [{"type": "text", "text": text}]
    for img in frames:
        content.append({"type": "image_url", "image_url": {"url": frame_to_data_url(img)}})
    return content


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    frames = extract_frames(p, n=8)
    print(f"extracted {len(frames)} frames, sizes={[f.size for f in frames]}")
