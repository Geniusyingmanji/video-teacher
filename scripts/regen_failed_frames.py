"""Regenerate first-frame images that failed quality check.

Reads the check report, finds FAIL cases, and regenerates with an improved
prompt that incorporates GPT-5.5's suggestion + issues. Defaults to FLUX.1-dev
(much better text/symbol rendering than SD 3.5).

Backs up the old PNGs to a per-iteration backup directory so we can compare.

Usage:
    CUDA_VISIBLE_DEVICES=2 python scripts/regen_failed_frames.py \\
        --prompts data/prompts/pilot_v0_1.jsonl \\
        --check-report data/first_frames/check_report.jsonl \\
        --first-frames data/first_frames \\
        --backup-dir data/first_frames_iter0_backup \\
        --iter 1
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import torch


FLUX_MODEL_ID = "/home/azureuser/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/3de623fc3c33e44ffbe2bad470d0f45bccf2eb21"
SD35_MODEL_ID = "/home/azureuser/.cache/huggingface/hub/models--stabilityai--stable-diffusion-3.5-medium/snapshots/b940f670f0eda2d07fbb75229e779da1ad11eb80"


def build_improved_prompt(case: dict, feedback: dict) -> str:
    """Lead with the judge's suggestion (the actionable fix), then add context."""
    discipline = case["discipline"]
    task_type = case["task_type"]
    difficulty = case.get("difficulty", "k12")
    visual_elements = case.get("expected_visual_elements", [])
    concepts = case.get("expected_concepts", [])

    elements_str = ", ".join(visual_elements[:5]) if visual_elements else ""
    concepts_str = ", ".join(concepts[:3]) if concepts else ""

    suggestion = (feedback.get("suggestion") or "").strip()
    issues = feedback.get("issues") or []
    issues_str = "; ".join(issues[:3]) if issues else ""

    scene_type = ("educational diagram, clearly labeled illustration"
                  if task_type == "explanation"
                  else "educational problem setup, clean whiteboard or blackboard layout")

    difficulty_style = {
        "k12": "colorful, friendly, age-appropriate for teenagers",
        "undergrad": "clean academic style, textbook-quality",
        "professional": "professional, precise, technical reference quality",
    }.get(difficulty, "clean academic style")

    # Lead with the suggestion — it's the actionable fix from GPT-5.5
    parts = []
    if suggestion:
        parts.append(suggestion)
    parts.append(f"Opening frame of an educational video about {discipline}: {concepts_str}.")
    parts.append(scene_type + ".")
    if elements_str:
        parts.append(f"Required visual elements: {elements_str}.")
    parts.append(f"Style: {difficulty_style}.")
    parts.append("All text and mathematical symbols must be legible and correctly written, "
                 "no garbled letters, no nonsense symbols.")
    if issues_str:
        parts.append(f"Avoid these problems: {issues_str}.")
    parts.append("Sharp focus, clean uncluttered composition, high resolution.")
    return " ".join(parts)[:1200]


