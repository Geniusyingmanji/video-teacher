"""Frame extraction for video evaluation.

Samples an MP4 at a fixed temporal rate and returns PIL images.
"""

from __future__ import annotations

import base64
from io import BytesIO
import math
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image


def sample_frame_indices(total: int, source_fps: float, sample_fps: float = 2.0) -> list[int]:
    """Return distinct source indices at 0, 1/sample_fps, ... through the last frame."""
    if total <= 0 or not math.isfinite(source_fps) or source_fps <= 0:
        raise ValueError("video must have frames and a valid source FPS")
    if not math.isfinite(sample_fps) or sample_fps <= 0:
        raise ValueError("sample_fps must be positive and finite")
    last_sample = math.floor((total - 1) * sample_fps / source_fps)
    return sorted({round(k * source_fps / sample_fps) for k in range(last_sample + 1)})


def extract_frames(
    video_path: str | Path,
    n: int | None = None,
    resize_max: int = 512,
    sample_fps: float = 2.0,
) -> list[Image.Image]:
    """Sample at 2 FPS by default. Explicit n retains legacy count sampling.

    resize_max: if > 0, resize longest side to this many pixels (saves judge tokens).
    """
    if n is not None and n <= 0:
        raise ValueError("n must be positive")
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open video: {video_path}")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            raise RuntimeError(f"empty video: {video_path}")
        if n is None:
            idx = sample_frame_indices(total, cap.get(cv2.CAP_PROP_FPS), sample_fps)
        else:
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
    frames = extract_frames(p, sample_fps=2)
    print(f"extracted {len(frames)} frames, sizes={[f.size for f in frames]}")
