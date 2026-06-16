# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B + GPT-Image first frames, 5s_

## Run summary

- prompts: **60** (12 disciplines × 5 cases)
- generation: 60 ok / 0 failed
- mean generation wallclock: **56.1s / video**
- evaluated: **60** videos × 6 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.917 |
| narrative_structure | 1.683 |
| visual_quality | 2.688 |
| pedagogical_clarity | 1.617 |
| didactic_affordances | 1.842 |
| audience_appropriateness | 2.548 |
| **Aggregate (weighted)** | **2.013** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| history | 5 | 2.469 | 0.0% |
| physics | 5 | 2.233 | 0.0% |
| art_music | 5 | 2.231 | 0.0% |
| biology | 5 | 2.073 | 0.0% |
| geography | 5 | 2.068 | 0.0% |
| chemistry | 5 | 2.052 | 0.0% |
| economics | 5 | 2.038 | 0.0% |
| medicine | 5 | 1.971 | 0.0% |
| civics | 5 | 1.855 | 0.0% |
| computer_science | 5 | 1.838 | 0.0% |
| mathematics | 5 | 1.742 | 0.0% |
| language_literature | 5 | 1.586 | 0.0% |

## Per difficulty

| Difficulty | N | Mean | Strict acc |
|---|---|---|---|
| k12 | 29 | 2.095 | 0.0% |
| professional | 5 | 1.971 | 0.0% |
| undergrad | 26 | 1.93 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 24 | 1.798 | 0.0% |
| explanation | 36 | 2.156 | 0.0% |

## Top 5 cases by aggregate

- **hist_exp_01** (history / explanation) — agg **3.095**, strict False
- **bio_exp_02** (biology / explanation) — agg **3.03**, strict False
- **art_exp_03** (art_music / explanation) — agg **2.942**, strict False
- **hist_exp_03** (history / explanation) — agg **2.885**, strict False
- **hist_exp_02** (history / explanation) — agg **2.587**, strict False

## Bottom 5 cases by aggregate

- **art_prob_01** (art_music / problem_solving) — agg **1.4**, strict False
- **lang_exp_02** (language_literature / explanation) — agg **1.35**, strict False
- **lang_prob_02** (language_literature / problem_solving) — agg **1.33**, strict False
- **lang_prob_01** (language_literature / problem_solving) — agg **1.328**, strict False
- **math_exp_03** (mathematics / explanation) — agg **1.198**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) A pairs only with T and G with C
- (1× fail) two strands are antiparallel (5' to 3' shown both ways)
- (1× fail) Renaissance side shows more linear/realistic style
- (1× fail) [2] downward flow is along the sides
- (1× fail) [3] circulation is continuous, not random
- (1× fail) 3 packets in correct order
- (1× fail) labels SYN / SYN-ACK / ACK correct
- (1× fail) direction arrows match standard handshake
- (1× fail) correct answer yellow + blue = green
- (1× fail) mixing demo visually produces green, not another color

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality, pedagogical_clarity, didactic_affordances, audience_appropriateness.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_1.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff_5s/pilot_v0_1/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_wan2_2_ti2v_5b_ff_5s`.