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
from PIL import Image, ImageOps

from generation.runners.provenance import can_resume, file_sha256, input_sha256


def load_pipe(model_path: str, dtype: torch.dtype, device: str, cpu_offload: bool = False):
    """Load Wan2.2-TI2V as an image-to-video pipeline."""
    from diffusers import WanImageToVideoPipeline

    print(f"[wan-ti2v] loading pipeline from {model_path} ...")
    pipe = WanImageToVideoPipeline.from_pretrained(model_path, torch_dtype=dtype)
    if cpu_offload:
        if device != "cuda":
            raise RuntimeError("CPU offload requires CUDA")
        pipe.enable_model_cpu_offload(gpu_id=0)
    else:
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
    ap.add_argument("--contracts", default=None,
                    help="Optional reviewed JSONL teaching contracts; validates all cases before model loading")
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
    ap.add_argument("--cpu-offload", action="store_true",
                    help="Offload model components to host RAM to reduce GPU memory use")
    ap.add_argument("--prompt-mode", choices=["source", "focused"], default="source",
                    help="focused: one visible change while preserving first-frame labels")
    ap.add_argument("--negative-prompt", default="",
                    help="Optional visual defects to suppress; recorded in the input fingerprint")
    args = ap.parse_args()
    if args.contracts and args.prompt_mode == "focused":
        ap.error("focused prompt mode cannot override reviewed teaching contracts")

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
    if args.contracts:
        from generation.teaching_contract import load_contracts, prepare_cases
        cases = prepare_cases(
            cases, load_contracts(args.contracts), args.width, args.height,
            args.num_frames, args.fps,
        )
    if args.prompt_mode == "focused":
        from generation.short_clip_prompt import focused_prompt
        for case in cases:
            case["video_prompt"] = focused_prompt(case, args.num_frames / args.fps)

    # Filter to cases that have first-frame images
    valid_cases = []
    for c in cases:
        ff_path = ff_dir / f"{c['id']}.png"
        if ff_path.exists():
            valid_cases.append(c)
        else:
            print(f"[wan-ti2v] WARNING: no first-frame for {c['id']}, skipping")
    print(f"[wan-ti2v] {len(valid_cases)}/{len(cases)} cases have first-frame images")

    # Resume support
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
    for case in valid_cases:
        record = latest_manifest.get(case["id"], {})
        ff_path = ff_dir / f"{case['id']}.png"
        if can_resume(record, out_dir / f"{case['id']}.mp4",
                      input_sha256(case, args, ff_path)):
            done_ids.add(case["id"])
    print(f"[wan-ti2v] resume: {len(done_ids)} already generated")
    if len(done_ids) == len(valid_cases):
        return
    pipe = load_pipe(args.model_path, dtype, device, args.cpu_offload)

    started_at = time.time()
    with manifest_path.open("a") as mf:
        for i, case in enumerate(valid_cases):
            cid = case["id"]
            if cid in done_ids:
                continue

            ff_path = ff_dir / f"{cid}.png"
            first_frame = Image.open(ff_path).convert("RGB")
            # Preserve charts, boards, and geometry. Directly stretching square
            # benchmark inputs to 16:9 visibly deforms axes and playing grids.
            first_frame = ImageOps.pad(
                first_frame,
                (args.width, args.height),
                method=Image.Resampling.LANCZOS,
                color=(245, 245, 245),
                centering=(0.5, 0.5),
            )

            out_mp4 = out_dir / f"{cid}.mp4"
            temporary_mp4 = out_dir / f"{cid}.partial.mp4"
            t0 = time.time()
            gen = torch.Generator(device=device).manual_seed(args.seed)

            try:
                result = pipe(
                    image=first_frame,
                    prompt=case.get("video_prompt", case["prompt_text"]),
                    negative_prompt=args.negative_prompt or None,
                    height=args.height,
                    width=args.width,
                    num_frames=args.num_frames,
                    num_inference_steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    generator=gen,
                )
                frames = result.frames[0] if hasattr(result, "frames") else result[0]
                save_video_mp4(frames, str(temporary_mp4), fps=args.fps)
                video_hash = file_sha256(temporary_mp4)
                temporary_mp4.replace(out_mp4)
                elapsed = time.time() - t0

                mf.write(json.dumps({
                    "id": cid,
                    "prompt_text": case["prompt_text"][:200],
                    "generation_prompt": case.get("video_prompt", case["prompt_text"]),
                    "input_sha256": input_sha256(case, args, ff_path),
                    "video_sha256": video_hash,
                    "model_path": args.model_path,
                    "first_frame_sha256": file_sha256(ff_path),
                    "teaching_contract_sha256": case.get("teaching_contract_sha256"),
                    "target_duration_s": case.get("target_duration_s"),
                    "discipline": case.get("discipline"),
                    "task_type": case.get("task_type"),
                    "difficulty": case.get("difficulty"),
                    "video_path": str(out_mp4),
                    "first_frame_path": str(ff_path),
                    "height": args.height, "width": args.width,
                    "num_frames": args.num_frames, "steps": args.steps,
                    "guidance_scale": args.guidance_scale, "seed": args.seed,
                    "negative_prompt": args.negative_prompt,
                    "fps": args.fps, "dtype": args.dtype,
                    "cpu_offload": args.cpu_offload,
                    "elapsed_s": round(elapsed, 2),
                    "status": "ok",
                }) + "\n")
                mf.flush()

                wall = (time.time() - started_at) / 60.0
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: ok in {elapsed:.1f}s (wall {wall:.1f}m)")

            except torch.cuda.OutOfMemoryError as e:
                temporary_mp4.unlink(missing_ok=True)
                torch.cuda.empty_cache()
                mf.write(json.dumps({
                    "id": cid, "status": "oom", "error": str(e)[:200],
                }) + "\n")
                mf.flush()
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: OOM")

            except Exception as e:
                temporary_mp4.unlink(missing_ok=True)
                mf.write(json.dumps({
                    "id": cid, "status": "error", "error": str(e)[:300],
                }) + "\n")
                mf.flush()
                print(f"[wan-ti2v] [{i+1}/{len(valid_cases)}] {cid}: error {type(e).__name__}: {str(e)[:120]}")

    total = (time.time() - started_at) / 60.0
    print(f"[wan-ti2v] DONE — {total:.1f} min, manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
