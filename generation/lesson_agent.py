"""Auditable teaching-video agent prototype. No model calls are made by default."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parent.parent


class VideoBackend(Protocol):
    def generate(self, shot: dict, output_dir: Path) -> dict: ...


class AudioBackend(Protocol):
    def generate(self, shot: dict, output_dir: Path) -> dict: ...


class TeachingPlanner:
    def plan(self, item: dict) -> dict:
        if item.get("task_type") not in {"explanation", "problem_solving"}:
            raise ValueError("task_type must be explanation or problem_solving")
        beats = item.get("expected_narrative_order") or [item["prompt_text"]]
        duration = float(item.get("target_duration_s") or 5)
        if duration <= 0:
            raise ValueError("target_duration_s must be positive")
        return {
            "case_id": item["id"], "discipline": item["discipline"],
            "task_type": item["task_type"], "duration_s": duration,
            "source_prompt": item["prompt_text"],
            "reference_facts": item.get("expected_concepts", []),
            "forbidden_errors": item.get("discipline_specific_rubric", []),
            "shots": [{
                "id": f"s{i+1}", "beat": beat, "duration_s": round(duration / len(beats), 3),
                "visual_evidence": item.get("expected_visual_elements", []),
                "narration": beat if item.get("audio_narration_required") else None,
                "first_frame": item.get("first_frame_path") if i == 0 else None,
                "generation_mode": "image_to_video" if i == 0 and item.get("first_frame_path") else "text_to_video",
            } for i, beat in enumerate(beats)],
        }


class ContractCritic:
    def check(self, plan: dict) -> list[str]:
        issues = []
        if not plan["reference_facts"]:
            issues.append("missing_reference_facts")
        if not plan["forbidden_errors"]:
            issues.append("missing_subject_rubric")
        for shot in plan["shots"]:
            frame = shot["first_frame"]
            if frame and not (ROOT / frame).is_file():
                issues.append(f"{shot['id']}:missing_first_frame")
        return issues


class LessonDirector:
    """Director owns state; specialist backends can be swapped without changing the contract."""

    def __init__(self, video: VideoBackend | None = None, audio: AudioBackend | None = None):
        self.video, self.audio = video, audio
        self.planner, self.critic = TeachingPlanner(), ContractCritic()

    def run(self, item: dict, output_dir: Path, execute: bool = False) -> dict:
        plan = self.planner.plan(item)
        issues = self.critic.check(plan)
        record = {"plan": plan, "preflight_issues": issues, "artifacts": []}
        if execute:
            if issues:
                raise ValueError(f"Preflight failed: {issues}")
            if self.video is None:
                raise ValueError("A video backend is required for execution")
            output_dir.mkdir(parents=True, exist_ok=True)
            for shot in plan["shots"]:
                artifacts = {"shot_id": shot["id"], "video": self.video.generate(shot, output_dir)}
                if shot["narration"]:
                    if self.audio is None:
                        raise ValueError("An audio backend is required for narrated shots")
                    artifacts["audio"] = self.audio.generate(shot, output_dir)
                record["artifacts"].append(artifacts)
        return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile one candidate into an agent execution plan")
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    item = next((json.loads(line) for line in args.prompts.open(encoding="utf-8")
                 if line.strip() and json.loads(line)["id"] == args.id), None)
    if item is None:
        parser.error(f"Unknown id: {args.id}")
    record = LessonDirector().run(item, args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
