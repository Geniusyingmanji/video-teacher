"""Long-running first-frame-first data construction for rise-teacher.

The script loops over generate -> critique -> accept/reject. It is intended for
overnight candidate construction, not direct promotion into pilot files.

Outputs live under data/prompts/longrun_<prefix>/:
  - raw.jsonl: every generated candidate
  - accepted.jsonl: schema-valid, judge-accepted candidates
  - rejected.jsonl: candidates with review issues
  - progress.jsonl: per-batch status
  - status.json: latest summary for monitoring
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.judges.gpt55 import chat


ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT / "data" / "prompts"

DISCIPLINES = [
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "medicine",
    "computer_science",
    "economics",
    "civics",
    "language_literature",
    "history",
    "geography",
    "art_music",
]

REQUIRED_FIELDS = [
    "id",
    "discipline",
    "subdomain",
    "task_type",
    "difficulty",
    "prompt_text",
    "expected_concepts",
    "expected_visual_elements",
    "expected_narrative_order",
    "pedagogical_target_audience",
    "discipline_specific_rubric",
    "audio_narration_required",
    "first_frame",
]

FOCUS_PLAN = [
    {
        "name": "medicine_low_medium",
        "disciplines": ["medicine", "biology", "chemistry"],
        "task_mix": "balanced explanation and problem_solving",
        "difficulty": ["k12", "undergrad", "professional"],
        "need": "fill medicine low/medium gaps and medically useful visual mechanisms",
    },
    {
        "name": "cs_low_accessible",
        "disciplines": ["computer_science", "mathematics"],
        "task_mix": "mostly k12/undergrad problem_solving",
        "difficulty": ["k12", "undergrad"],
        "need": "intro computer science cases with concrete diagrams, tables, or code traces",
    },
    {
        "name": "humanities_problem_solving",
        "disciplines": ["history", "civics", "language_literature", "art_music"],
        "task_mix": "mostly problem_solving",
        "difficulty": ["k12", "undergrad", "professional"],
        "need": "humanities/social-science worked analyses that have visual evidence and stepwise reasoning",
    },
    {
        "name": "social_science_visual",
        "disciplines": ["economics", "geography", "civics"],
        "task_mix": "balanced explanation and problem_solving",
        "difficulty": ["k12", "undergrad", "professional"],
        "need": "charts, maps, timelines, and policy diagrams with unambiguous first frames",
    },
    {
        "name": "high_difficulty_visualizable",
        "disciplines": ["mathematics", "physics", "chemistry", "computer_science", "economics"],
        "task_mix": "balanced, but only if the first frame can be visually judged",
        "difficulty": ["professional"],
        "need": "graduate/professional cases where CC and NS can be judged from frames",
    },
]


GEN_SYSTEM = """You construct benchmark data for rise-teacher, a pixel-level T2V
educational-video benchmark. Quality is more important than quantity.

Hard rule: design the first frame first. A case is useful only if its opening
frame can look like a real teaching-video start:
- explanation: clean concept setup diagram, accurate labels/arrows, low clutter.
- problem_solving: problem statement + known quantities + blank/early workspace,
  not a page of final answers unless the first_frame spec explicitly says why.
- no illegible text, wrong formulas, decorative posters, generic classrooms, or
  images that are only exam screenshots.

Return only a JSON array. Do not wrap it in markdown."""


REVIEW_SYSTEM = """You are a strict rise-teacher data critic. Judge whether each
candidate should enter an accepted candidate pool. Reject cases that are hard to
render as a first frame, duplicate existing topics, visually untestable, too
abstract for 5 seconds, or likely to cause wrong/illegible text.

