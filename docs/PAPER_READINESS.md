# Paper-Readiness Audit

**Audit date:** 2026-08-06. This document distinguishes implemented infrastructure from evidence actually collected. A script, a pilot, or an attractive qualitative example is not treated as a completed paper experiment.

## What is already defensible

- A reproducible 60-case pilot spanning 12 disciplines and explanation/problem-solving tasks.
- Two open-model configurations and 3 s/5 s standard-evaluation results; a 22-case graduate stress set for Wan1.3B.
- A pre/post/random-control TeachQuiz-T pipeline with case-level outputs for Qwen3-VL-2B on the 60-case pilot.
- Six video-only rubric dimensions with per-case automated scores, plus a defect-oriented TI2V seed study that is clearly labelled as `n=6`.
- A blinded human-validation package (`scripts/human_eval.py`, `human_eval/index.html`, and `HUMAN_EVAL_PROTOCOL.md`). This is infrastructure only until ratings are collected.

## Submission blockers

1. **Human validation has not been collected.** Execute the preregistered 60-video × 3-rater study and report ordinal alpha and judge--human correlations per dimension. Do not describe GPT-5.5 scores as validated beforehand.
2. **The central model comparison is too narrow.** Current headline comparisons are variants of Wan; add at least one independently developed T2V system, or sharply limit claims to the studied Wan configurations. A commercial baseline is useful but not a substitute for transparent configuration reporting.
3. **TI2V-vs-T2V is incomplete at benchmark scale.** The n=6 defect seed is not a 60-case controlled comparison. Run matched 60-case TI2V and T2V generations with identical prompts, duration, resolution, steps, and seed policy; evaluate both standard scores and TeachQuiz-T.
4. **Graduate conclusions are one-sided.** Run Wan5B on the same 22 high-difficulty cases and run the canonical Qwen3-VL TeachQuiz-T for both configurations. Until then, claims about model-size effects at graduate difficulty are unsupported.
5. **TeachQuiz-T learner dependence is unknown.** Repeat the pilot with a second frozen weak student model, report agreement/rank stability, and retain all pre/post/random case-level outputs. A single simulated learner is insufficient for a general learning-effectiveness claim.
6. **Uncertainty is missing from headline comparisons.** For every model comparison, report paired case-level effect sizes, 95% bootstrap CIs, and a predeclared paired significance procedure. Do not infer a winner from a difference such as 0.030 without its uncertainty.
7. **Dataset release is not ready.** The multisource set is explicitly blocked by source-license and curation review. Release only prompt/provenance assets whose redistribution status is verified; document exclusions and hashes.

## Important but scope-dependent gaps

- Audio and triple-modal dimensions cannot be claimed for silent-video Wan outputs. Either omit them from the main scorecard or evaluate an audio-capable model with a separately validated protocol.
- 3--5 second clips support a short-form instructional-clip benchmark, not a claim about full lessons or long-horizon teaching. Rename claims accordingly unless a longer-video study is run.
- One generation seed per prompt cannot quantify generation variance. For the final selected models, use 3--5 independent seeds on a preregistered subset and report prompt-level variability.
- The 60-case pilot can support a pilot paper only if claims are carefully bounded. A public benchmark/leaderboard needs a frozen, reviewed test split and substantially more cases.

## Required evidence package before submission

Freeze a release tag containing: prompts and schema; generator commands/model revisions; manifests and SHA-256 hashes; raw per-case standard and TeachQuiz outputs; human-study assignments, raw anonymized responses, exclusion log, and analysis output; exact judge prompts/model deployment identifiers; bootstrap/significance code; licenses and data card; and a paper appendix listing every failure/exclusion.

## Claim language allowed today

Use: “In this 60-case pilot with two Wan configurations and one Qwen3-VL-2B learner proxy, automated visual-rubric scores had low correlation with normalized simulated learning gain.”

Do not yet use: “standard video evaluation does not predict human learning,” “TeachQuiz-T is validated,” “the benchmark ranks T2V models,” or “TI2V improves teaching quality.”
