# rise-teacher pilot report

_v0.1 — Wan2.1-T2V-1.3B_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **66.1s / video**
- evaluated: **60** videos × 3 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.567 |
| narrative_structure | 1.45 |
| visual_quality | 3.021 |
| **Aggregate (weighted)** | **1.823** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| art_music | 5 | 2.4 | 0.0% |
| history | 5 | 2.36 | 0.0% |
| geography | 5 | 2.13 | 0.0% |
| biology | 5 | 2.02 | 0.0% |
| physics | 5 | 1.98 | 0.0% |
| mathematics | 5 | 1.87 | 0.0% |
| civics | 5 | 1.77 | 0.0% |
| computer_science | 5 | 1.72 | 0.0% |
| economics | 5 | 1.65 | 0.0% |
| chemistry | 5 | 1.34 | 0.0% |
| medicine | 5 | 1.32 | 0.0% |
| language_literature | 5 | 1.31 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| explanation | 36 | 1.933 | 0.0% |
| problem_solving | 24 | 1.656 | 0.0% |

## Top 5 cases by aggregate

- **geo_exp_03** (geography / explanation) — agg **3.45**, strict False
- **art_prob_02** (art_music / problem_solving) — agg **3.0**, strict False
- **hist_exp_02** (history / explanation) — agg **2.95**, strict False
- **hist_exp_03** (history / explanation) — agg **2.95**, strict False
- **bio_exp_02** (biology / explanation) — agg **2.9**, strict False

## Bottom 5 cases by aggregate

- **chem_exp_01** (chemistry / explanation) — agg **1.25**, strict False
- **chem_prob_01** (chemistry / problem_solving) — agg **1.25**, strict False
- **med_prob_02** (medicine / problem_solving) — agg **1.25**, strict False
- **civ_exp_03** (civics / explanation) — agg **1.25**, strict False
- **lang_prob_01** (language_literature / problem_solving) — agg **1.15**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) [1] three ships visible (not two, not four)
- (1× fail) geographic direction roughly west from China
- (1× fail) Renaissance side shows more linear/realistic style
- (1× fail) construction is on ramps, not cranes
- (1× fail) no obvious anachronisms (no machinery, modern people, etc.)
- (1× fail) axes are labeled
- (1× fail) tangent slope visually matches local curve slope
- (1× fail) triangles have visibly different shapes
- (1× fail) angle pieces visibly add up to a straight line
- (1× fail) no contradiction with Euclidean geometry

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b`.