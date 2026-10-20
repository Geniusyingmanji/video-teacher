"""Render a short, deterministic teaching video from one checked contract.

This is a code-rendered baseline: a visible setup is followed by the checked
result. It does not claim to reproduce a stochastic text-to-video model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from generation.contract_frame import render_first_frame
from generation.teaching_contract import ContractError, validate_contract


def _checked_video(path: Path, setup: np.ndarray, result: np.ndarray,
                   expected_frames: int, fps: int) -> dict:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ContractError(f"encoded video cannot be opened: {path}")
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = float(capture.get(cv2.CAP_PROP_FPS))
        if count != expected_frames or abs(actual_fps - fps) > 0.1:
            raise ContractError(f"encoded video metadata differs: {count} frames at {actual_fps} fps")
        ok_first, first = capture.read()
        capture.set(cv2.CAP_PROP_POS_FRAMES, count - 1)
        ok_last, last = capture.read()
        if not ok_first or not ok_last:
            raise ContractError("encoded video is missing its first or last frame")
        first_error = float(np.mean(cv2.absdiff(first, setup)))
        last_error = float(np.mean(cv2.absdiff(last, result)))
        if first_error > 15 or last_error > 15:
            raise ContractError(f"encoded video changed endpoint frames: {first_error:.1f}, {last_error:.1f}")
        return {"frame_count": count, "fps": actual_fps,
                "duration_s": round(count / actual_fps, 3),
                "first_frame_mean_error": round(first_error, 3),
                "last_frame_mean_error": round(last_error, 3)}
    finally:
        capture.release()


def render_contract_video(contract: dict, case: dict, out_path: str | Path,
                          *, width: int = 832, height: int = 480,
                          fps: int = 24) -> dict:
    """Validate a beat, encode setup/result holds, then verify the actual MP4."""
    if width <= 0 or height <= 0 or fps <= 0:
        raise ContractError("video width, height and fps must be positive")
    target = contract.get("target_duration_s")
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        raise ContractError("contract target_duration_s must be numeric")
    validate_contract(contract, case, width, height, float(target))
    frame_count = round(float(target) * fps)
    if frame_count < 2:
        raise ContractError("video must contain at least two frames")
    setup_frames = max(1, min(frame_count - 1, round(frame_count * 0.4)))
    setup = cv2.cvtColor(np.asarray(render_first_frame(contract, width, height, "setup")),
                         cv2.COLOR_RGB2BGR)
    result = cv2.cvtColor(np.asarray(render_first_frame(contract, width, height, "result")),
                          cv2.COLOR_RGB2BGR)
    if np.array_equal(setup, result):
        raise ContractError("setup and result frames are identical")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pending = out_path.with_name(out_path.stem + ".partial.mp4")
    writer = cv2.VideoWriter(str(pending), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))
    if not writer.isOpened():
        raise ContractError(f"MP4 encoder cannot open {pending}")
    try:
        for index in range(frame_count):
            writer.write(setup if index < setup_frames else result)
    finally:
        writer.release()
    try:
        inspection = _checked_video(pending, setup, result, frame_count, fps)
        pending.replace(out_path)
    except Exception:
        pending.unlink(missing_ok=True)
        raise
    return {
        "id": case["id"], "video_path": str(out_path),
        "generation_mode": "checked_contract_cut_v1", "has_audio": False,
        "width": width, "height": height, "setup_frames": setup_frames,
        "result_frames": frame_count - setup_frames,
        "contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "video_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        **inspection,
    }