def load_pipeline(model_id: str):
    """Load the right diffusers pipeline class for the model."""
    if "FLUX" in model_id.upper() or "flux" in model_id:
        from diffusers import FluxPipeline
        print(f"[regen] loading FluxPipeline from {model_id} ...")
        return FluxPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
    from diffusers import DiffusionPipeline
    print(f"[regen] loading DiffusionPipeline from {model_id} ...")
    return DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--check-report", required=True)
    ap.add_argument("--first-frames", required=True)
    ap.add_argument("--backup-dir", default=None,
                    help="If set, back up originals here before overwriting.")
    ap.add_argument("--iter", type=int, default=1,
                    help="Iteration number; affects seed and manifest filename.")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance-scale", type=float, default=3.5)
    ap.add_argument("--model-id", default=FLUX_MODEL_ID,
                    help="HF model id or local path. Default: FLUX.1-dev.")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cases = {json.loads(l)["id"]: json.loads(l)
             for l in open(args.prompts) if l.strip()}

    failed = {}
    with open(args.check_report) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("verdict") == "FAIL" and r["id"] in cases:
                failed[r["id"]] = r

    if not failed:
        print(f"[regen-iter{args.iter}] no FAIL cases — nothing to do")
        return

    fails = list(failed.items())
    if args.limit > 0:
        fails = fails[: args.limit]
    print(f"[regen-iter{args.iter}] {len(fails)} FAIL cases to regenerate "
          f"(model={args.model_id})")

    ff_dir = Path(args.first_frames)
    ff_dir.mkdir(parents=True, exist_ok=True)

    # Backup originals
    if args.backup_dir:
        backup = Path(args.backup_dir)
        backup.mkdir(parents=True, exist_ok=True)
        n_backed = 0
        for cid, _ in fails:
            src = ff_dir / f"{cid}.png"
            dst = backup / f"{cid}.png"
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                n_backed += 1
        print(f"[regen-iter{args.iter}] backed up {n_backed} originals -> {backup}")

    pipe = load_pipeline(args.model_id)
    # FLUX is too big for the ~30GB we have free per GPU — use CPU offload.
    # This shuttles modules to CPU when idle, so peak VRAM stays low.
    if hasattr(pipe, "enable_model_cpu_offload"):
        pipe.enable_model_cpu_offload()
        print(f"[regen-iter{args.iter}] using model_cpu_offload")
    else:
        pipe.to("cuda")
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    if hasattr(pipe, "enable_vae_tiling"):
        try:
            pipe.enable_vae_tiling()
        except Exception:
            pass
    print(f"[regen-iter{args.iter}] pipeline loaded: {type(pipe).__name__}")

    manifest_path = ff_dir / f"manifest_regen_iter{args.iter}.jsonl"
    t_start = time.time()
    with manifest_path.open("w") as mf:
        for i, (cid, feedback) in enumerate(fails):
            case = cases[cid]
            prompt = build_improved_prompt(case, feedback)
            out_path = ff_dir / f"{cid}.png"
            # Per-iter, per-case seed: distinct from previous attempts
            seed = (hash(cid) & 0xFFFF) + args.iter * 7919
            t0 = time.time()
            try:
                gen = torch.Generator("cuda").manual_seed(seed)
                kwargs = dict(
                    prompt=prompt,
                    height=args.height,
                    width=args.width,
                    num_inference_steps=args.steps,
                    guidance_scale=args.guidance_scale,
                    generator=gen,
                )
                result = pipe(**kwargs)
                result.images[0].save(str(out_path))
                elapsed = time.time() - t0
                mf.write(json.dumps({
                    "id": cid, "iter": args.iter, "seed": seed,
                    "image_prompt": prompt[:400],
                    "status": "ok", "elapsed_s": round(elapsed, 2),
                }) + "\n")
                mf.flush()
                wall = (time.time() - t_start) / 60.0
                print(f"[regen-iter{args.iter}] [{i+1}/{len(fails)}] {cid}: "
                      f"ok in {elapsed:.1f}s (wall {wall:.1f}m)")
            except torch.cuda.OutOfMemoryError as e:
                torch.cuda.empty_cache()
                mf.write(json.dumps({"id": cid, "status": "oom",
                                     "error": str(e)[:200]}) + "\n")
                mf.flush()
                print(f"[regen-iter{args.iter}] [{i+1}/{len(fails)}] {cid}: OOM")
            except Exception as e:
                mf.write(json.dumps({"id": cid, "status": "error",
                                     "error": str(e)[:300]}) + "\n")
                mf.flush()
                print(f"[regen-iter{args.iter}] [{i+1}/{len(fails)}] {cid}: "
                      f"error {type(e).__name__}: {str(e)[:120]}")

    total = (time.time() - t_start) / 60.0
    print(f"[regen-iter{args.iter}] DONE — {total:.1f} min, "
          f"manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
