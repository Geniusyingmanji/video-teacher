"""Render a short, deterministic teaching video from one checked contract.

This is a code-rendered baseline with setup, contract-defined motion, and
result phases. It does not claim to reproduce a stochastic text-to-video model.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from generation.contract_frame import render_first_frame
from generation.teaching_contract import ContractError, _operand, validate_contract


def _primitive(contract: dict, selector: str) -> dict:
    try:
        element_id, index_text = selector.rsplit(":", 1)
        element = next(item for item in contract["layout"] if item["id"] == element_id)
        return element["draw"][int(index_text)]
    except (ValueError, StopIteration, KeyError, IndexError, TypeError) as exc:
        raise ContractError(f"invalid animation selector: {selector}") from exc


def _number(value: object, beat: dict) -> float:
    resolved = _operand(value, beat) if isinstance(value, dict) else value
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float)) or not math.isfinite(resolved):
        raise ContractError(f"invalid animation coordinate: {resolved!r}")
    return float(resolved)


def _point(primitive: dict, index: int, beat: dict, width: int, height: int) -> tuple[float, float]:
    if primitive.get("type") != "radial_dots":
        raise ContractError("move_radial_dot selectors must name radial_dots primitives")
    count = _operand(primitive["count"], beat) if isinstance(primitive["count"], dict) else primitive["count"]
    slots = primitive.get("slots", count)
    if not isinstance(count, int) or not isinstance(slots, int) or isinstance(count, bool) or isinstance(slots, bool) or not 0 <= index < count <= slots <= 32:
        raise ContractError("invalid radial dot index, count or slots")
    center = primitive["center"]
    radius = _number(primitive["radius"], beat) * min(width, height)
    angle = -math.pi / 2 + index * 2 * math.pi / slots
    return (_number(center[0], beat) * width + radius * math.cos(angle),
            _number(center[1], beat) * height + radius * math.sin(angle))


def _motion_image(contract: dict, progress: float, width: int, height: int) -> Image.Image:
    animation = contract.get("animation")
    if not isinstance(animation, dict):
        raise ContractError("contract animation specification is required")
    kind = animation.get("type")
    working = deepcopy(contract)
    if kind == "reveal_elements":
        final_ids = animation.get("final_element_ids")
        if not isinstance(final_ids, list) or not final_ids:
            raise ContractError("reveal_elements needs final_element_ids")
        if progress < 0.5:
            for element in working["layout"]:
                if element["id"] in final_ids:
                    element["phase"] = "hidden"
        return render_first_frame(working, width, height, "result")
    if kind == "grow_lines":
        selectors = animation.get("selectors")
        if not isinstance(selectors, list) or not selectors:
            raise ContractError("grow_lines needs selectors")
        for selector in selectors:
            primitive = _primitive(working, selector)
            if primitive.get("type") not in {"line", "arrow"} or primitive.get("phase") != "result":
                raise ContractError(f"grow_lines requires a result-phase line: {selector}")
            start, end = primitive["start"], primitive["end"]
            if len(start) != 2 or len(end) != 2:
                raise ContractError(f"invalid line endpoints: {selector}")
            primitive["end"] = [
                _number(start[i], working["beat"]) * (1 - progress)
                + _number(end[i], working["beat"]) * progress for i in range(2)
            ]
        for selector in animation.get("hide_until_final", []):
            _primitive(working, selector)["phase"] = "hidden"
        return render_first_frame(working, width, height, "result")
    if kind == "move_radial_dot":
        source = _primitive(working, animation.get("source", ""))
        target = _primitive(working, animation.get("target", ""))
        beat = working["beat"]
        source_count = _operand(source["count"], beat) if isinstance(source["count"], dict) else source["count"]
        target_slot = animation.get("target_slot")
        if not isinstance(source_count, int) or source_count < 1 or not isinstance(target_slot, int):
            raise ContractError("move_radial_dot needs a source dot and integer target_slot")
        start = _point(source, source_count - 1, beat, width, height)
        end = _point(target, target_slot, beat, width, height)
        source["count"] = source_count - 1
        image = render_first_frame(working, width, height, "setup")
        waypoints = [start]
        if animation.get("via"):
            guide = _primitive(working, animation["via"])
            if guide.get("type") not in {"line", "arrow"}:
                raise ContractError("move_radial_dot via must name a line or arrow")
            for point in (guide["start"], guide["end"]):
                waypoints.append((_number(point[0], beat) * width,
                                  _number(point[1], beat) * height))
        waypoints.append(end)
        segment = min(len(waypoints) - 2, int(progress * (len(waypoints) - 1)))
        local = progress * (len(waypoints) - 1) - segment
        x = waypoints[segment][0] * (1 - local) + waypoints[segment + 1][0] * local
        y = waypoints[segment][1] * (1 - local) + waypoints[segment + 1][1] * local
        radius = source.get("dot_px", 6)
        ImageDraw.Draw(image).ellipse((x - radius, y - radius, x + radius, y + radius),
                                      fill=source.get("color", "#14756f"))
        return image
    raise ContractError(f"unsupported contract animation type: {kind!r}")


def _checked_video(path: Path, expected: list[np.ndarray], motion_index: int, fps: int) -> dict:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ContractError(f"encoded video cannot be opened: {path}")
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = float(capture.get(cv2.CAP_PROP_FPS))
        if count != len(expected) or abs(actual_fps - fps) > 0.1:
            raise ContractError(f"encoded video metadata differs: {count} frames at {actual_fps} fps")
        errors = []
        for index, reference in enumerate(expected):
            ok, frame = capture.read()
            if not ok:
                raise ContractError(f"encoded video cannot decode frame {index}")
            errors.append(float(np.mean(cv2.absdiff(frame, reference))))
        worst_index = max(range(count), key=errors.__getitem__)
        if errors[worst_index] > 15:
            raise ContractError(f"encoded frame {worst_index} differs from checked state: {errors[worst_index]:.1f}")
        return {"frame_count": count, "fps": actual_fps,
                "duration_s": round(count / actual_fps, 3),
                "frames_checked": len(errors),
                "first_frame_mean_error": round(errors[0], 3),
                "motion_frame_mean_error": round(errors[motion_index], 3),
                "last_frame_mean_error": round(errors[-1], 3),
                "worst_frame_index": worst_index,
                "worst_frame_time_s": round(worst_index / actual_fps, 3),
                "worst_frame_mean_error": round(errors[worst_index], 3)}
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
    setup_frames = max(1, round(frame_count * 0.2))
    motion_frames = max(1, round(frame_count * 0.6))
    result_frames = frame_count - setup_frames - motion_frames
    if result_frames < 1:
        raise ContractError("video is too short for setup, motion and result")
    setup = cv2.cvtColor(np.asarray(render_first_frame(contract, width, height, "setup")),
                         cv2.COLOR_RGB2BGR)
    result = cv2.cvtColor(np.asarray(render_first_frame(contract, width, height, "result")),
                          cv2.COLOR_RGB2BGR)
    if np.array_equal(setup, result):
        raise ContractError("setup and result frames are identical")
    motion_steps = min(24, motion_frames)
    motion_cache = {}
    for step in range(motion_steps):
        progress = (step + 1) / motion_steps
        motion_cache[step] = cv2.cvtColor(
            np.asarray(_motion_image(contract, progress, width, height)), cv2.COLOR_RGB2BGR
        )
    if not any(not np.array_equal(frame, setup) and not np.array_equal(frame, result)
               for frame in motion_cache.values()):
        raise ContractError("animation has no visible intermediate teaching state")
    motion_index = setup_frames + motion_frames // 4
    expected_frames = ([setup] * setup_frames
                       + [motion_cache[min(motion_steps - 1, index * motion_steps // motion_frames)]
                          for index in range(motion_frames)]
                       + [result] * result_frames)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pending = out_path.with_name(out_path.stem + ".partial.mp4")
    writer = cv2.VideoWriter(str(pending), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))
    if not writer.isOpened():
        raise ContractError(f"MP4 encoder cannot open {pending}")
    try:
        for frame in expected_frames:
            writer.write(frame)
    finally:
        writer.release()
    try:
        inspection = _checked_video(pending, expected_frames, motion_index, fps)
        pending.replace(out_path)
    except Exception:
        pending.unlink(missing_ok=True)
        raise
    return {
        "id": case["id"], "video_path": str(out_path),
        "generation_mode": f"checked_contract_{contract['animation']['type']}_v2", "has_audio": False,
        "width": width, "height": height, "setup_frames": setup_frames,
        "motion_frames": motion_frames, "result_frames": result_frames,
        "contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "video_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        **inspection,
    }
