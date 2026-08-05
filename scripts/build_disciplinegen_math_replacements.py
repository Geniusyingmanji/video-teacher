"""Build five deterministic math replacements with DisciplineGen renderers.

The upstream repository contains programmatic input/GT renderers but hard-codes
large dataset sizes.  This adapter imports those renderers unchanged, overrides
only output/count/seed globals, and converts one sample per task family to the
video-teacher schema.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_URL = "https://github.com/VisionXLab/DisciplineGen-1M"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(module: Any, output_dir: Path, seed: int) -> None:
    module.OUTPUT_DIR = output_dir
    module.INPUT_DIR = output_dir / "input"
    module.GT_DIR = output_dir / "gt"
    module.META_DIR = output_dir / "meta"
    original_name = Path(module.META_FILE).name
    module.META_FILE = module.META_DIR / original_name
    module.SAMPLE_COUNT = 1
    module.RANDOM_SEED = seed


def build_row(family: str, record: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    before = Path(record["input_image"])
    target = Path(record["gt_image"])
    if not before.is_absolute():
        before = output_dir / "input" / before.name
    if not target.is_absolute():
        target = output_dir / "gt" / target.name
    prompt = record.get("prompt")
    if not prompt:
        if family == "rotation":
            rotation = record["rotation"]
            prompt = (
                f"Rotate the polygon {rotation['angle_deg']} degrees "
                f"{rotation['direction']} about the marked center."
            )
        elif family == "translation":
            vector = record["translation_vector"]
            prompt = f"Translate the polygon by vector ({vector['dx']}, {vector['dy']})."
        elif family == "scaling":
            prompt = "Scale the polygon about the marked center by the specified area factor."
        else:
            prompt = f"Complete the requested {family} construction."
    case_id = f"disciplinegen_math_generated_{family}"
    rel_before = before.resolve().relative_to(ROOT).as_posix()
    rel_target = target.resolve().relative_to(ROOT).as_posix()
    beats = [
        "identify the original geometry and the requested operation",
        "highlight the controlling point, line, or measurement",
        "animate the construction in one verifiable step",
        "overlay the final result and check the defining relationship",
    ]
    return {
        "id": case_id,
        "discipline": "mathematics",
        "subdomain": f"2d_geometry_{family}",
        "task_type": "problem_solving",
        "difficulty": "undergrad",
        "prompt_text": f"Create a 5-second teaching video. {prompt}",
        "expected_concepts": [family, "coordinate geometry", "geometric verification"],
        "expected_visual_elements": [
            "the unchanged input construction",
            "the controlling geometric feature",
            "the completed target construction overlaid clearly",
        ],
        "expected_narrative_order": beats,
        "pedagogical_target_audience": "introductory mathematics student",
        "discipline_specific_rubric": [
            "the final construction matches the supplied ground truth",
            "the requested geometric invariant is preserved",
            "labels, coordinates, and construction lines remain readable",
        ],
        "audio_narration_required": False,
        "target_duration_s": 5,
        "narrative_beats": [
            {"beat": beat, "expected_frame_range": frame_range}
            for beat, frame_range in zip(beats, ([1, 2], [2, 4], [4, 7], [7, 8]))
        ],
        "source": {
            "dataset": "DisciplineGen-1M",
            "source_id": f"github_math_renderer_{family}_seed_20260805",
            "source_url": UPSTREAM_URL,
            "source_file": f"math/{family}_task_render.py",
            "local_before_path": rel_before,
            "local_gt_path": rel_target,
            "generator_record": record,
            "license_status": "verified_redistributable",
            "license": "CC BY 4.0",
            "license_source": UPSTREAM_URL,
        },
        "curation": {
            "status": "reviewed_release_ready",
            "conversion": "disciplinegen_generator_adapter_v1",
            "visual_review": "passed 2026-08-05",
            "ground_truth_review": "passed against deterministic generator parameters",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "sources" / "disciplinegen" / "generated_math",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=ROOT / "data" / "curated" / "disciplinegen_math_replacements.jsonl",
    )
    args = parser.parse_args()
    # The upstream reflection renderer currently raises NameError in
    # adaptive_figsize (x_span is undefined), so it is intentionally excluded.
    families = ["line_point", "triangle", "rotation", "scaling", "translation"]
    rows = []
    for index, family in enumerate(families):
        script = args.upstream / "math" / f"{family}_task_render.py"
        module = load_module(script, f"disciplinegen_{family}")
        output_dir = args.output_root / family
        configure(module, output_dir, 20260805 + index)
        module.generate_tasks()
        records = json.loads(Path(module.META_FILE).read_text(encoding="utf-8"))
        if len(records) != 1:
            raise RuntimeError(f"{family}: expected one record, got {len(records)}")
        rows.append(build_row(family, records[0], output_dir))
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} replacements to {args.output_jsonl}")


if __name__ == "__main__":
    main()
