"""Wan2.2-TI2V runner: Text-Image-to-Video generation with first-frame input.

Unlike wan_runner.py (text-only T2V), this runner loads WanImageToVideoPipeline
and feeds both the text prompt and a first-frame image for each case.

Usage:
    CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_ti2v_runner \
        --prompts data/prompts/pilot_v0_1.jsonl \
        --first-frames data/first_frames \
        --out /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/pilot_v0_1 \
        --num-frames 49 --height 480 --width 832 --steps 30
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
from PIL import Image


def load_pipe(model_path: str, dtype: torch.dtype, device: str):
    """Load Wan2.2-TI2V as an image-to-video pipeline."""
    from diffusers import WanImageToVideoPipeline

    print(f"[wan-ti2v] loading pipeline from {model_path} ...")
    pipe = WanImageToVideoPipeline.from_pretrained(model_path, torch_dtype=dtype)
    pipe.to(device)
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    if hasattr(pipe, "enable_vae_tiling"):
        try:
            pipe.enable_vae_tiling()
        except Exception:
            pass
    print(f"[wan-ti2v] loaded. pipeline class: {type(pipe).__name__}")
    return pipe


def save_video_mp4(frames, path: str, fps: int = 16) -> None:
    import numpy as np
    import imageio.v3 as iio

    if isinstance(frames, list):
        arr = np.stack([np.asarray(f) for f in frames], axis=0)
    else:
        arr = np.asarray(frames)
    if arr.dtype != np.uint8:
        arr = (arr * 255).clip(0, 255).astype(np.uint8)
    iio.imwrite(path, arr, fps=fps, codec="libx264", macro_block_size=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--first-frames", required=True,
                    help="Directory containing <case_id>.png first-frame images")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-path",
                    default="/data/zyf/rise-teacher/models/Wan2.2-TI2V-5B-Diffusers")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--num-frames", type=int, default=49)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance-scale", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dtype", default="bfloat16",
                    choices=["bfloat16", "float16", "float32"])
    args = ap.parse_args()

    dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
    dtype = dtype_map[args.dtype]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"
    ff_dir = Path(args.first_frames)

    # Load prompts
    cases: list[dict] = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.limit > 0:
        cases = cases[:args.limit]

    # Filter to cases that have first-frame images
    valid_cases = []
    for c in cases:
        ff_path = ff_dir / f"{c['id']}.png"
        if ff_path.exists():
            valid_cases.append(c)
        else:
            print(f"[wan-ti2v] WARNING: no first-frame for {c['id']}, skipping")
    print(f"[wan-ti2v] {len(valid_cases)}/{len(cases)} cases have first-frame images")

    pipe = load_pipe(args.model_path, dtype, device)

    # Resume support
    done_ids = set()
    if manifest_path.exists():
        with manifest_path.open() as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    print(f"[wan-ti2v] resume: {len(done_ids)} already generated")

    started_at = time.time()
    with manifest_path.open("a") as mf:
        for i, case in enumerate(valid_cases):
            cid = case["id"]
            if cid in done_ids:
                continue

            ff_path = ff_dir / f"{cid}.png"
            first_frame = Image.open(ff_path).convert("RGB")
            first_frame = first_frame.resize((args.width, args.height), Image.LANCZOS)

            out_mp4 = out_dir / f"{cid}.mp4"
            t0 = time.time()
            gen = torch.Generator(device=device).manual_seed(args.seed)

            try:
                result = pipe(
                    image=first_frame,
                    prompt=case["prompt_text"],
                    height=args.height,
                    width=args.width,
                    num_frames=args.num_frames,
                    num_inference_steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    generator=gen,
                )
                frames = result.frames[0] if hasattr(result, "frames") else result[0]
                save_video_mp4(frames, str(out_mp4), fps=args.fps)
                elapsed = time.time() - t0

                mf.write(json.dumps({
                    "id": cid,
                    "prompt_text": case["prompt_text"][:200],
                    "discipline": case.get("discipline"),
                    "task_type": case.get("task_type"),
                    "difficulty": case.get("difficulty"),
                    "video_path": str(out_mp4),
                    "first_frame_path": str(ff_path),
                    "height": args.height, "width": args.width,
                    "num_frames": args.num_frames, "steps": args.steps,
                    "guidance_scale": args.guidance_scale, "seed": args.seed,
                    "fps": args.fps, "dtype": args.dtype,
                    "elapsed_s": round(elapsed, 2),
                    "status": "ok",
                }) + "\n")
                mf.flush()

                wall = (time.time() - started_at) / 60.0
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: ok in {elapsed:.1f}s (wall {wall:.1f}m)")

            except torch.cuda.OutOfMemoryError as e:
                torch.cuda.empty_cache()
                mf.write(json.dumps({
                    "id": cid, "status": "oom", "error": str(e)[:200],
                }) + "\n")
                mf.flush()
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: OOM")

            except Exception as e:
                mf.write(json.dumps({
                    "id": cid, "status": "error", "error": str(e)[:300],
                }) + "\n")
                mf.flush()
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: error {type(e).__name__}: {str(e)[:120]}")

    total = (time.time() - started_at) / 60.0
    print(f"[wan-ti2v] DONE — {total:.1f} min, manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