Return only a JSON array of review objects:
{
  "id": "...",
  "verdict": "ACCEPT" or "REJECT",
  "first_frame_score": 1-5,
  "visual_evaluability_score": 1-5,
  "pedagogy_score": 1-5,
  "schema_score": 1-5,
  "issues": ["..."],
  "fix": "..."
}
Do not wrap it in markdown."""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def extract_json_array(raw: str) -> list[Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        raise ValueError(f"no JSON array found in response: {raw[:200]!r}")
    return json.loads(text[start:end + 1])


def normalize_id(text: str, used_ids: set[str], prefix: str, idx: int) -> str:
    base = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")
    base = re.sub(r"_+", "_", base)[:48] or f"{prefix}_{idx:05d}"
    if not base.startswith(prefix):
        base = f"{prefix}_{base}"
    cid = base
    n = 2
    while cid in used_ids:
        cid = f"{base}_{n}"
        n += 1
    used_ids.add(cid)
    return cid


def beats_to_timed(beats: list[str]) -> list[dict[str, Any]]:
    out = []
    n = max(len(beats), 1)
    for i, beat in enumerate(beats):
        start = max(1, round((i / n) * 7 + 1))
        end = min(8, round(((i + 1) / n) * 7 + 1))
        out.append({"beat": str(beat), "expected_frame_range": [start, end]})
    return out


def deterministic_issues(case: dict[str, Any], used_ids: set[str]) -> list[str]:
    issues = []
    for field in REQUIRED_FIELDS:
        if field not in case:
            issues.append(f"missing field: {field}")
    if case.get("discipline") not in DISCIPLINES:
        issues.append("discipline is outside frozen 12-discipline scope")
    if case.get("task_type") not in {"explanation", "problem_solving"}:
        issues.append("invalid task_type")
    if case.get("difficulty") not in {"k12", "undergrad", "professional"}:
        issues.append("invalid difficulty")
    for field in [
        "expected_concepts",
        "expected_visual_elements",
        "expected_narrative_order",
        "discipline_specific_rubric",
    ]:
        if not isinstance(case.get(field), list) or len(case.get(field) or []) < 3:
            issues.append(f"{field} must be a list with at least 3 items")
    ff = case.get("first_frame")
    if not isinstance(ff, dict):
        issues.append("first_frame must be an object")
    else:
        if not str(ff.get("prompt", "")).strip():
            issues.append("first_frame.prompt is empty")
        for field in ["must_include", "avoid", "quality_checks"]:
            if not isinstance(ff.get(field), list) or len(ff.get(field) or []) < 3:
                issues.append(f"first_frame.{field} must have at least 3 items")
    cid = str(case.get("id", ""))
    if cid in used_ids:
        issues.append("duplicate id")
    return issues


def build_generation_prompt(
    focus: dict[str, Any],
    batch_size: int,
    existing_summary: str,
    next_index: int,
    prefix: str,
) -> str:
    return f"""
Generate {batch_size} new rise-teacher candidate cases.

Focus slice: {focus['name']}
Need: {focus['need']}
Allowed disciplines: {focus['disciplines']}
Task mix: {focus['task_mix']}
Allowed difficulties: {focus['difficulty']}
ID format: start ids with "{prefix}_" and use readable lowercase names. Next index hint: {next_index}.

Avoid close duplicates of these existing topics:
{existing_summary}

Each case must use this schema:
{{
  "id": "...",
  "discipline": one of the allowed disciplines,
  "subdomain": "...",
  "task_type": "explanation" or "problem_solving",
  "difficulty": "k12" or "undergrad" or "professional",
  "prompt_text": "Generate a 5-second educational video ...",
  "expected_concepts": ["...", "...", "..."],
  "expected_visual_elements": ["...", "...", "..."],
  "expected_narrative_order": ["...", "...", "...", "..."],
  "pedagogical_target_audience": "...",
  "discipline_specific_rubric": ["...", "...", "..."],
  "audio_narration_required": false,
  "first_frame": {{
    "type": "diagram_opening_frame" or "worked_problem_opening_frame",
    "prompt": "specific 16:9 opening-frame spec",
    "must_include": ["...", "...", "..."],
    "avoid": ["...", "...", "..."],
    "quality_checks": ["...", "...", "..."]
  }},
  "metadata": {{
    "source": "long_data_construction",
    "focus": "{focus['name']}",
    "first_frame_priority": "high"
  }}
}}

Quality bar:
- first_frame.prompt must be concrete enough for an image generator.
- prefer diagrams, graphs, maps, timelines, labeled mechanisms, code traces,
  tables, whiteboards, or medical illustrations.
- 5-second narrative order must be 4-6 short beats.
- problem_solving must have an unambiguous final answer in the rubric, but the
  first frame should emphasize setup unless showing the final answer is essential.
