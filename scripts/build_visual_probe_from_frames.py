"""Auto-generate visual probe questions from video frames using GPT-5.5.

For each case, samples 8 frames, asks GPT-5.5 to generate 3 questions that:
1. Require seeing the specific frames to answer correctly
2. Cannot be guessed from the prompt text alone
3. Are multiple-choice (A-D) with one correct answer

Writes:
    data/teachquiz/visual_probe_auto_<manifest_stem>.jsonl

Usage:
    python scripts/build_visual_probe_from_frames.py \
      --manifest /data/.../manifest.jsonl \
      --prompts data/prompts/pilot_v0_1.jsonl \
      --out data/teachquiz/visual_probe_auto_5b.jsonl \
      --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.frame_extractor import extract_frames, frames_as_multimodal_content
from eval.judges.gpt55 import chat


SYSTEM_PROMPT = """You are designing evaluation questions for an educational video benchmark.
Given 8 frames from a generated educational video, create 3 multiple-choice questions that:

1. REQUIRE seeing these specific frames to answer correctly
2. CANNOT be answered by just knowing the topic — they must test visual grounding
3. Are about OBSERVABLE details: colors used, specific labels shown, what appears in frame N,
   spatial relationships, whether a specific element is present

Format as JSON: {"questions": [{"question": "...", "choices": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "A|B|C|D", "rationale": "observable reason"}]}

Bad example (too factual): "What is the derivative of x^2?"
Good example: "What color is the tangent line in the frames?"
Good example: "Which label appears on the x-axis?"
Good example: "In frame 4, what shape is highlighted in yellow?"
"""


def generate_probe_questions(case: dict, frames: list, max_retries: int = 2) -> list[dict]:
    user_text = (
        f"Case: {case['id']} — {case['discipline']}\n"
        f"Topic: {case['prompt_text'][:200]}\n\n"
        "Generate 3 visual grounding questions about these 8 frames. "
        "Return JSON only."
    )
    content = frames_as_multimodal_content(frames, user_text)
    for _ in range(max_retries):
        raw = chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(raw)
            questions = data.get("questions", [])
            if not questions:
                # Try top-level list
                if isinstance(data, list):
                    questions = data
            if questions:
                return questions
        except Exception:
            pass
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-frames", type=int, default=8)
    ap.add_argument("--frame-max-px", type=int, default=384)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    prompts = {}
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                prompts[c["id"]] = c

    manifest = []
    with open(args.manifest) as f:
        for line in f:
            line = line.strip()
            if line:
                m = json.loads(line)
                if m.get("status") == "ok":
                    manifest.append(m)
    if args.limit > 0:
        manifest = manifest[:args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume
    done_ids = set()
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["case_id"])
                except Exception:
                    pass
    print(f"[probe-gen] {len(manifest)} videos, {len(done_ids)} already done")

    with out_path.open("a") as out_f:
        for i, m in enumerate(manifest):
            cid = m["id"]
            if cid in done_ids:
                continue
            case = prompts.get(cid)
            if not case:
                print(f"[probe-gen] [{i+1}/{len(manifest)}] {cid}: no prompt, skip")
                continue
            try:
                frames = extract_frames(m["video_path"], n=args.n_frames, resize_max=args.frame_max_px)
            except Exception as e:
                print(f"[probe-gen] [{i+1}/{len(manifest)}] {cid}: frame extract failed: {e}")
                continue
            questions = generate_probe_questions(case, frames)
            if not questions:
                print(f"[probe-gen] [{i+1}/{len(manifest)}] {cid}: no questions generated")
                continue
            # Normalize question IDs
            quiz_items = []
            for j, q in enumerate(questions[:3]):
                quiz_items.append({
                    "id": f"{cid}_vp{j+1}",
                    "question": q.get("question", ""),
                    "choices": q.get("choices", []),
                    "answer": q.get("answer", "A"),
                    "tested_concepts": ["visual grounding"],
                    "rationale": q.get("rationale", ""),
                })
            entry = {"case_id": cid, "quiz": quiz_items}
            out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out_f.flush()
            print(f"[probe-gen] [{i+1}/{len(manifest)}] {cid}: wrote {len(quiz_items)} questions")

    print(f"[probe-gen] done → {out_path}")


if __name__ == "__main__":
    main()
