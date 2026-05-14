# rise-teacher pilot report

_v0.1 — Wan1.3B @ v0.2 high-difficulty_

## Run summary

- prompts: **82** (12 disciplines × 5 cases)
- generation: 22 ok / 0 failed
- mean generation wallclock: **228.4s / video**
- evaluated: **22** videos × 3 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 1.227 |
| narrative_structure | 1.091 |
| visual_quality | 2.727 |
| **Aggregate (weighted)** | **1.486** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| language_literature | 2 | 1.8 | 0.0% |
| civics | 2 | 1.775 | 0.0% |
| art_music | 2 | 1.75 | 0.0% |
| geography | 2 | 1.625 | 0.0% |
| biology | 2 | 1.425 | 0.0% |
| physics | 2 | 1.4 | 0.0% |
| history | 2 | 1.4 | 0.0% |
| mathematics | 2 | 1.375 | 0.0% |
| computer_science | 2 | 1.325 | 0.0% |
| economics | 2 | 1.275 | 0.0% |
| chemistry | 2 | 1.2 | 0.0% |

## Per difficulty

| Difficulty | N | Mean | Strict acc |
|---|---|---|---|
| high | 22 | 1.486 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| problem_solving | 11 | 1.527 | 0.0% |
| explanation | 11 | 1.445 | 0.0% |

## Top 5 cases by aggregate

- **civ_high_02** (civics / problem_solving) — agg **2.15**, strict False
- **geo_high_02** (geography / problem_solving) — agg **1.9**, strict False
- **art_high_01** (art_music / explanation) — agg **1.9**, strict False
- **lang_high_01** (language_literature / explanation) — agg **1.8**, strict False
- **lang_high_02** (language_literature / problem_solving) — agg **1.8**, strict False

## Bottom 5 cases by aggregate

- **bio_high_02** (biology / problem_solving) — agg **1.3**, strict False
- **cs_high_02** (computer_science / problem_solving) — agg **1.3**, strict False
- **chem_high_02** (chemistry / problem_solving) — agg **1.25**, strict False
- **econ_high_01** (economics / explanation) — agg **1.2**, strict False
- **chem_high_01** (chemistry / explanation) — agg **1.15**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) [1] Realist explanation mentions power balancing or Soviet threat
- (1× fail) [2] Liberal explanation mentions institutional benefits or collective security
- (1× fail) [3] comparison is fair to both theories
- (1× fail) [4] NATO correctly dated to 1949
- (1× fail) [2] World-Island correctly identified as Eurasia + Africa
- (1× fail) [3] sea-power critique mentioned
- (1× fail) 12 distinct pitches in the row (no repeats)
- (1× fail) inversion correctly reverses intervals (up↔down)
- (1× fail) retrograde correctly reverses pitch order
- (1× fail) all four forms labeled P, I, R, RI

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/pilot_v0_2.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_2_high/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_pilot_v0_2_high`.