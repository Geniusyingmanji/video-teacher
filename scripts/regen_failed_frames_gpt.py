"""Regenerate FAIL first-frames using Azure GPT-Image-1.

Same input contract as regen_failed_frames.py (reads check_report.jsonl FAILs,
uses suggestion + issues to build an improved prompt) but routes to Azure's
GPT-Image-1 deployment instead of a local diffusers pipeline.

Usage:
    python scripts/regen_failed_frames_gpt.py \\
        --prompts data/prompts/pilot_v0_1.jsonl \\
        --check-report data/first_frames/check_report.jsonl \\
        --first-frames data/first_frames \\
        --backup-dir data/first_frames/_backup_before_gpt_image \\
        --iter gpt1
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from eval.judges.gpt55 import make_client


def build_prompt(case: dict, feedback: dict) -> str:
    """Build a GPT-Image-1 prompt led by the judge's suggestion."""
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
    explicit = case.get("first_frame") or case.get("first_frame_spec")

    scene = ("educational diagram, clearly labeled illustration"
             if task_type == "explanation"
             else "educational problem setup, clean whiteboard or blackboard")

    style = {
        "k12": "colorful, friendly, age-appropriate",
        "undergrad": "clean academic textbook style",
        "professional": "precise technical reference style",
    }.get(difficulty, "clean academic style")

    parts = []
    if suggestion:
        parts.append(suggestion)

    if explicit:
        if isinstance(explicit, str):
            parts.append(explicit)
        else:
            if explicit.get("prompt"):
                parts.append(str(explicit["prompt"]))
            must_include = explicit.get("must_include") or []
            avoid = explicit.get("avoid") or []
            quality_checks = explicit.get("quality_checks") or []
            if must_include:
                parts.append("Must include: " + ", ".join(map(str, must_include[:8])) + ".")
            if avoid:
                parts.append("Avoid: " + ", ".join(map(str, avoid[:8])) + ".")
            if quality_checks:
                parts.append("Quality checks: " + ", ".join(map(str, quality_checks[:6])) + ".")
    else:
        parts.append(f"Opening frame for an educational video about {discipline}: {concepts_str}.")
        if elements_str:
            parts.append(f"Must include: {elements_str}.")

    parts.append(f"{scene}.")
    if elements_str:
        parts.append(f"Case visual requirements: {elements_str}.")
    parts.append(f"Style: {style}.")
    parts.append("All text and mathematical symbols must be perfectly legible and correctly spelled.")
    if issues_str:
        parts.append(f"Specifically avoid: {issues_str}.")
    parts.append(
        "Clean uncluttered 16:9 educational-diagram composition, high resolution, "
        "suitable as a static opening frame. Keep important labels and diagrams "
        "inside a central safe area with generous margins for 832x480 video input."
    )
    return " ".join(parts)


