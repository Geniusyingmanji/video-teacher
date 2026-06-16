"""Generate first-frame images for arbitrary rise-teacher prompt JSONL via GPT-Image-1.

This complements generate_first_frames.py, which uses a local diffusers model.
It is intended for accepted candidate files that include a `first_frame` spec.

Usage:
    python scripts/generate_first_frames_gpt.py \
        --prompts data/prompts/longrun_<prefix>/accepted.jsonl \
        --out data/first_frames_candidates/<prefix> \
        --quality high --limit 10
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.judges.gpt55 import make_client
from scripts.generate_first_frames import build_image_prompt
from scripts.regen_failed_frames_gpt import fit_into_canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    ap.add_argument("--deployment", default="gpt-image-1")
    ap.add_argument("--endpoint", default="https://t2vgoaigpt4o3.openai.azure.com/")
    ap.add_argument("--target-width", type=int, default=832)
    ap.add_argument("--target-height", type=int, default=480)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep-raw", action="store_true")
    args = ap.parse_args()

    cases = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.limit > 0:
        cases = cases[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"

    done_ids = set()
    if manifest_path.exists():
        with manifest_path.open() as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    if row.get("status") == "ok":
                        done_ids.add(row.get("id"))

    print(f"[gpt-imggen] {len(cases)} cases; resume={len(done_ids)}")
    client = make_client(endpoint=args.endpoint, api_version="2025-01-01-preview")
    started = time.time()
    n_ok = n_err = 0

    with manifest_path.open("a") as mf:
        for i, case in enumerate(cases, 1):
            cid = case["id"]
            if cid in done_ids:
                print(f"[gpt-imggen] [{i}/{len(cases)}] {cid}: skip")
                continue
            prompt = build_image_prompt(case)
            out_path = out_dir / f"{cid}.png"
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
                    raise RuntimeError("no b64_json or url in image response")
                if args.keep_raw:
                    out_path.write_bytes(blob)
                    normalized_size = None
                else:
                    normalized = fit_into_canvas(blob, args.target_width, args.target_height)
                    normalized.save(str(out_path))
                    normalized_size = list(normalized.size)
                elapsed = time.time() - t0
                n_ok += 1
                mf.write(json.dumps({
                    "id": cid,
                    "image_path": str(out_path),
                    "image_prompt": prompt[:500],
                    "status": "ok",
                    "elapsed_s": round(elapsed, 2),
                    "size_bytes": len(blob),
                    "normalized_size": normalized_size,
                }, ensure_ascii=False) + "\n")
                mf.flush()
                wall = (time.time() - started) / 60.0
                print(f"[gpt-imggen] [{i}/{len(cases)}] {cid}: ok in {elapsed:.1f}s (wall {wall:.1f}m)")
            except Exception as exc:
                n_err += 1
                err = f"{type(exc).__name__}: {str(exc)[:200]}"
                mf.write(json.dumps({
                    "id": cid,
                    "status": "error",
                    "error": err,
                }, ensure_ascii=False) + "\n")
                mf.flush()
                print(f"[gpt-imggen] [{i}/{len(cases)}] {cid}: ERR {err}")

    total = (time.time() - started) / 60.0
    print(f"[gpt-imggen] DONE {total:.1f}m; ok={n_ok}; error={n_err}; manifest={manifest_path}")


if __name__ == "__main__":
    main()
