"""Save frames sampled at a temporal rate as JPGs for human inspection.

Useful for spot-checking what the model actually produced after a generation run.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Allow running this as `python scripts/save_sample_frames.py` from project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.frame_extractor import extract_frames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-fps", type=float, default=2.0)
    ap.add_argument("--frame-max-px", type=int, default=512)
    args = ap.parse_args()
    if not math.isfinite(args.sample_fps) or args.sample_fps <= 0:
        ap.error("sample FPS must be positive and finite")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with open(args.manifest) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    for r in rows:
        if r.get("status") != "ok":
            continue
        cid = r["id"]
        try:
            frames = extract_frames(r["video_path"], sample_fps=args.sample_fps,
                                    resize_max=args.frame_max_px)
        except Exception as e:
            print(f"[skip] {cid}: {e}")
            continue
        case_dir = out_dir / cid
        case_dir.mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(frames):
            img.save(case_dir / f"frame_{i+1}.jpg", quality=85)
        print(f"[ok] {cid}: {len(frames)} frames")


if __name__ == "__main__":
    main()
