"""Offline, reproducible first pass over generated teaching videos.

This checks file-level failures and saves original-resolution evidence frames.
Knowledge and layout judgments still require reviewing those frames.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


# Include 65%: several local Code2Video defects occurred between the old 50%
# and 75% samples. These frames are review evidence, not a full-video proof.
SAMPLE_POSITIONS = (0.02, 0.25, 0.50, 0.65, 0.75, 0.98)


def load_prompts(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    return {
        row["id"]: row
        for line in path.read_text(encoding="utf-8").splitlines()
        if (row := json.loads(line.strip()))
    }


def inspect_video(path: Path, out_dir: Path, target_duration_s: float | None) -> dict:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return {"id": path.stem, "video_path": str(path), "status": "unreadable"}
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if count <= 0 or fps <= 0 or width <= 0 or height <= 0:
            return {"id": path.stem, "video_path": str(path), "status": "invalid_metadata"}

        duration = count / fps
        frames: list[tuple[float, Image.Image]] = []
        for position in SAMPLE_POSITIONS:
            frame_number = round((count - 1) * position)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, bgr = cap.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            frames.append((frame_number / fps, Image.fromarray(rgb)))
    finally:
        cap.release()

    flags = []
    if target_duration_s is not None and duration > target_duration_s * 1.2:
        flags.append("over_target_duration")
    if target_duration_s is not None and duration < target_duration_s * 0.8:
        flags.append("under_target_duration")
    if len(frames) != len(SAMPLE_POSITIONS):
        flags.append("frame_decode_failure")

    evidence_dir = out_dir / "frames" / path.stem
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for index, (seconds, frame) in enumerate(frames):
        frame.save(evidence_dir / f"{index:02d}_{seconds:.2f}s.png")
        # VisualEDU-style render feedback: reviewers see the actual frame with
        # fixed safe areas. This overlay is never used as generation evidence.
        overlay = frame.copy()
        pen = ImageDraw.Draw(overlay)
        margin_x, margin_y = round(width * .04), round(height * .05)
        title_bottom = round(height * .15)
        pen.rectangle((margin_x, margin_y, width - margin_x, height - margin_y),
                      outline="#00e5ff", width=2)
        pen.line((margin_x, title_bottom, width - margin_x, title_bottom),
                 fill="#ffb000", width=2)
        overlay_dir = out_dir / "layout_overlays" / path.stem
        overlay_dir.mkdir(parents=True, exist_ok=True)
        overlay.save(overlay_dir / f"{index:02d}_{seconds:.2f}s.png")

    # The contact sheet is for navigation; source PNGs retain all text pixels.
    thumb_width = 480
    thumb_height = round(height * thumb_width / width)
    sheet = Image.new("RGB", (thumb_width, (thumb_height + 30) * len(frames)), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    for index, (seconds, frame) in enumerate(frames):
        y = index * (thumb_height + 30)
        draw.text((8, y + 7), f"{path.stem}  {seconds:.2f}s", fill="black")
        sheet.paste(frame.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS), (0, y + 30))
    sheet_path = out_dir / "contact_sheets" / f"{path.stem}.jpg"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=90)

    return {
        "id": path.stem,
        "video_path": str(path),
        "status": "review_required" if flags else "metadata_ok_review_required",
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": count,
        "duration_s": round(duration, 3),
        "target_duration_s": target_duration_s,
        "flags": flags,
        "sample_times_s": [round(t, 3) for t, _ in frames],
        "contact_sheet": str(sheet_path),
        "evidence_dir": str(evidence_dir),
        "layout_overlay_dir": str(out_dir / "layout_overlays" / path.stem),
        "layout_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos", type=Path, default=Path("data/videos"))
    parser.add_argument("--prompts", type=Path, default=Path("data/prompts/pilot_v0_1.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("results/video_audit"))
    parser.add_argument("--target-duration-s", type=float, default=5.0)
    parser.add_argument("--no-duration-check", action="store_true",
                        help="Review long reference videos without a short-clip duration target")
    args = parser.parse_args()
    if args.target_duration_s <= 0 and not args.no_duration_check:
        parser.error("--target-duration-s must be positive")
    prompts = load_prompts(args.prompts if args.prompts.is_file() else None)
    videos = sorted(args.videos.glob("*.mp4"))
    if not videos:
        parser.error(f"no MP4 files found in {args.videos}")
    args.out.mkdir(parents=True, exist_ok=True)

    records = []
    for video in videos:
        case = prompts.get(video.stem, {})
        target = None if args.no_duration_check else float(case.get("target_duration_s", args.target_duration_s))
        record = inspect_video(video, args.out, target)
        record["prompt_found"] = bool(case)
        record["task_type"] = case.get("task_type")
        records.append(record)
        print(f"{video.name}: {record['status']} {record.get('duration_s', '?')}s {record.get('flags', [])}")

    report = args.out / "audit.jsonl"
    report.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
