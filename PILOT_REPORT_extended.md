# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B (5-dim)_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **33.9s / video**
- evaluated: **60** videos × 5 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.5 |
| narrative_structure | 1.4 |
| visual_quality | 2.919 |
| pedagogical_clarity | 1.492 |
| didactic_affordances | 1.604 |
| **Aggregate (weighted)** | **1.766** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| history | 5 | 2.183 | 0.0% |
| geography | 5 | 2.031 | 0.0% |
| art_music | 5 | 2.012 | 0.0% |
| civics | 5 | 1.899 | 0.0% |
| biology | 5 | 1.831 | 0.0% |
| physics | 5 | 1.804 | 0.0% |
| computer_science | 5 | 1.705 | 0.0% |
| mathematics | 5 | 1.647 | 0.0% |
| medicine | 5 | 1.613 | 0.0% |
| chemistry | 5 | 1.572 | 0.0% |
| language_literature | 5 | 1.471 | 0.0% |
| economics | 5 | 1.424 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.572 | 0.0% |
| explanation | 36 | 1.895 | 0.0% |

## Top 5 cases by aggregate

- **hist_exp_01** (history / explanation) — agg **2.717**, strict False
- **hist_exp_03** (history / explanation) — agg **2.715**, strict False
- **bio_exp_02** (biology / explanation) — agg **2.455**, strict False
- **math_exp_02** (mathematics / explanation) — agg **2.422**, strict False
- **geo_exp_02** (geography / explanation) — agg **2.415**, strict False

## Bottom 5 cases by aggregate

- **econ_exp_01** (economics / explanation) — agg **1.275**, strict False
- **math_prob_01** (mathematics / problem_solving) — agg **1.273**, strict False
- **math_prob_02** (mathematics / problem_solving) — agg **1.238**, strict False
- **bio_prob_02** (biology / problem_solving) — agg **1.238**, strict False
- **lang_prob_01** (language_literature / problem_solving) — agg **1.238**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) [3] no obvious anachronisms (no machinery, modern people, etc.)
- (1× fail) geographic direction roughly west from China
- (1× fail) A pairs only with T and G with C
- (1× fail) two strands are antiparallel (5' to 3' shown both ways)
- (1× fail) triangles have visibly different shapes
- (1× fail) angle pieces visibly add up to a straight line
- (1× fail) red+yellow=orange (not brown or other)
- (1× fail) blue+yellow=green
- (1× fail) blue+red=purple
- (1× fail) spiral rotation visible

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality, pedagogical_clarity, didactic_affordances.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_extended`.