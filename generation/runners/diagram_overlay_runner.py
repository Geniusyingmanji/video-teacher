"""Render reviewed diagram highlights without redrawing labels or equations.

This is a separate deterministic baseline for text-heavy teaching diagrams,
not a replacement for Wan output in model comparisons.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def render_frames(image: Image.Image, boxes: list[list[float]], count: int,
                  size: tuple[int, int]) -> np.ndarray:
    if not boxes or count < 2:
        raise ValueError("at least one box and two frames are required")
    base = ImageOps.pad(image.convert("RGB"), size, method=Image.Resampling.LANCZOS,
                        color=(245, 245, 245), centering=(0.5, 0.5))
    width, height = size
    frames = []
    for frame_no in range(count):
        frame = base.copy()
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        pen = ImageDraw.Draw(overlay)
        phase = min(len(boxes) - 1, frame_no * len(boxes) // count)
        local = (frame_no * len(boxes) / count) % 1
        opacity = round(220 * min(1.0, local * 5, (1 - local) * 5 + 0.25))
        for index, box in enumerate(boxes[:phase + 1]):
            if len(box) != 4 or any(not isinstance(v, (int, float)) for v in box):
                raise ValueError("boxes must contain four numeric coordinates")
            x0, y0, x1, y1 = box
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError("box must be normalized and nonempty")
            color = (10, 118, 220, opacity if index == phase else 80)
            rect = (round(x0 * width), round(y0 * height),
                    round(x1 * width), round(y1 * height))
            pen.rounded_rectangle(rect, radius=10, outline=color, width=5)
        frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
        frames.append(np.asarray(frame))
    return np.stack(frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs", type=Path, required=True)
    parser.add_argument("--first-frames", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--num-frames", type=int, default=73)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    specs = [json.loads(line) for line in args.specs.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    with (args.out / "manifest.jsonl").open("w", encoding="utf-8") as manifest:
        for spec in specs:
            case_id = spec["id"]
            frame = Image.open(args.first_frames / f"{case_id}.png")
            frames = render_frames(frame, spec["boxes"], args.num_frames, (832, 480))
            target = args.out / f"{case_id}.mp4"
            iio.imwrite(target, frames, fps=args.fps, codec="libx264",
                       macro_block_size=1)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest.write(json.dumps({"id": case_id, "video_path": str(target),
                                       "video_sha256": digest, "status": "ok",
                                       "render_method": "reviewed_diagram_overlay",
                                       "spec_version": spec.get("version", "v1")}) + "\n")


if __name__ == "__main__":
    main()
