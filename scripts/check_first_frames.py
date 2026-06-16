"""Check first-frame images against case requirements using GPT-5.5 vision.

For each case, sends the first-frame image + case metadata to GPT-5.5 and asks
whether the image is suitable as an opening frame for the educational video.
Outputs a pass/fail verdict + suggestions for regeneration.

Usage:
    python scripts/check_first_frames.py \
        --prompts data/prompts/pilot_v0_1.jsonl \
        --first-frames data/first_frames \
        --out data/first_frames/check_report.jsonl
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.judges.gpt55 import chat


SYSTEM_PROMPT = """You are evaluating whether a generated image is suitable as the OPENING FRAME
of an educational video. You will receive:
1. The image
2. The video prompt (what the video should teach)
3. The expected visual elements
4. The discipline and difficulty level

Judge the image on these criteria:
1. RELEVANCE: Does it depict the right topic/subject?
2. VISUAL ELEMENTS: Are the expected elements present or at least suggested?
3. EDUCATIONAL QUALITY: Would this work as a clean starting point for a teaching video?
4. TECHNICAL QUALITY: Is it sharp, well-composed, free of artifacts?

Return JSON:
{
    "verdict": "PASS" or "FAIL",
    "relevance_score": 1-5,
    "elements_score": 1-5,
    "educational_score": 1-5,
    "technical_score": 1-5,
    "issues": ["list of specific problems, if any"],
    "suggestion": "what to change if FAIL, or empty string if PASS"
}

Be strict but fair. PASS means the image is usable as-is. FAIL means it needs
regeneration. Minor imperfections are OK for PASS."""


def check_image(case: dict, image_path: str) -> dict:
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    first_frame_spec = case.get("first_frame") or case.get("first_frame_spec")
    first_frame_text = ""
    if first_frame_spec:
        first_frame_text = (
            f"\nFirst-frame specification: "
            f"{json.dumps(first_frame_spec, ensure_ascii=False)[:800]}"
        )

    user_content = [
        {"type": "text", "text": (
            f"Case: {case['id']} — {case['discipline']} ({case['task_type']}, {case['difficulty']})\n"
            f"Video prompt: {case['prompt_text'][:300]}\n"
            f"Expected visual elements: {case.get('expected_visual_elements', [])}\n"
            f"Expected concepts: {case.get('expected_concepts', [])}"
            f"{first_frame_text}\n\n"
            "Is this image suitable as the opening frame for this educational video?"
        )},
        {"type": "image_url", "image_url": {
            "url": f"data:image/png;base64,{img_b64}",
            "detail": "high",
        }},
    ]

    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except Exception:
        return {"verdict": "ERROR", "raw": raw[:300]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--first-frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    cases: list[dict] = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.limit > 0:
        cases = cases[:args.limit]

    ff_dir = Path(args.first_frames)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume
    done_ids = set()
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass

    total = 0
    passed = 0
    failed = 0

    with out_path.open("a") as out_f:
        for i, case in enumerate(cases):
            cid = case["id"]
            if cid in done_ids:
                total += 1
                continue
            img_path = ff_dir / f"{cid}.png"
            if not img_path.exists():
                print(f"[check] [{i+1}/{len(cases)}] {cid}: no image, skip")
                continue

            result = {"verdict": "ERROR", "raw": ""}
            for attempt in range(max(1, args.retries + 1)):
                result = check_image(case, str(img_path))
                if result.get("verdict") != "ERROR":
                    break
                if attempt < args.retries:
                    wait = 5 * (attempt + 1)
                    print(f"[check] [{i+1}/{len(cases)}] {cid}: ERROR, retrying in {wait}s")
                    time.sleep(wait)
            result["id"] = cid
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()

            total += 1
            verdict = result.get("verdict", "?")
            if verdict == "PASS":
                passed += 1
            else:
                failed += 1

            print(f"[check] [{i+1}/{len(cases)}] {cid}: {verdict} "
                  f"(rel={result.get('relevance_score','?')} "
                  f"elem={result.get('elements_score','?')} "
                  f"edu={result.get('educational_score','?')} "
                  f"tech={result.get('technical_score','?')})")

    print(f"\n[check] DONE — {total} checked, {passed} PASS, {failed} FAIL")
    if failed > 0:
        print(f"[check] Failed IDs need regeneration. See {out_path}")


if __name__ == "__main__":
    main()
