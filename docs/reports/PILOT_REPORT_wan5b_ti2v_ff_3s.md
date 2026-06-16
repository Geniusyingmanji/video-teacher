# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B + GPT-Image first frames, 3s_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **33.5s / video**
- evaluated: **60** videos × 6 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.967 |
| narrative_structure | 1.733 |
| visual_quality | 2.675 |
| pedagogical_clarity | 1.581 |
| didactic_affordances | 1.863 |
| audience_appropriateness | 2.44 |
| **Aggregate (weighted)** | **2.017** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| history | 5 | 2.557 | 0.0% |
| art_music | 5 | 2.399 | 0.0% |
| physics | 5 | 2.123 | 0.0% |
| geography | 5 | 2.087 | 0.0% |
| biology | 5 | 2.056 | 0.0% |
| economics | 5 | 1.975 | 0.0% |
| civics | 5 | 1.974 | 0.0% |
| chemistry | 5 | 1.907 | 0.0% |
| medicine | 5 | 1.905 | 0.0% |
| computer_science | 5 | 1.744 | 0.0% |
| language_literature | 5 | 1.742 | 0.0% |
| mathematics | 5 | 1.739 | 0.0% |

## Per difficulty

| Difficulty | N | Mean | Strict acc |
|---|---|---|---|
| k12 | 29 | 2.121 | 0.0% |
| professional | 5 | 1.905 | 0.0% |
| undergrad | 26 | 1.924 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.853 | 0.0% |
| explanation | 36 | 2.127 | 0.0% |

## Top 5 cases by aggregate

- **hist_exp_01** (history / explanation) — agg **3.48**, strict False
- **bio_exp_02** (biology / explanation) — agg **2.968**, strict False
- **hist_exp_03** (history / explanation) — agg **2.923**, strict False
- **art_prob_02** (art_music / problem_solving) — agg **2.845**, strict False
- **art_exp_03** (art_music / explanation) — agg **2.607**, strict False

## Bottom 5 cases by aggregate

- **lang_prob_02** (language_literature / problem_solving) — agg **1.442**, strict False
- **lang_prob_01** (language_literature / problem_solving) — agg **1.438**, strict False
- **chem_exp_01** (chemistry / explanation) — agg **1.42**, strict False
- **cs_exp_01** (computer_science / explanation) — agg **1.2**, strict False
- **math_prob_01** (mathematics / problem_solving) — agg **1.198**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) A pairs only with T and G with C
- (1× fail) two strands are antiparallel (5' to 3' shown both ways)
- (1× fail) three ships visible (not two, not four)
- (1× fail) system is over warm water (not ice or desert)
- (1× fail) Renaissance side shows more linear/realistic style
- (1× fail) summation of discounted cash flows shown
- (1× fail) rays converge AFTER the lens
- (1× fail) all 3 rays meet at a single point F on the axis
- (1× fail) [1] upward flow is in the center (above heat source)
- (1× fail) [2] downward flow is along the sides

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality, pedagogical_clarity, didactic_affordances, audience_appropriateness.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_wan2_2_ti2v_5b_ff`.