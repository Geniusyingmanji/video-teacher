"""Use GPT-5.5 vision to pick the best MMMU candidate per rise-teacher case.

For each case (with K candidates from match_mmmu_candidates.py), sends the case
spec + all K candidate images to GPT-5.5 and asks it to pick the best fit as an
opening frame, or reject all if none work.

Usage:
    python scripts/select_mmmu_best.py \\
        --candidates data/first_frames_mmmu/candidates.jsonl \\
        --mmmu-root /data/zyf/datasets/mmmu \\
        --out data/first_frames_mmmu/selections.jsonl
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.judges.gpt55 import chat


SYSTEM_PROMPT = """You are selecting an opening frame for a short educational video.

You will receive:
1. The case spec: discipline, difficulty, concepts to teach, expected visual elements, prompt text.
2. K candidate images, each labeled CANDIDATE 0..K-1, with metadata.

These candidates come from existing educational benchmark datasets. They will NOT
match the exact concept perfectly — your job is to pick the candidate that is the
CLOSEST FIT TOPICALLY, even if it covers a related/adjacent topic in the same
discipline. A useful opening frame:
- Is in the same broad subject area (e.g., the case is about cells → any biology
  cell-related diagram, not necessarily the exact organelle)
- Looks clean and readable as a static starting visual
- Avoids spoiling the video's answer

ONLY return best = -1 if every candidate is from a clearly different discipline
or topic family. Lean toward picking the closest match — a topically-related
opening frame is better than nothing for our use case.

Return JSON:
{
  "best": <integer index 0..K-1, or -1 if all are clearly off-topic discipline-wise>,
  "reason": "<one sentence>",
  "ranking": [<list of indices, best first>]
}"""


def _b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def select_one(case_row: dict, mmmu_root: Path | None) -> dict:
    case_id = case_row["case_id"]
    candidates = case_row["candidates"]

    text_lines = [
        f"CASE: {case_id}",
        f"discipline: {case_row['discipline']}",
        f"difficulty: {case_row.get('difficulty')}",
        f"concepts to teach: {case_row.get('concepts')}",
        "",
        f"There are {len(candidates)} candidate images below.",
        "",
    ]
    for i, c in enumerate(candidates):
        text_lines.append(
            f"CANDIDATE {i}: subject={c['subject']}, subfield={c.get('subfield')}, "
            f"img_type={c.get('img_type')}, difficulty={c.get('topic_difficulty')}, "
            f"q_excerpt={c.get('question','')[:120]}"
        )

    user_content: list[dict] = [{"type": "text", "text": "\n".join(text_lines)}]
    for i, c in enumerate(candidates):
        # image_path may be absolute (cross-source) or relative to mmmu_root
        p = Path(c["image_path"])
        img_path = p if p.is_absolute() else (mmmu_root / p if mmmu_root else p)
        if not img_path.exists():
            continue
        user_content.append({"type": "text", "text": f"\n--- CANDIDATE {i} image ---"})
        user_content.append({"type": "image_url", "image_url": {
            "url": f"data:image/png;base64,{_b64(img_path)}",
            "detail": "low",  # save tokens — first-frame fit is gross-level
        }})

    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except Exception:
        return {"best": -1, "reason": f"parse_error: {raw[:160]}", "ranking": []}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--mmmu-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.candidates) if l.strip()]
    if args.limit > 0:
        rows = rows[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mmmu_root = Path(args.mmmu_root)

    # Resume
    done_ids = set()
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["case_id"])
                except Exception:
                    pass

    n_pick = n_reject = 0
    with out_path.open("a") as out_f:
        for i, row in enumerate(rows):
            cid = row["case_id"]
            if cid in done_ids:
                continue
            try:
                sel = select_one(row, mmmu_root)
            except Exception as e:
                sel = {"best": -1, "reason": f"exception: {type(e).__name__}: {e}",
                       "ranking": []}
            best = sel.get("best", -1)
            if best is not None and best >= 0 and best < len(row["candidates"]):
                chosen = row["candidates"][best]
                sel["chosen_image_path"] = chosen["image_path"]
                sel["chosen_subject"] = chosen["subject"]
                n_pick += 1
                marker = f"PICK#{best}"
            else:
                n_reject += 1
                marker = "REJECT"
            sel["case_id"] = cid
            out_f.write(json.dumps(sel, ensure_ascii=False) + "\n")
            out_f.flush()
            reason = (sel.get("reason") or "")[:80]
            print(f"[{i+1}/{len(rows)}] {cid}: {marker} — {reason}")
    print(f"\n[select] DONE — {n_pick} pick, {n_reject} reject")


if __name__ == "__main__":
    main()
