# Project status — 2026-08-21

This is the canonical current-status page. Historical experiment details remain
in `docs/reports/`, `docs/REPORT.md`, and the Git history. “Implemented” below
means that code or study infrastructure exists; it does not mean that the
corresponding paper evidence has been collected.

## Current scope and defensible result

rise-teacher currently supports a reproducible 60-case short instructional-clip
pilot over 12 disciplines. Standard evaluation results exist for Wan 1.3B and
5B configurations at 3 s and 5 s, and Qwen3-VL-2B TeachQuiz-T results exist for
the two 3 s configurations. A 22-case graduate stress set has standard results
for Wan1.3B only.

The claim supported today is deliberately narrow:

> In this 60-case pilot with two Wan configurations and one Qwen3-VL-2B
> learner proxy, automated visual-rubric scores had low correlation with
> normalized simulated learning gain.

This is not evidence that standard video evaluation fails to predict human
learning, that TeachQuiz-T is human-validated, or that the benchmark ranks T2V
model families.

## Completed evidence

- 60-case pilot prompts, first frames, quiz/probe data, and schema validation.
- Standard automated evaluation for six Wan configuration/duration variants
  represented in `results/`, plus Wan1.3B on 22 graduate cases.
- TeachQuiz-T Qwen3-VL results for Wan5B-3s and Wan1.3B-3s.
- Six video-only rubric dimensions and a pre/post/random-control TeachQuiz-T
  pipeline.
- A blinded human-study exporter, rater UI, validation, reliability, and
  judge--human analysis code. No real ratings have been collected yet.
- A reproducible 100-case GRADE + DisciplineGen draft. It is not release-ready.
- Paired uncertainty analysis for the three existing matched standard-eval
  comparisons, including case-bootstrap CIs, Cohen's dz, paired sign-flip
  tests, and Holm correction:
  - `analysis/paired_wan5b_vs_wan13b_3s.md`
  - `analysis/paired_wan5b_5s_vs_3s.md`
  - `analysis/paired_wan13b_5s_vs_3s.md`

## What the paired analysis changes

- Wan5B-3s vs Wan1.3B-3s: the aggregate difference is -0.0683 in favour of
  Wan1.3B, but its 95% CI crosses zero (`[-0.1775, 0.0425]`). The current data
  do not establish an aggregate winner.
- Wan5B 5s vs 3s: aggregate change is small and uncertain. Narrative structure
  improves by 0.2000, but does not survive Holm correction at 0.05. Visual
  quality decreases by 0.4167 (`95% CI [-0.6000, -0.2417]`, Holm p=0.0008).
- Wan1.3B 5s vs 3s: no analysed headline dimension has a CI excluding zero.

These results supersede prose that inferred winners from unpaired means alone.

## Submission blockers

1. **Collect human validation:** 60 videos × 3 raters; report ordinal alpha and
   per-dimension judge--human correlations.
2. **Add an independent T2V family:** current headline model comparisons remain
   within Wan.
3. **Complete matched TI2V vs T2V:** the existing defect-oriented TI2V result is
   only `n=6`, not a benchmark-scale controlled comparison.
4. **Complete graduate evidence:** run Wan5B on the same 22 cases and canonical
   Qwen3-VL TeachQuiz-T for both configurations.
5. **Test learner dependence:** repeat TeachQuiz-T with a second frozen weak
   student model.
6. **Apply uncertainty analysis to every new final comparison:** the machinery
   now exists, but future model/TI2V/learner results must also use it.
7. **Clear the release gate:** verify redistribution rights, finish disciplinary
   and image review, resolve duplicate music rows, and document exclusions.

## Scope-dependent gaps

- Audio-narration and triple-modal evaluation require audio-capable outputs.
- Current 3–5 s videos support claims about short clips, not full lessons.
- Generation variance is unknown because there is one seed per prompt.
- A public benchmark requires a larger frozen and reviewed test split.
- The first-frame strict PASS rate remains about 25/60 for the original pilot.

## Recommended execution order

1. Freeze and distribute the human-rating packet; collect ratings.
2. Run the matched 60-case TI2V/T2V experiment.
3. Complete Wan5B graduate generation/evaluation and graduate TeachQuiz-T.
4. Run a second student model.
5. Add an independent model family.
6. Apply paired uncertainty analysis to every completed comparison.
7. Finish licensing/curation review, then freeze the release evidence package.

For detailed claim boundaries and required release artifacts, see
`docs/PAPER_READINESS.md`. For the prioritized experimental backlog, see
`docs/plan.md`.