"""


def build_review_prompt(cases: list[dict[str, Any]], existing_summary: str) -> str:
    compact = []
    for c in cases:
        compact.append({
            "id": c.get("id"),
            "discipline": c.get("discipline"),
            "subdomain": c.get("subdomain"),
            "task_type": c.get("task_type"),
            "difficulty": c.get("difficulty"),
            "prompt_text": c.get("prompt_text"),
            "expected_concepts": c.get("expected_concepts"),
            "expected_visual_elements": c.get("expected_visual_elements"),
            "expected_narrative_order": c.get("expected_narrative_order"),
            "rubric": c.get("discipline_specific_rubric"),
            "first_frame": c.get("first_frame"),
        })
    return (
        "Existing topics to avoid near-duplicates:\n"
        + existing_summary
        + "\n\nReview these candidates:\n"
        + json.dumps(compact, ensure_ascii=False)
    )


def summarize_existing(rows: list[dict[str, Any]], accepted: list[dict[str, Any]]) -> str:
    all_rows = rows + accepted
    samples = []
    for row in all_rows[-160:]:
        samples.append(
            f"- {row.get('discipline')} / {row.get('task_type')} / "
            f"{row.get('subdomain')}: {str(row.get('expected_concepts', []))[:120]}"
        )
    return "\n".join(samples[-120:])


def prepare_case(
    case: dict[str, Any],
    used_ids: set[str],
    prefix: str,
    next_index: int,
    focus_name: str,
) -> dict[str, Any]:
    c = dict(case)
    c["id"] = normalize_id(str(c.get("id", f"{prefix}_{next_index:05d}")), used_ids, prefix, next_index)
    c["audio_narration_required"] = bool(c.get("audio_narration_required", False))
    beats = [str(x) for x in c.get("expected_narrative_order", [])]
    c["difficulty_v0_1"] = c.get("difficulty")
    c["target_duration_s"] = int(c.get("target_duration_s") or 5)
    c["narrative_beats"] = beats_to_timed(beats)
    md = dict(c.get("metadata") or {})
    md.update({
        "source": "long_data_construction",
        "focus": focus_name,
        "first_frame_priority": "high",
    })
    c["metadata"] = md
    return c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default=time.strftime("long_%Y%m%d_%H%M%S"))
    ap.add_argument("--duration-hours", type=float, default=9.0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-accepted", type=int, default=300)
    ap.add_argument("--sleep-seconds", type=float, default=20.0)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--max-batches", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    out_dir = PROMPT_DIR / f"longrun_{args.prefix}"
    raw_path = out_dir / "raw.jsonl"
    accepted_path = out_dir / "accepted.jsonl"
    rejected_path = out_dir / "rejected.jsonl"
    progress_path = out_dir / "progress.jsonl"
    status_path = out_dir / "status.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    base_rows = []
    base_paths = [
        PROMPT_DIR / "pilot_v0_1.jsonl",
        PROMPT_DIR / "pilot_v0_2.jsonl",
        PROMPT_DIR / "high_difficulty_addon.jsonl",
    ]
    base_paths.extend(sorted(PROMPT_DIR.glob("candidates_subagent_*.jsonl")))
    base_paths.extend(
        p for p in sorted(PROMPT_DIR.glob("longrun_*/accepted.jsonl"))
        if p.resolve() != accepted_path.resolve()
    )
    for path in base_paths:
        base_rows.extend(load_jsonl(path))

    accepted_rows = load_jsonl(accepted_path)
    raw_rows = load_jsonl(raw_path)
    rejected_rows = load_jsonl(rejected_path)
    used_ids = {str(r.get("id")) for r in base_rows + accepted_rows + raw_rows if r.get("id")}

    start = time.time()
    deadline = start + max(args.duration_hours, 0.0) * 3600.0
    batch_idx = 0
    next_index = len(raw_rows) + 1

    while time.time() < deadline and len(accepted_rows) < args.max_accepted:
        if args.max_batches and batch_idx >= args.max_batches:
            break
        focus = FOCUS_PLAN[batch_idx % len(FOCUS_PLAN)]
        existing_summary = summarize_existing(base_rows, accepted_rows)
        progress = {
            "event": "batch_start",
            "batch": batch_idx,
            "focus": focus["name"],
            "accepted_total": len(accepted_rows),
            "raw_total": len(raw_rows),
            "rejected_total": len(rejected_rows),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        append_jsonl(progress_path, [progress])
        print(f"[long-data] batch {batch_idx} focus={focus['name']} accepted={len(accepted_rows)}", flush=True)

        try:
            gen_raw = chat(
                [
                    {"role": "system", "content": GEN_SYSTEM},
                    {"role": "user", "content": build_generation_prompt(
                        focus, args.batch_size, existing_summary, next_index, args.prefix
                    )},
                ],
                model=args.model,
                max_tokens=12000,
            )
            generated = extract_json_array(gen_raw)
            generated = [x for x in generated if isinstance(x, dict)]
        except Exception as exc:
            append_jsonl(progress_path, [{
                "event": "generation_error",
                "batch": batch_idx,
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            }])
            print(f"[long-data] generation error: {exc}", flush=True)
            time.sleep(args.sleep_seconds)
            batch_idx += 1
            continue

        prepared = []
        local_rejects = []
        for row in generated:
            case = prepare_case(row, used_ids, args.prefix, next_index, focus["name"])
            next_index += 1
            issues = deterministic_issues(case, set())
            if issues:
                reject = dict(case)
                reject["review"] = {
                    "verdict": "REJECT",
                    "issues": issues,
                    "fix": "failed deterministic schema validation",
                }
                local_rejects.append(reject)
            else:
                prepared.append(case)

        if prepared:
            append_jsonl(raw_path, prepared)
            raw_rows.extend(prepared)

        if local_rejects:
            append_jsonl(rejected_path, local_rejects)
            rejected_rows.extend(local_rejects)

        reviews_by_id: dict[str, dict[str, Any]] = {}
        if prepared:
            try:
                review_raw = chat(
                    [
                        {"role": "system", "content": REVIEW_SYSTEM},
                        {"role": "user", "content": build_review_prompt(prepared, existing_summary)},
                    ],
                    model=args.model,
                    max_tokens=8000,
                )
                reviews = extract_json_array(review_raw)
                reviews_by_id = {
                    str(r.get("id")): r for r in reviews
                    if isinstance(r, dict) and r.get("id")
                }
            except Exception as exc:
                append_jsonl(progress_path, [{
                    "event": "review_error",
                    "batch": batch_idx,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                }])
                print(f"[long-data] review error: {exc}", flush=True)

        new_accepts = []
        new_rejects = []
        for case in prepared:
            review = reviews_by_id.get(case["id"], {
                "verdict": "REJECT",
                "issues": ["missing model review"],
                "fix": "rerun review",
            })
            scores = [
                int(review.get("first_frame_score") or 0),
                int(review.get("visual_evaluability_score") or 0),
                int(review.get("pedagogy_score") or 0),
                int(review.get("schema_score") or 0),
            ]
            row = dict(case)
            row["review"] = review
            if review.get("verdict") == "ACCEPT" and min(scores) >= 4:
                new_accepts.append(row)
            else:
                new_rejects.append(row)

        if new_accepts:
            append_jsonl(accepted_path, new_accepts)
            accepted_rows.extend(new_accepts)
        if new_rejects:
            append_jsonl(rejected_path, new_rejects)
            rejected_rows.extend(new_rejects)

        status = {
            "prefix": args.prefix,
            "out_dir": str(out_dir),
            "duration_hours": args.duration_hours,
            "elapsed_minutes": round((time.time() - start) / 60.0, 2),
            "batch": batch_idx,
            "accepted": len(accepted_rows),
            "raw": len(raw_rows),
            "rejected": len(rejected_rows),
            "accepted_by_discipline": dict(Counter(r.get("discipline") for r in accepted_rows)),
            "accepted_by_task_type": dict(Counter(r.get("task_type") for r in accepted_rows)),
            "accepted_by_difficulty": dict(Counter(r.get("difficulty") for r in accepted_rows)),
            "last_focus": focus["name"],
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        write_json(status_path, status)
        append_jsonl(progress_path, [{
            "event": "batch_done",
            "batch": batch_idx,
            "generated": len(generated),
            "prepared": len(prepared),
            "accepted": len(new_accepts),
            "rejected": len(new_rejects) + len(local_rejects),
            "accepted_total": len(accepted_rows),
            "elapsed_minutes": status["elapsed_minutes"],
        }])
        print(
            f"[long-data] batch {batch_idx} done: +{len(new_accepts)} accepted, "
            f"+{len(new_rejects) + len(local_rejects)} rejected; total={len(accepted_rows)}",
            flush=True,
        )

        batch_idx += 1
        if time.time() < deadline and len(accepted_rows) < args.max_accepted:
            time.sleep(args.sleep_seconds)

    write_json(status_path, {
        "prefix": args.prefix,
        "out_dir": str(out_dir),
        "elapsed_minutes": round((time.time() - start) / 60.0, 2),
        "batches": batch_idx,
        "accepted": len(accepted_rows),
        "raw": len(raw_rows),
        "rejected": len(rejected_rows),
        "accepted_by_discipline": dict(Counter(r.get("discipline") for r in accepted_rows)),
        "accepted_by_task_type": dict(Counter(r.get("task_type") for r in accepted_rows)),
        "accepted_by_difficulty": dict(Counter(r.get("difficulty") for r in accepted_rows)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    print(f"[long-data] finished. accepted={len(accepted_rows)} out_dir={out_dir}", flush=True)


if __name__ == "__main__":
    main()
