"""Wan2.2-TI2V-5B generation runner for the rise-teacher pilot.

Loads the diffusers pipeline once, then iterates a JSONL prompt set, writing
MP4 per case + a results manifest.

Usage:
    python -m generation.runners.wan_runner \
        --prompts data/prompts/pilot_v0_1.jsonl \
        --out generation/outputs_data/wan2_2_ti2v_5b/pilot_v0_1 \
        --num-frames 49 --height 480 --width 704 --steps 30
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch

from generation.runners.provenance import can_resume, file_sha256, input_sha256


def load_pipe(model_path: str, dtype: torch.dtype, device: str):
    """Load Wan2.2-TI2V-5B as a text-to-video pipeline."""
    from diffusers import DiffusionPipeline

    print(f"[wan] loading pipeline from {model_path} ...")
    pipe = DiffusionPipeline.from_pretrained(model_path, torch_dtype=dtype)
    pipe.to(device)
    # Try to free memory aggressively
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    if hasattr(pipe, "enable_vae_tiling"):
        try:
            pipe.enable_vae_tiling()
        except Exception:
            pass
    print(f"[wan] loaded. pipeline class: {type(pipe).__name__}")
    return pipe


def save_video_mp4(frames, path: str, fps: int = 16) -> None:
    """frames: list[PIL.Image] or numpy array of shape (T, H, W, 3)."""
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
    ap.add_argument("--contracts", default=None,
                    help="Optional reviewed JSONL teaching contracts; validates all cases before model loading")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-path",
                    default="/data/zyf/rise-teacher/models/Wan2.2-TI2V-5B-Diffusers")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--width", type=int, default=704)
    ap.add_argument("--num-frames", type=int, default=49)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance-scale", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=42)
    # Wan 2.x native frame rate is 24fps. The pilot v0.1 (3s output) used
    # fps=16 by mistake, stretching 49 frames over ~3s of playback. Default
    # corrected to 24 for v0.2; the 5s reruns use num_frames=121 @ 24fps.
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0,
                    help="If >0, only first N prompts (for quick smoke).")
    ap.add_argument("--dtype", default="bfloat16",
                    choices=["bfloat16", "float16", "float32"])
    args = ap.parse_args()

    dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[args.dtype]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"

    # Load prompts
    prompts: list[dict] = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                prompts.append(json.loads(line))
    if args.limit > 0:
        prompts = prompts[: args.limit]
    if args.contracts:
        from generation.teaching_contract import load_contracts, prepare_cases
        prompts = prepare_cases(
            prompts, load_contracts(args.contracts), args.width, args.height,
            args.num_frames, args.fps,
        )
    print(f"[wan] {len(prompts)} prompts to generate")

    # Resume support: skip already-generated
    done_ids = set()
    latest_manifest = {}
    if manifest_path.exists():
        with manifest_path.open() as f:
            for line in f:
                try:
                    record = json.loads(line)
                    latest_manifest[record["id"]] = record
                except Exception:
                    pass
    for prompt in prompts:
        record = latest_manifest.get(prompt["id"], {})
        if can_resume(record, out_dir / f"{prompt['id']}.mp4", input_sha256(prompt, args)):
            done_ids.add(prompt["id"])
    print(f"[wan] resume: {len(done_ids)} already generated")
    if len(done_ids) == len(prompts):
        return
    pipe = load_pipe(args.model_path, dtype, device)

    started_at = time.time()
    with manifest_path.open("a") as manifest_f:
        for i, p in enumerate(prompts):
            cid = p["id"]
            if cid in done_ids:
                continue
            out_mp4 = out_dir / f"{cid}.mp4"
            temporary_mp4 = out_dir / f"{cid}.partial.mp4"
            t0 = time.time()
            gen = torch.Generator(device=device).manual_seed(args.seed)
            try:
                result = pipe(
                    prompt=p.get("video_prompt", p["prompt_text"]),
                    height=args.height,
                    width=args.width,
                    num_frames=args.num_frames,
                    num_inference_steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    generator=gen,
                )
                # diffusers conventions: result.frames is a list-of-list of PIL
                frames = result.frames[0] if hasattr(result, "frames") else result[0]
                save_video_mp4(frames, str(temporary_mp4), fps=args.fps)
                video_hash = file_sha256(temporary_mp4)
                temporary_mp4.replace(out_mp4)
                elapsed = time.time() - t0
                manifest_f.write(json.dumps({
                    "id": cid,
                    "prompt_text": p["prompt_text"][:200],
                    "generation_prompt": p.get("video_prompt", p["prompt_text"]),
                    "input_sha256": input_sha256(p, args),
                    "video_sha256": video_hash,
                    "model_path": args.model_path,
                    "teaching_contract_sha256": p.get("teaching_contract_sha256"),
                    "target_duration_s": p.get("target_duration_s"),
                    "discipline": p.get("discipline"),
                    "task_type": p.get("task_type"),
                    "video_path": str(out_mp4),
                    "height": args.height, "width": args.width,
                    "num_frames": args.num_frames, "steps": args.steps,
                    "guidance_scale": args.guidance_scale, "seed": args.seed,
                    "fps": args.fps, "dtype": args.dtype,
                    "elapsed_s": round(elapsed, 2),
                    "status": "ok",
                }) + "\n")
                manifest_f.flush()
                wall = (time.time() - started_at) / 60.0
                print(f"[wan] [{i+1}/{len(prompts)}] {cid}: ok in {elapsed:.1f}s (wall {wall:.1f}m)")
            except torch.cuda.OutOfMemoryError as e:
                temporary_mp4.unlink(missing_ok=True)
                torch.cuda.empty_cache()
                manifest_f.write(json.dumps({
                    "id": cid, "status": "oom", "error": str(e)[:200],
                }) + "\n")
                manifest_f.flush()
                print(f"[wan] [{i+1}/{len(prompts)}] {cid}: OOM (continuing)")
            except Exception as e:
                temporary_mp4.unlink(missing_ok=True)
                manifest_f.write(json.dumps({
                    "id": cid, "status": "error", "error": str(e)[:300],
                }) + "\n")
                manifest_f.flush()
                print(f"[wan] [{i+1}/{len(prompts)}] {cid}: error {type(e).__name__}: {str(e)[:120]}")

    total = (time.time() - started_at) / 60.0
    print(f"[wan] DONE — {total:.1f} min wall, manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
