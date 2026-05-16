"""Generate first-frame images for rise-teacher pilot cases using FLUX.1-dev.

For each case in the prompt JSONL, constructs a static educational-scene prompt
from the case metadata and generates an 832x480 image (matching video resolution).

Usage:
    CUDA_VISIBLE_DEVICES=2 python scripts/generate_first_frames.py \
        --prompts data/prompts/pilot_v0_1.jsonl \
        --out data/first_frames \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch


def build_image_prompt(case: dict) -> str:
    """Build a FLUX prompt for a static educational first-frame image."""
    discipline = case["discipline"]
    task_type = case["task_type"]
    difficulty = case.get("difficulty", "k12")
    visual_elements = case.get("expected_visual_elements", [])
    concepts = case.get("expected_concepts", [])
    audience = case.get("pedagogical_target_audience", "")
    prompt_text = case.get("prompt_text", "")

    elements_str = ", ".join(visual_elements[:5]) if visual_elements else ""
    concepts_str = ", ".join(concepts[:3]) if concepts else ""

    # Extract the core topic from prompt_text
    topic = prompt_text.split(".")[-2] if "." in prompt_text else prompt_text[:120]
    # Clean up common prefixes
    for prefix in [
        "Generate a 10-second educational video ",
        "Generate a short educational video ",
        "Generate a video that solves: ",
        "Generate a video ",
        "Generate an educational video ",
    ]:
        if topic.strip().startswith(prefix):
            topic = topic.strip()[len(prefix):]
            break

    if task_type == "explanation":
        scene_type = "educational diagram, clear labeled illustration"
        action_hint = "showing the starting state of a concept explanation"
    else:
        scene_type = "educational problem setup, clean whiteboard or blackboard layout"
        action_hint = "showing the problem statement ready to be solved step by step"

    difficulty_style = {
        "k12": "colorful, friendly, age-appropriate for teenagers",
        "undergrad": "clean academic style, textbook-quality",
        "professional": "professional, precise, technical reference quality",
    }.get(difficulty, "clean academic style")

    prompt = (
        f"A single static frame for an educational video about {discipline}. "
        f"{scene_type}, {action_hint}. "
        f"Visual elements: {elements_str}. "
        f"Topic: {concepts_str}. "
        f"Style: {difficulty_style}, high resolution, no text watermarks, "
        f"clean background, well-lit, suitable as the opening frame of a teaching video. "
        f"No motion blur, no video artifacts, sharp and clear."
    )
    return prompt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance-scale", type=float, default=3.5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model-id", default="/home/azureuser/.cache/huggingface/hub/models--stabilityai--stable-diffusion-3.5-medium/snapshots/b940f670f0eda2d07fbb75229e779da1ad11eb80")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load prompts
    cases: list[dict] = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.limit > 0:
        cases = cases[:args.limit]
    print(f"[imggen] {len(cases)} cases to generate first frames for")

    # Load image generation pipeline (auto-detect type)
    from diffusers import DiffusionPipeline

    print(f"[imggen] loading {args.model_id} ...")
    pipe = DiffusionPipeline.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
    )
    pipe.to("cuda")
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    print(f"[imggen] pipeline loaded: {type(pipe).__name__}")

    # Generate
    manifest_path = out_dir / "manifest.jsonl"
    done_ids = set()
    if manifest_path.exists():
        with manifest_path.open() as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("status") == "ok":
                        done_ids.add(entry["id"])
                except Exception:
                    pass
    print(f"[imggen] resume: {len(done_ids)} already done")

    started_at = time.time()
    with manifest_path.open("a") as mf:
        for i, case in enumerate(cases):
            cid = case["id"]
            if cid in done_ids:
                print(f"[imggen] [{i+1}/{len(cases)}] {cid}: skip (already done)")
                continue

            img_prompt = build_image_prompt(case)
            out_path = out_dir / f"{cid}.png"
            t0 = time.time()

            try:
                gen = torch.Generator("cuda").manual_seed(args.seed)
                result = pipe(
                    prompt=img_prompt,
                    height=args.height,
                    width=args.width,
                    num_inference_steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    generator=gen,
                )
                image = result.images[0]
                image.save(str(out_path))
                elapsed = time.time() - t0

                mf.write(json.dumps({
                    "id": cid,
                    "discipline": case.get("discipline"),
                    "task_type": case.get("task_type"),
                    "difficulty": case.get("difficulty"),
                    "image_path": str(out_path),
                    "image_prompt": img_prompt[:300],
                    "status": "ok",
                    "elapsed_s": round(elapsed, 2),
                }) + "\n")
                mf.flush()

                wall = (time.time() - started_at) / 60.0
                print(f"[imggen] [{i+1}/{len(cases)}] {cid}: ok in {elapsed:.1f}s (wall {wall:.1f}m)")

            except torch.cuda.OutOfMemoryError as e:
                torch.cuda.empty_cache()
                mf.write(json.dumps({
                    "id": cid, "status": "oom", "error": str(e)[:200],
                }) + "\n")
                mf.flush()
                print(f"[imggen] [{i+1}/{len(cases)}] {cid}: OOM")

            except Exception as e:
                mf.write(json.dumps({
                    "id": cid, "status": "error", "error": str(e)[:300],
                }) + "\n")
                mf.flush()
                print(f"[imggen] [{i+1}/{len(cases)}] {cid}: error {type(e).__name__}: {str(e)[:120]}")

    total = (time.time() - started_at) / 60.0
    print(f"[imggen] DONE — {total:.1f} min, manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
