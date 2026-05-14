"""Migrate pilot_v0_1.jsonl → pilot_v0_2.jsonl with schema updates:

  - difficulty: k12→low, undergrad→medium, professional→high
  - add `target_duration_s`: 5 (our 5s rerun target)
  - add `narrative_beats`: same content as expected_narrative_order but
    structured as [{beat, approx_frame_range}] for richer eval
  - add `difficulty_rationale`: brief text explaining why this difficulty level

Run:
    python scripts/migrate_to_v0_2.py
Writes:
    data/prompts/pilot_v0_2.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path

DIFF_MAP = {"k12": "low", "undergrad": "medium", "professional": "high"}

# Duration hint per target: 5s @ 24fps = 121 frames, sample 8 → every ~15f
# We tag each beat with a rough fraction of the video
def beats_to_timed(beats: list[str], n_beats: int) -> list[dict]:
    out = []
    for i, b in enumerate(beats):
        start_frac = i / max(n_beats, 1)
        end_frac = (i + 1) / max(n_beats, 1)
        # Map to 8-frame grid (frames 1-8)
        start_frame = max(1, round(start_frac * 7 + 1))
        end_frame = min(8, round(end_frac * 7 + 1))
        out.append({
            "beat": b,
            "expected_frame_range": [start_frame, end_frame],
        })
    return out


def migrate(src: str, addon: str | None, dst: str) -> None:
    cases = []
    with open(src) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            old_diff = c.get("difficulty", "undergrad")
            new_diff = DIFF_MAP.get(old_diff, "medium")
            order = c.get("expected_narrative_order", [])
            c2 = dict(c)
            c2["difficulty"] = new_diff
            c2["difficulty_v0_1"] = old_diff
            c2["target_duration_s"] = 5
            c2["narrative_beats"] = beats_to_timed(order, len(order))
            cases.append(c2)

    if addon and Path(addon).exists():
        with open(addon) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                old_diff = c.get("difficulty", "professional")
                new_diff = DIFF_MAP.get(old_diff, "high")
                order = c.get("expected_narrative_order", [])
                c2 = dict(c)
                c2["difficulty"] = new_diff
                c2["difficulty_v0_1"] = old_diff
                c2["target_duration_s"] = 5
                c2["narrative_beats"] = beats_to_timed(order, len(order))
                cases.append(c2)
        print(f"  merged addon from {addon}")

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Migrated {len(cases)} cases → {dst}")


if __name__ == "__main__":
    src = "data/prompts/pilot_v0_1.jsonl"
    addon = "data/prompts/high_difficulty_addon.jsonl"
    dst = "data/prompts/pilot_v0_2.jsonl"
    migrate(src, addon, dst)
