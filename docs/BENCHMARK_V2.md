当前规则为 `video-teacher-2x8-v9`，保留布局、过程、末帧对照、分钟级时长及逐窗口取证，增加实际语音识别和口述正确性、解释覆盖与音画对应门槛。详见 [英文有声协议](NARRATED_LESSONS_V2.md)、[历史分钟级协议](LESSONS_V1.md) 和 [v7 研究出处与局限](SCORING_V7_DESIGN.md)。本文其余部分保留八轴协议及历史说明。

# Video Teacher benchmark 2x8-v4

Version v4 strengthens comprehensibility within pedagogical clarity and visual
explanation within didactic affordances. It adds a separate, unweighted
teaching-engagement report. The eight public axes, equal-category weights and
correctness gates remain fixed. V3 and v4 results are not directly comparable;
reevaluate the same videos under v4. Exact criteria and score anchors are in
[the v4 teaching-design rules](TEACHING_DESIGN_V4.md).

This is a new scoring protocol. Its results must never be mixed with the legacy
3/6-dimension results or the 6x6 pilot. It follows FORGE's separation of
operators, named axes, per-sample evidence, a frozen score policy, completeness
gates, and aggregate reporting. It does **not** reuse industrial-video thresholds.

## Public score

| Category (50% each) | Subcategory | Algorithm | Scale |
| --- | --- | --- | --- |
| Video quality | Visual quality | Six evidence-backed VLM criteria: legibility, text stability, shape stability, artifacts, composition, motion | 0–100 |
| Video quality | Temporal consistency | Six evidence-backed VLM criteria for identity, motion, state, transitions, completion and readability; full-frame freeze operator caps severe failures | 0–100 |
| Video quality | Signal quality | Six evidence-backed VLM criteria for focus, exposure, compression, text, contrast and frame integrity; full-frame near-blank operator caps severe failures | 0–100 |
| Teaching quality | Conceptual correctness | Six factual, relational, symbolic, procedural, outcome and contradiction criteria | 0–100 |
| Teaching quality | Narrative structure | Six setup, target, sequence, transition, completion and pace criteria | 0–100 |
| Teaching quality | Pedagogical clarity | Six focus, attention, explanation, readability, ambiguity and takeaway criteria | 0–100 |
| Teaching quality | Didactic affordances | Six observable-change, step, anchor, alignment, inspectability and diagnosis criteria | 0–100 |
| Teaching quality | Audience appropriateness | Six prerequisite, vocabulary, complexity, speed, accessibility and task-fit criteria | 0–100 |

Six teaching/visual axes use `eval.rubric_6x6`; two video axes use
`eval.benchmark_video_rubric`. Each criterion has a score,
applicability flag, evidence-frame indices, and a finding. The dimension score
is the mean applicable 1–5 criterion score, mapped by `(score - 1) × 25`.
The judge sees up to 24 frames sampled uniformly across the clip; the selected
indices are retained. The CV operators inspect every decoded frame up to the
frozen 3000-frame safety limit.
Missing visual evidence is a low score; an unavailable judge is an error.
Each category is the unweighted mean of its axes. Overall score is the mean of
the two categories. No floor, imputation, or renormalization is allowed.

Strict pass requires every axis ≥60, each category ≥70, and conceptual
correctness plus pedagogical clarity ≥70. If required narration has no detected
audio signal, the final score is capped at 40 and strict pass fails. A failed
audio probe invalidates the case. The audio detector measures signal presence
only: it cannot establish speech, narration correctness, or intelligibility.

Critical observed defects are non-compensatory. Criterion scores of 1–2 for
intrusive artifacts, mutated text/symbols, wrong core facts, broken object
identity, or missing requested transitions cap their axis at 40 and the final
score at 50. A requested multistep action frozen for at least 1.5 seconds caps
temporal consistency at 50 and the final score at 60. Every cap is recorded
with its triggering criterion, finding and cited frames. The ten-video trial
showed high CV diagnostic values on clips with hands and corrupted diagrams;
therefore CV values are not used as direct video-quality scores.

## Run

```bash
python -m eval.run_benchmark_v2 \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest path/to/manifest.jsonl \
  --out results/benchmark_v2
```

The judge must support vision input and Chat Completions JSON mode. For an
OpenAI-compatible API, set these environment variables in the same shell:

```powershell
$env:VIDEO_TEACHER_API_KEY = '<API key>'
$env:VIDEO_TEACHER_BASE_URL = 'https://your-provider.example/v1'
$env:VIDEO_TEACHER_MODEL = 'your-vision-model'
python -m eval.run_benchmark_v2 --prompts data/prompts/pilot_v0_1.jsonl --manifest path/to/manifest.jsonl --out results/benchmark_v2 --preflight
python -m eval.run_benchmark_v2 --prompts data/prompts/pilot_v0_1.jsonl --manifest path/to/manifest.jsonl --out results/benchmark_v2_probe --limit 1
python -m eval.run_benchmark_v2 --prompts data/prompts/pilot_v0_1.jsonl --manifest path/to/manifest.jsonl --out results/benchmark_v2
```

`--preflight` checks the input files, local video paths, judge configuration,
and local dependencies without spending API calls. It exits with code 2 when
a requested case has no successful generation or its video is missing. The one-case run exercises
all eight vision judgments and should report `n_valid: 1`; its ranking is
intentionally not publishable. If an API call or rubric validation fails,
inspect that case's `errors` and `axes.*.error` in `per_case.jsonl`, fix the
cause, and rerun the same full command. Valid cases are reused; failed cases
are retried. Do not put the API key in command arguments or output files.

Without `VIDEO_TEACHER_API_KEY`, the existing Azure CLI login and Azure endpoint
configuration are used. `ffmpeg` must be available for cases requiring
narration; `imageio-ffmpeg` is accepted when installed. The runner writes
`per_case.jsonl` with criterion evidence, operator diagnostics, video digest,
errors and category scores; `aggregate.json` contains counts, means, strata and
a seeded case-bootstrap 95% interval. The latest manifest attempt per ID wins.
Missing/failed generations remain in the denominator. Any failed case or
`--limit` debug run sets `ranking_publishable=false` and `ranking_score=null`.
Completed case results are saved immediately and reused only when the case,
video hash, scoring code, rubric version, judge provider/model/endpoint and sampling
configuration match. Failed cases are
retried on the next invocation.

For matched models, run `python -m eval.compare_benchmark_v2 --left
LEFT/per_case.jsonl --right RIGHT/per_case.jsonl --out comparison.json`.
It rejects unequal case sets or incomplete cases and reports a paired case
bootstrap interval and two-sided sign-flip randomisation p-value. Both are
conditional on the chosen cases and judges; they do not establish general
population validity.

## Validity requirements before a paper claim

The thresholds and category weights are declared design choices, **not**
empirically calibrated values. The relative focus metric cannot detect a
uniformly blurred clip; duplicate-frame and luminance operators can mistake intended holds
or cuts for faults. A soundtrack can pass the audio-signal detector. Sampled
frames can miss brief factual errors. Consequently these code-complete metrics
are an executable protocol, not validated evidence of teaching effectiveness.

Before a top-conference claim, freeze a held-out, discipline-balanced test set;
obtain independent expert ratings with blind duplicate items; report inter-rater
agreement and uncertainty; check calibration and sensitivity of every operator
against those ratings; validate audio narration with speech transcription and
human listening; run paired model comparisons with case-level bootstrap; and
test learning outcomes with human learners. Keep TeachQuiz-T separate as a
learner-proxy outcome, not another aesthetic subscore. Publish missingness,
cost, prompt/model versions, and failure examples alongside rankings.
