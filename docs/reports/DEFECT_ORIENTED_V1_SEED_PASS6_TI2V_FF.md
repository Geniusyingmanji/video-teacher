# rise-teacher pilot report

_v0.1 — Wan2.2-TI2V-5B + defect-oriented first frames, pass6, 3s_

## Run summary

- prompts: **6** (12 disciplines × 5 cases)
- generation: 6 ok / 0 failed
- mean generation wallclock: **49.4s / video**
- evaluated: **6** videos × 6 dims via GPT-5.5 keyless

## Headline scores (1..5, higher better)

| Dimension | Mean |
|---|---|
| conceptual_correctness | 2.667 |
| narrative_structure | 2.167 |
| visual_quality | 2.583 |
| pedagogical_clarity | 2.167 |
| didactic_affordances | 2.417 |
| audience_appropriateness | 3.083 |
| **Aggregate (weighted)** | **2.512** |
| **Strict accuracy** | **0.0%** |

## Per discipline

| Discipline | N | Mean | Strict acc |
|---|---|---|---|
| geography | 1 | 3.853 | 0.0% |
| physics | 1 | 2.755 | 0.0% |
| civics | 1 | 2.745 | 0.0% |
| biology | 1 | 2.002 | 0.0% |
| mathematics | 1 | 1.895 | 0.0% |
| economics | 1 | 1.82 | 0.0% |

## Per difficulty

| Difficulty | N | Mean | Strict acc |
|---|---|---|---|
| k12 | 1 | 3.853 | 0.0% |
| undergrad | 5 | 2.243 | 0.0% |

## Per task type

| Task | N | Mean | Strict acc |
|---|---|---|---|
| explanation | 3 | 2.87 | 0.0% |
| problem_solving | 3 | 2.153 | 0.0% |

## Top 5 cases by aggregate

- **defect_v1_geo_orographic_rain_shadow** (geography / explanation) — agg **3.853**, strict False
- **defect_v1_phys_rc_time_constant** (physics / explanation) — agg **2.755**, strict False
- **defect_v1_civics_judicial_review_vs_amendment** (civics / problem_solving) — agg **2.745**, strict False
- **defect_v1_bio_crispr_repair_choice** (biology / explanation) — agg **2.002**, strict False
- **defect_v1_math_chain_rule_trace** (mathematics / problem_solving) — agg **1.895**, strict False

## Bottom 5 cases by aggregate

- **defect_v1_phys_rc_time_constant** (physics / explanation) — agg **2.755**, strict False
- **defect_v1_civics_judicial_review_vs_amendment** (civics / problem_solving) — agg **2.745**, strict False
- **defect_v1_bio_crispr_repair_choice** (biology / explanation) — agg **2.002**, strict False
- **defect_v1_math_chain_rule_trace** (mathematics / problem_solving) — agg **1.895**, strict False
- **defect_v1_econ_ad_as_supply_shock** (economics / problem_solving) — agg **1.82**, strict False

## Most-failed rubric checks (conceptual_correctness)

- (1× fail) [2] Cooling during ascent and warming during descent must be shown or labeled.
- (1× fail) Must distinguish current decrease from voltage increase.
- (1× fail) Graph must label tau=RC and the 63 percent point correctly.
- (1× fail) Must show double-strand break before repair.
- (1× fail) Must distinguish NHEJ disruption from HDR template-guided repair.
- (1× fail) Must show the inner derivative 6x, not just the outer power rule.
- (1× fail) Final derivative must be 24x(3x^2+1)^3.
- (1× fail) Notation must keep u, x, dy/du, and du/dx consistently distinguished.
- (1× fail) Price level must rise while output falls.

## Notes

- All evaluation is automated via GPT-5.5 keyless Azure OpenAI; no human raters yet.
- Dimension subset for this pilot: conceptual_correctness, narrative_structure, visual_quality, pedagogical_clarity, didactic_affordances, audience_appropriateness.
- See `eval/dimensions/` for prompt details. Aggregate weighting defined in `eval/run_eval.py`.
- Source files: prompts at `data/prompts/defect_oriented_v1_seed_pass6.jsonl`, manifest at `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/defect_oriented_v1_seed_pass6/manifest.jsonl`, eval at `/data/zyf/rise-teacher/outputs/eval_defect_oriented_v1_seed_pass6_ti2v_ff`.