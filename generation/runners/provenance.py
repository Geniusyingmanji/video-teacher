"""Input and artifact fingerprints for resumable video generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_sha256(case: dict, args: object, first_frame: Path | None = None) -> str:
    """Hash every input that can change the generated pixels or playback."""
    payload = {
        "generation_prompt": case.get("video_prompt", case["prompt_text"]),
        "teaching_contract_sha256": case.get("teaching_contract_sha256"),
        "model_path": str(Path(args.model_path).resolve()),
        "height": args.height,
        "width": args.width,
        "num_frames": args.num_frames,
        "steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "seed": args.seed,
        "fps": args.fps,
        "dtype": args.dtype,
        "first_frame_sha256": file_sha256(first_frame) if first_frame else None,
    }
    negative_prompt = getattr(args, "negative_prompt", "")
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def can_resume(record: dict, video_path: Path, fingerprint: str) -> bool:
    return (
        record.get("status") == "ok"
        and record.get("input_sha256") == fingerprint
        and isinstance(record.get("video_sha256"), str)
        and video_path.is_file()
        and file_sha256(video_path) == record["video_sha256"]
    )
