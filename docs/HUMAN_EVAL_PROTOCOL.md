# Blinded Human Validation Protocol

This protocol is the release gate for claims based on the GPT-5.5 evaluator. It validates the six video-only dimensions; it does not claim that human raters validate TeachQuiz-T's simulated learner outcome.

## Preregistered design

Rate 60 videos sampled deterministically and stratified over discipline, task type, and difficulty. Each video is independently rated by three qualified raters (180 video-rater assignments; up to 1,080 ordinal ratings). Recruit raters who can read English instructional material; require a short qualification set with at least 80% agreement on anchor examples. Do not show model names, generation method, GPT scores, aggregate scores, or the study hypothesis.

Each rater watches the full video once, may replay it once, and assigns integer 1--5 scores to the dimensions listed in the assigned packet. They may report `cannot assess` only for an unplayable asset; that video must be reassigned rather than silently scored as zero. Randomize video order independently per rater. Do not let a rater score a video they authored or generated.

Use the dimension definitions in `eval/dimensions/`; preserve the expected concepts and narrative order in the packet so that correctness is evaluated against the task specification, not personal taste. Before the main study, calibrate with 8 held-out videos and discuss only rubric interpretation, never the desired outcome.

## Execution

Run this from the repository root after the chosen generation/evaluation run exists:

```bash
python scripts/human_eval.py export \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest /data/zyf/rise-teacher/generations/.../manifest.jsonl \
  --judge /data/zyf/rise-teacher/outputs/.../per_case.jsonl \
  --out data/human_eval/pilot_01 --n-cases 60 --raters 3 --seed 20260806
```

Serve the files under `data/human_eval/pilot_01/raters/` and the referenced videos through an authenticated internal server, giving each rater only their matching packet. `assignments.jsonl` is the combined analysis copy and should not be distributed. All assignment files are intentionally blinded. Collect one response object per assignment using the schema below; retain raw submissions and the generated `study_manifest.json` without edits.

```json
{"assignment_id":"s20260806-r1-001","rater_id":"rater_01","scores":{"conceptual_correctness":4,"narrative_structure":3,"visual_quality":4}}
```

Analyse only after collection closes:

```bash
python scripts/human_eval.py analyse \
  --assignments data/human_eval/pilot_01/assignments.jsonl \
  --responses data/human_eval/pilot_01/responses.jsonl \
  --judge /data/zyf/rise-teacher/outputs/.../per_case.jsonl \
  --out docs/analysis/human_validation.md --seed 20260806
```

The script rejects unknown assignments, rater/assignment mismatches, duplicate submissions, and non-integer/out-of-range scores. It writes both a readable report and machine-readable JSON.

## Reporting rule

Report the sample, rater qualifications, compensation, exclusions, completion rate, ordinal Krippendorff's alpha for every dimension, and case-level Spearman judge--human correlations with 5,000 case-bootstrap 95% CIs. Avoid a global claim that the automated judge is human-aligned if a core factual or pedagogical dimension has weak reliability or a CI spanning a practically negligible association. State that this validates the *video-quality judge*, not the VLM learner proxy.

The static `human_eval/index.html` is an optional local collector: it reads one file from the generated `raters/` directory and downloads that rater's JSONL responses. For production collection, use an authenticated service and retain its immutable audit log.

Operational handoff instructions and a response example are tracked in
`data/human_eval/README.md`. The final study must also satisfy the human-study
section of `docs/RELEASE_CHECKLIST.md`.
