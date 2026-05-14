# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B @ 5s_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **87.0s / video**
- evaluated: **60** videos × 3 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.567 |
| narrative_structure | 1.7 |
| visual_quality | 2.479 |
| **Aggregate (weighted)** | **1.789** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| art_music | 5 | 2.27 | 0.0% |
| history | 5 | 2.13 | 0.0% |
| physics | 5 | 2.12 | 0.0% |
| geography | 5 | 1.97 | 0.0% |
| biology | 5 | 1.95 | 0.0% |
| mathematics | 5 | 1.83 | 0.0% |
| medicine | 5 | 1.71 | 0.0% |
| chemistry | 5 | 1.64 | 0.0% |
| computer_science | 5 | 1.56 | 0.0% |
| language_literature | 5 | 1.56 | 0.0% |
| economics | 5 | 1.38 | 0.0% |
| civics | 5 | 1.35 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.552 | 0.0% |
| explanation | 36 | 1.947 | 0.0% |

## Top 5 cases by aggregate

- **art_exp_01** (art_music / explanation) — agg **3.1**, strict False
- **math_exp_02** (mathematics / explanation) — agg **2.85**, strict False
- **bio_exp_02** (biology / explanation) — agg **2.85**, strict False
- **hist_exp_02** (history / explanation) — agg **2.8**, strict False
- **geo_exp_03** (geography / explanation) — agg **2.8**, strict False

## Bottom 5 cases by aggregate

- **cs_exp_02** (computer_science / explanation) — agg **1.15**, strict False
- **civ_prob_02** (civics / problem_solving) — agg **1.15**, strict False
- **med_prob_02** (medicine / problem_solving) — agg **1.1**, strict False
- **econ_exp_01** (economics / explanation) — agg **1.1**, strict False
- **civ_exp_03** (civics / explanation) — agg **1.1**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) angle pieces visibly add up to a straight line
- (1× fail) A pairs only with T and G with C
- (1× fail) two strands are antiparallel (5' to 3' shown both ways)
- (1× fail) 3 packets in correct order
- (1× fail) labels SYN / SYN-ACK / ACK correct
- (1× fail) direction arrows match standard handshake
- (1× fail) outcome (slower heart rate) is at least implied
- (1× fail) axes are labeled
- (1× fail) tangent slope visually matches local curve slope
- (1× fail) two arrows are equal in length

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_5s/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_5s`.