"""Replace data/first_frames/{case_id}.png with the selected real images.

For each case in selections.jsonl:
  - If best >= 0: copy the chosen MMMU/AI2D image, resize/letterbox to 832x480
    (Wan TI2V input size) onto a black canvas, save as PNG.
  - If REJECT: leave the existing PNG (which is the GPT-Image-1 fallback).

The current data/first_frames/{case_id}.png files are backed up first.

Usage:
    python scripts/apply_real_first_frames.py \\
        --selections data/first_frames_mmmu/selections_v3.jsonl \\
        --first-frames data/first_frames \\
        --backup-dir data/first_frames/_backup_before_real
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


TARGET_W, TARGET_H = 832, 480


def fit_into_canvas(src: Image.Image, w: int, h: int,
                    bg=(0, 0, 0)) -> Image.Image:
    """Resize src to fit inside (w, h) preserving aspect, pad to canvas."""
    src = src.convert("RGB")
    sw, sh = src.size
    scale = min(w / sw, h / sh)
    new_w, new_h = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg)
    canvas.paste(resized, ((w - new_w) // 2, (h - new_h) // 2))
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selections", required=True)
    ap.add_argument("--first-frames", required=True)
    ap.add_argument("--backup-dir", required=True)
    ap.add_argument("--candidates", default=None,
                    help="candidates jsonl to look up chosen image_path if not "
                         "already in selections rows.")
    args = ap.parse_args()

    selections = [json.loads(l) for l in open(args.selections) if l.strip()]

    # Optional: load candidates to resolve chosen path when only `best` index is stored
    cand_index: dict[str, list[dict]] = {}
    if args.candidates:
        for l in open(args.candidates):
            if l.strip():
                r = json.loads(l)
                cand_index[r["case_id"]] = r.get("candidates", [])

    ff_dir = Path(args.first_frames)
    backup = Path(args.backup_dir)
    backup.mkdir(parents=True, exist_ok=True)

    n_replaced = n_keep = n_missing = 0
    for sel in selections:
        cid = sel["case_id"]
        best = sel.get("best", -1)
        dst = ff_dir / f"{cid}.png"

        # Backup
        if dst.exists():
            bdst = backup / f"{cid}.png"
            if not bdst.exists():
                shutil.copy2(dst, bdst)

        if best is None or best < 0:
            n_keep += 1
            continue

        chosen_path = sel.get("chosen_image_path")
        if not chosen_path and cid in cand_index:
            cands = cand_index[cid]
            if best < len(cands):
                chosen_path = cands[best]["image_path"]
        if not chosen_path:
            print(f"[apply] {cid}: PICK={best} but no chosen_image_path — skip")
            n_missing += 1
            continue
        src_path = Path(chosen_path)
        if not src_path.is_absolute():
            # try treating relative to project root
            src_path = Path("/home/azureuser/workspace-gzy/zyf/datasets") / chosen_path
        if not src_path.exists():
            print(f"[apply] {cid}: missing source {src_path} — skip")
            n_missing += 1
            continue
        try:
            img = Image.open(str(src_path))
            out = fit_into_canvas(img, TARGET_W, TARGET_H)
            out.save(str(dst))
            n_replaced += 1
            src_marker = "ai2d" if "ai2d" in str(src_path) else "mmmu"
            print(f"[apply] {cid}: replaced ({src_marker}) from {src_path.name}")
        except Exception as e:
            print(f"[apply] {cid}: ERROR {type(e).__name__}: {e}")
            n_missing += 1

    print(f"\n[apply] DONE — replaced {n_replaced}, kept {n_keep} (REJECT fallback), "
          f"missing {n_missing}")


if __name__ == "__main__":
    main()