def fit_into_canvas(blob: bytes, width: int, height: int) -> Image.Image:
    """Preserve image aspect ratio while normalizing to the TI2V frame size."""
    src = Image.open(io.BytesIO(blob)).convert("RGB")
    sw, sh = src.size
    scale = min(width / sw, height / sh)
    new_w, new_h = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(resized, ((width - new_w) // 2, (height - new_h) // 2))
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--check-report", required=True)
    ap.add_argument("--first-frames", required=True)
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--iter", default="gpt1")
    ap.add_argument("--size", default="1536x1024",
                    help="GPT-Image-1 supports 1024x1024, 1024x1536, 1536x1024.")
    ap.add_argument("--quality", default="medium",
                    help="low|medium|high (medium ~ $0.04, high ~ $0.17)")
    ap.add_argument("--deployment", default="gpt-image-1")
    ap.add_argument("--endpoint", default="https://t2vgoaigpt4o3.openai.azure.com/")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--target-width", type=int, default=832)
    ap.add_argument("--target-height", type=int, default=480)
    ap.add_argument("--keep-raw", action="store_true",
                    help="Write the raw model output instead of normalizing to 832x480.")
    ap.add_argument("--include-errors", action="store_true",
                    help="Also regenerate rows whose check verdict is ERROR.")
    args = ap.parse_args()

    cases = {json.loads(l)["id"]: json.loads(l)
             for l in open(args.prompts) if l.strip()}

    failed = {}
    for l in open(args.check_report):
        l = l.strip()
        if not l:
            continue
        r = json.loads(l)
        verdict = r.get("verdict")
        if (verdict == "FAIL" or (args.include_errors and verdict == "ERROR")) and r["id"] in cases:
            failed[r["id"]] = r

    fails = list(failed.items())
    if args.limit > 0:
        fails = fails[: args.limit]
    print(f"[regen-{args.iter}] {len(fails)} FAIL cases via {args.deployment} "
          f"({args.size}, q={args.quality})")

    ff_dir = Path(args.first_frames)
    ff_dir.mkdir(parents=True, exist_ok=True)
    if args.backup_dir:
        backup = Path(args.backup_dir)
        backup.mkdir(parents=True, exist_ok=True)
        n = 0
        for cid, _ in fails:
            src = ff_dir / f"{cid}.png"
            dst = backup / f"{cid}.png"
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                n += 1
        print(f"[regen-{args.iter}] backed up {n} originals -> {backup}")

    client = make_client(endpoint=args.endpoint, api_version="2025-01-01-preview")

    manifest_path = ff_dir / f"manifest_regen_{args.iter}.jsonl"
    t_start = time.time()
    n_ok = n_err = 0
    with manifest_path.open("w") as mf:
        for i, (cid, feedback) in enumerate(fails):
            case = cases[cid]
            prompt = build_prompt(case, feedback)
            out_path = ff_dir / f"{cid}.png"
            t0 = time.time()
            try:
                resp = client.images.generate(
                    model=args.deployment,
                    prompt=prompt,
                    size=args.size,
                    quality=args.quality,
                    n=1,
                )
                data = resp.data[0]
                blob = None
                if getattr(data, "b64_json", None):
                    blob = base64.b64decode(data.b64_json)
                elif getattr(data, "url", None):
                    import urllib.request
                    with urllib.request.urlopen(data.url, timeout=30) as r:
                        blob = r.read()
                if not blob:
                    raise RuntimeError("no b64_json or url in response")
                if args.keep_raw:
                    out_path.write_bytes(blob)
                    out_size = None
                else:
                    normalized = fit_into_canvas(blob, args.target_width, args.target_height)
                    normalized.save(str(out_path))
                    out_size = list(normalized.size)
                elapsed = time.time() - t0
                n_ok += 1
                mf.write(json.dumps({
                    "id": cid, "iter": args.iter,
                    "image_prompt": prompt[:400],
                    "status": "ok", "elapsed_s": round(elapsed, 2),
                    "size_bytes": len(blob),
                    "normalized_size": out_size,
                }) + "\n")
                mf.flush()
                wall = (time.time() - t_start) / 60.0
                print(f"[regen-{args.iter}] [{i+1}/{len(fails)}] {cid}: "
                      f"ok in {elapsed:.1f}s (wall {wall:.1f}m, {len(blob)//1024}KB)")
            except Exception as e:
                n_err += 1
                err = f"{type(e).__name__}: {str(e)[:200]}"
                mf.write(json.dumps({"id": cid, "status": "error", "error": err}) + "\n")
                mf.flush()
                print(f"[regen-{args.iter}] [{i+1}/{len(fails)}] {cid}: ERR {err[:100]}")

    total = (time.time() - t_start) / 60.0
    print(f"[regen-{args.iter}] DONE — {total:.1f} min, {n_ok} ok, {n_err} err, "
          f"manifest @ {manifest_path}")


if __name__ == "__main__":
    main()
