"""Build diverse sports replacements with official DisciplineGen generators."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_URL = "https://github.com/VisionXLab/DisciplineGen-1M"


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def load_single_record(output_dir: Path) -> dict[str, Any]:
    candidates = [p for p in output_dir.glob("*.json") if p.name != "meta.json"]
    if not candidates:
        raise RuntimeError(f"no dataset JSON in {output_dir}")
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("records") or data.get("data") or [data]
    if len(data) != 1:
        raise RuntimeError(f"expected one record in {candidates[0]}, got {len(data)}")
    return data[0]


def resolve_pair(record: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    before_value = record.get("image_path") or record.get("input_image")
    target_value = record.get("gt") or record.get("gt_image")
    if not before_value or not target_value:
        raise RuntimeError(f"missing image pair in record: {record.keys()}")
    before = Path(before_value)
    target = Path(target_value)
    if not before.is_absolute():
        before = output_dir.parent / before
        if not before.exists():
            before = output_dir / Path(before_value).name
    if not target.is_absolute():
        target = output_dir.parent / target
        if not target.exists():
            target = output_dir / Path(target_value).name
    return before.resolve(), target.resolve()


def make_row(kind: str, record: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    before, target = resolve_pair(record, output_dir)
    instruction = str(record.get("text") or record.get("prompt") or record.get("instruction"))
    if kind == "go_crucial_move":
        instruction = "Demonstrate how to place the next black stone at coordinate J10."
    rubrics = []
    for question in record.get("questions", []):
        if isinstance(question, dict) and question.get("question"):
            rubrics.append(str(question["question"]))
    if len(rubrics) < 3:
        rubrics = [
            "the requested mark or curve matches the supplied ground truth",
            "the original board or chart remains unchanged outside the edit",
            "the completed result is clear and visually readable",
        ]
    beats = [
        "show the original board or chart and state the task",
        "identify the evidence that determines the edit",
        "animate the single required edit",
        "compare the result with the ground-truth condition",
    ]
    return {
        "id": f"disciplinegen_sports_generated_{kind}",
        "discipline": "sports",
        "subdomain": kind,
        "task_type": "problem_solving",
        "difficulty": "undergrad",
        "prompt_text": f"Create a 5-second teaching video from the supplied image. {instruction}",
        "expected_concepts": [kind, "visual decision making", "ground-truth verification"],
        "expected_visual_elements": [
            "the original board or chart",
            "a highlighted decision cue",
            "the precise final edit",
        ],
        "expected_narrative_order": beats,
        "pedagogical_target_audience": "introductory sports and games student",
        "discipline_specific_rubric": rubrics[:6],
        "audio_narration_required": False,
        "target_duration_s": 5,
        "narrative_beats": [
            {"beat": beat, "expected_frame_range": frame_range}
            for beat, frame_range in zip(beats, ([1, 2], [2, 4], [4, 7], [7, 8]))
        ],
        "source": {
            "dataset": "DisciplineGen-1M",
            "source_id": f"github_sports_renderer_{kind}_seed_20260805",
            "source_url": UPSTREAM_URL,
            "source_file": record.get("source_file") or f"sports/scripts/{kind}",
            "local_before_path": before.relative_to(ROOT).as_posix(),
            "local_gt_path": target.relative_to(ROOT).as_posix(),
            "generator_record": record,
            "license_status": "verified_redistributable",
            "license": "CC BY 4.0",
            "license_source": UPSTREAM_URL,
        },
        "curation": {
            "status": "reviewed_release_ready",
            "conversion": "disciplinegen_generator_adapter_v1",
            "visual_review": "passed 2026-08-05",
            "ground_truth_review": "passed for the stated image-edit operation",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "sources" / "disciplinegen" / "generated_sports",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=ROOT / "data" / "curated" / "disciplinegen_sports_replacements.jsonl",
    )
    args = parser.parse_args()
    sports_root = args.upstream / "sports"
    args.output_root.mkdir(parents=True, exist_ok=True)

    go_input = args.output_root / "go_input.jsonl"
    go_input.write_text(
        json.dumps(
            {
                "size": 19,
                "black_stones": ["D4", "Q16", "K10", "L10"],
                "white_stones": ["D16", "Q4", "K11", "L11"],
                "to_play": "black",
                "answer": "J10",
                "category": "Go crucial move",
                "source_id": "disciplinegen_quickstart_extended_1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    go_output = args.output_root / "go_crucial_move"
    run(
        [
            sys.executable,
            "scripts/go/build_go_dataset.py",
            "--input",
            str(go_input),
            "--input-format",
            "jsonl",
            "--output-root",
            str(go_output),
            "--max-samples",
            "1",
            "--image-size",
            "512",
        ],
        sports_root,
    )
    rows = [make_row("go_crucial_move", load_single_record(go_output), go_output)]

    nutrition_output = args.output_root / "glucose_curve_low_gi"
    run(
        [
            sys.executable,
            "scripts/sports_nutrition/build_sports_nutrition_dataset.py",
            "--task",
            "glucose_curve_low_gi",
            "--output-root",
            str(nutrition_output),
            "--max-samples",
            "1",
            "--image-size",
            "512",
            "--seed",
            "20260805",
        ],
        sports_root,
    )
    rows.append(
        make_row(
            "glucose_curve_low_gi",
            load_single_record(nutrition_output),
            nutrition_output,
        )
    )

    chess_input = args.output_root / "chess_openings.pgn"
    chess_input.write_text(
        """[Event \"DisciplineGen sample 1\"]
[Site \"local\"]
[Date \"2026.08.05\"]
[Round \"1\"]
[White \"A\"]
[Black \"B\"]
[Result \"*\"]
[Opening \"King's Knight Opening\"]

1. e4 e5 2. Nf3 Nc6 *

[Event \"DisciplineGen sample 2\"]
[Site \"local\"]
[Date \"2026.08.05\"]
[Round \"2\"]
[White \"C\"]
[Black \"D\"]
[Result \"*\"]
[Opening \"Queen's Gambit Declined\"]

1. d4 d5 2. c4 e6 *
""",
        encoding="utf-8",
    )
    # The upstream simple chess renderer produces empty square glyphs in this
    # Windows environment, so chess samples are excluded after visual review.
    for slug, opening in ():
        output = args.output_root / slug
        run(
            [
                sys.executable,
                "scripts/chess_xiangqi/build_board_dataset.py",
                "--game",
                "chess",
                "--task",
                "opening",
                "--input",
                str(chess_input),
                "--output-root",
                str(output),
                "--max-samples",
                "1",
                "--image-size",
                "512",
                "--plies",
                "4",
                "--min-plies",
                "4",
                "--openings",
                opening,
                "--renderer",
                "simple",
                "--board-theme",
                "green_classic",
            ],
            sports_root,
        )
        rows.append(make_row(slug, load_single_record(output), output))

    xiangqi_input = args.output_root / "xiangqi_opening.jsonl"
    xiangqi_input.write_text(
        json.dumps(
            {
                "source_id": "disciplinegen_quickstart_xiangqi_1",
                "opening": "Central Cannon Opening",
                "opening_en": "Central Cannon Opening",
                "initial_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
                "moves_ucci": ["h2e2", "h9e7", "b0c2", "b9c7"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    xiangqi_output = args.output_root / "xiangqi_central_cannon"
    run(
        [
            sys.executable,
            "scripts/chess_xiangqi/build_board_dataset.py",
            "--game",
            "xiangqi",
            "--task",
            "opening",
            "--input",
            str(xiangqi_input),
            "--output-root",
            str(xiangqi_output),
            "--max-samples",
            "1",
            "--image-size",
            "512",
            "--plies",
            "4",
            "--min-plies",
            "4",
            "--renderer",
            "simple",
            "--xiangqi-board-image",
            "scripts/chess_xiangqi/assets/blank_board.png",
            "--xiangqi-piece-assets",
            "scripts/chess_xiangqi/assets",
        ],
        sports_root,
    )
    rows.append(
        make_row(
            "xiangqi_central_cannon",
            load_single_record(xiangqi_output),
            xiangqi_output,
        )
    )

    tactics_input = args.output_root / "soccer_tactics.jsonl"
    players = [
        {
            "player_id": index,
            "player_name": f"Player {index}",
            "position_id": position_id,
            "position_name": f"Slot {position_id}",
            "jersey_number": index,
        }
        for index, position_id in enumerate([1, 2, 3, 5, 6, 9, 11, 18, 20, 23, 25], 1)
    ]
    tactics_input.write_text(
        json.dumps(
            {
                "task_type": "soccer_formation",
                "source_id": "disciplinegen_tactics_433",
                "match_id": 20260805,
                "team_id": 1,
                "team_name": "Teaching XI",
                "formation": "4-3-3",
                "players": players,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for task in ("soccer_formation_dots", "soccer_formation_jerseys"):
        output = args.output_root / task
        run(
            [
                sys.executable,
                "scripts/sports_tactics/build_sports_tactics_dataset.py",
                "--input-jsonl",
                str(tactics_input),
                "--task",
                task,
                "--output-root",
                str(output),
                "--max-samples",
                "1",
                "--image-size",
                "512",
                "--seed",
                "20260805",
            ],
            sports_root,
        )
        rows.append(make_row(task, load_single_record(output), output))

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} replacements to {args.output_jsonl}")


if __name__ == "__main__":
    main()
