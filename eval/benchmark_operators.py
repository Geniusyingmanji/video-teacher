"""Reproducible, task-aware video signal operators and narration check.

These are diagnostic proxies, not measurements of semantic teaching quality.
Thresholds are frozen for v1 and must be calibrated on held-out human labels
before claiming construct validity.
"""
from __future__ import annotations

import math
import subprocess

import cv2
import numpy as np


def _clip(value: float) -> float:
    return round(float(np.clip(value, 0, 100)), 4)


def decode_video(path: str, *, max_frames: int = 3000) -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise ValueError("video cannot be opened")
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("invalid video FPS")
        frames = []
        while len(frames) <= max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if frame is None or frame.size == 0:
                raise ValueError("undecodable frame")
            frames.append(cv2.resize(frame, (256, 144), interpolation=cv2.INTER_AREA))
        if len(frames) > max_frames:
            raise ValueError("video exceeds operator frame limit")
        if len(frames) < 2:
            raise ValueError("video has fewer than two frames")
        return frames, fps
    finally:
        cap.release()


def signal_quality(frames: list[np.ndarray]) -> dict:
    """Within-clip focus loss and exposure at 256x144.

    Relative focus avoids treating a clean, flat vector diagram as blurry.
    Uniform blur remains a visual-rubric problem, not a reliable CV claim.
    """
    focus, exposure = [], []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        focus.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        exposure.append(float(np.mean((gray < 8) | (gray > 247))))
    p10 = float(np.percentile(focus, 10))
    p90 = float(np.percentile(focus, 90))
    focus_score = 100 * min(1.0, (p10 + 5) / (0.5 * p90 + 5))
    # White or black backgrounds are legitimate when visible structure remains.
    clipped_p90 = float(np.percentile(exposure, 90))
    exposure_penalty_applicable = p90 < 50
    exposure_score = (100 * (1 - min(1, clipped_p90 / 0.45))
                      if exposure_penalty_applicable else 100.0)
    score = _clip(0.6 * focus_score + 0.4 * exposure_score)
    return {"score": score, "method": "relative_laplacian_focus_and_clipped_pixel_fraction_v1",
            "focus_p10": round(p10, 4), "focus_p90": round(p90, 4),
            "clipped_fraction_p90": round(clipped_p90, 6),
            "exposure_penalty_applicable": exposure_penalty_applicable,
            "focus_score": _clip(focus_score), "exposure_score": _clip(exposure_score),
            "frame_count": len(frames)}


def temporal_consistency(frames: list[np.ndarray], fps: float,
                         expected_steps: int) -> dict:
    """Detect duplicate frames, abrupt residual changes, and luminance flicker.

    Static teaching diagrams are allowed. Freeze only penalizes a clip when
    the task asks for multiple visible ordered steps.
    """
    if len(frames) < 2 or fps <= 0:
        raise ValueError("temporal operator needs at least two frames and valid FPS")
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    differences = np.array([np.mean(cv2.absdiff(a, b)) / 255
                            for a, b in zip(grays, grays[1:])], dtype=float)
    duplicate = differences < 0.002
    longest = run = 0
    for is_duplicate in duplicate:
        run = run + 1 if is_duplicate else 0
        longest = max(longest, run)
    freeze_seconds = longest / fps
    # Outliers relative to the clip's own typical motion; only clear jumps.
    typical = max(0.015, float(np.median(differences)))
    jump_fraction = float(np.mean(differences > max(0.20, 5 * typical)))
    means = np.array([float(g.mean()) / 255 for g in grays])
    luminance_jumps = np.abs(np.diff(means))
    flicker_fraction = float(np.mean(luminance_jumps > 0.16))
    freeze_penalty = min(40.0, 20.0 * max(0, freeze_seconds - 0.5)) if expected_steps > 1 else 0.0
    score = _clip(100 - freeze_penalty - min(35, 350 * jump_fraction)
                  - min(25, 250 * flicker_fraction))
    return {"score": score, "method": "duplicate_jump_flicker_v1",
            "longest_duplicate_run_seconds": round(freeze_seconds, 4),
            "abrupt_change_fraction": round(jump_fraction, 6),
            "luminance_jump_fraction": round(flicker_fraction, 6),
            "expected_steps": expected_steps, "frame_count": len(frames)}


def narration_presence(path: str, ffmpeg: str = "ffmpeg") -> dict:
    """Decode mono PCM and test signal presence; never infer spoken content."""
    proc = subprocess.run([ffmpeg, "-v", "error", "-i", path, "-map", "0:a:0", "-vn", "-ac", "1",
                           "-ar", "16000", "-f", "f32le", "pipe:1"],
                          capture_output=True, timeout=90, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        if "matches no streams" in stderr or "does not contain any stream" in stderr:
            return {"detected": False, "reason": "audio_stream_missing"}
        return {"detected": None, "reason": "audio_decode_failed", "error": stderr[-300:]}
    if not proc.stdout:
        return {"detected": False, "reason": "empty_audio_stream"}
    audio = np.frombuffer(proc.stdout, dtype="<f4")
    if len(audio) < 16000 or not np.isfinite(audio).all():
        return {"detected": None if not np.isfinite(audio).all() else False,
                "reason": "audio_too_short_or_invalid"}
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))
    active = float(np.mean(np.abs(audio) > 0.01))
    detected = rms >= 0.003 and active >= 0.01
    return {"detected": bool(detected), "rms": round(rms, 6),
            "active_fraction": round(active, 6),
            "reason": "signal_present_content_unverified" if detected else "near_silent"}
