# rise-teacher pilot report

_v0.1 — Wan2.1-T2V-1.3B @ 5s_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **239.2s / video**
- evaluated: **60** videos × 3 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.517 |
| narrative_structure | 1.4 |
| visual_quality | 3.05 |
| **Aggregate (weighted)** | **1.788** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| art_music | 5 | 2.4 | 0.0% |
| history | 5 | 2.4 | 0.0% |
| mathematics | 5 | 2.06 | 0.0% |
| physics | 5 | 2.0 | 0.0% |
| geography | 5 | 1.93 | 0.0% |
| biology | 5 | 1.84 | 0.0% |
| civics | 5 | 1.58 | 0.0% |
| chemistry | 5 | 1.55 | 0.0% |
| medicine | 5 | 1.52 | 0.0% |
| computer_science | 5 | 1.45 | 0.0% |
| economics | 5 | 1.44 | 0.0% |
| language_literature | 5 | 1.29 | 0.0% |

## Per difficulty

| Difficulty | N | Mean | Strict acc |
|---|---|---|---|
| k12 | 29 | 1.984 | 0.0% |
| professional | 5 | 1.52 | 0.0% |
| undergrad | 26 | 1.621 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.625 | 0.0% |
| explanation | 36 | 1.897 | 0.0% |

## Top 5 cases by aggregate

- **art_exp_01** (art_music / explanation) — agg **3.35**, strict False
- **geo_exp_03** (geography / explanation) — agg **3.35**, strict False
- **hist_exp_03** (history / explanation) — agg **3.2**, strict False
- **art_prob_02** (art_music / problem_solving) — agg **3.2**, strict False
- **bio_exp_02** (biology / explanation) — agg **2.95**, strict False

## Bottom 5 cases by aggregate

- **lang_exp_02** (language_literature / explanation) — agg **1.3**, strict False
- **geo_exp_01** (geography / explanation) — agg **1.25**, strict False
- **lang_prob_01** (language_literature / problem_solving) — agg **1.25**, strict False
- **civ_prob_01** (civics / problem_solving) — agg **1.2**, strict False
- **lang_exp_03** (language_literature / explanation) — agg **1.2**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) A pairs only with T and G with C
- (1× fail) two strands are antiparallel (5' to 3' shown both ways)
- (1× fail) axes are labeled
- (1× fail) [2] construction is on ramps, not cranes
- (1× fail) triangles have visibly different shapes
- (1× fail) angle pieces visibly add up to a straight line
- (1× fail) [1] upward flow is in the center (above heat source)
- (1× fail) [2] downward flow is along the sides
- (1× fail) [3] circulation is continuous, not random
- (1× fail) final answer 2 mol H2O

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b_5s/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b_5s`.