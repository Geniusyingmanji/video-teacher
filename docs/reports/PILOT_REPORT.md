# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **33.9s / video**
- evaluated: **60** videos × 3 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.45 |
| narrative_structure | 1.5 |
| visual_quality | 2.896 |
| **Aggregate (weighted)** | **1.754** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| history | 5 | 2.23 | 0.0% |
| civics | 5 | 2.01 | 0.0% |
| art_music | 5 | 2.0 | 0.0% |
| geography | 5 | 1.88 | 0.0% |
| mathematics | 5 | 1.8 | 0.0% |
| biology | 5 | 1.79 | 0.0% |
| physics | 5 | 1.78 | 0.0% |
| language_literature | 5 | 1.6 | 0.0% |
| computer_science | 5 | 1.59 | 0.0% |
| chemistry | 5 | 1.51 | 0.0% |
| medicine | 5 | 1.51 | 0.0% |
| economics | 5 | 1.35 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.5 | 0.0% |
| explanation | 36 | 1.924 | 0.0% |

## Top 5 cases by aggregate

- **hist_exp_03** (history / explanation) — agg **3.15**, strict False
- **math_exp_02** (mathematics / explanation) — agg **2.65**, strict False
- **phys_exp_01** (physics / explanation) — agg **2.6**, strict False
- **art_exp_01** (art_music / explanation) — agg **2.55**, strict False
- **hist_exp_01** (history / explanation) — agg **2.45**, strict False

## Bottom 5 cases by aggregate

- **chem_prob_02** (chemistry / problem_solving) — agg **1.25**, strict False
- **med_prob_01** (medicine / problem_solving) — agg **1.25**, strict False
- **math_prob_02** (mathematics / problem_solving) — agg **1.2**, strict False
- **cs_prob_01** (computer_science / problem_solving) — agg **1.2**, strict False
- **econ_prob_02** (economics / problem_solving) — agg **1.15**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) geographic direction roughly west from China
- (1× fail) triangles have visibly different shapes
- (1× fail) angle pieces visibly add up to a straight line
- (1× fail) arrows are on the two distinct bodies (one on wall, one on person)
- (1× fail) no obvious anachronisms (no machinery, modern people, etc.)
- (1× fail) three ships visible (not two, not four)
- (1× fail) [1] spiral rotation visible
- (1× fail) [2] eye is in the center and visibly calmer
- (1× fail) red+yellow=orange (not brown or other)
- (1× fail) blue+yellow=green

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_1`.