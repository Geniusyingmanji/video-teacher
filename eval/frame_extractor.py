"""Frame extraction for video evaluation.

Extracts N evenly-spaced frames from an MP4 and returns them as PIL.Image
list. Used by every dimension judge.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

import imageio.v3 as iio
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
    video_path = str(video_path)
    arr = iio.imread(video_path, plugin="pyav")
    # arr shape: (T, H, W, C)
    T = arr.shape[0]
    if T == 0:
        raise RuntimeError(f"empty video: {video_path}")

    if n >= T:
        idx = list(range(T))
    else:
        # evenly spaced: include first and last
        idx = np.linspace(0, T - 1, num=n).round().astype(int).tolist()

    frames: list[Image.Image] = []
    for i in idx:
        f = arr[i]
        img = Image.fromarray(f)
        if resize_max > 0 and max(img.size) > resize_max:
            scale = resize_max / max(img.size)
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.LANCZOS)
        frames.append(img)
    return frames


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
