# 60-case TI2V quality review (2026-10-31)

## Evidence

The original 3-second Wan TI2V run completed 60/60 files with valid hashes.
File completion is not a quality result. Reviewing sampled start, midpoint and
end frames found static diagrams, altered equations, unrelated hands or objects,
and a pyramid surface that changed into illegible symbols. The automated
motion review flagged 13/60 clips with a maximum sampled grayscale change
below 5/255 at 160 × 90. This flag is only a review cue; small meaningful
movements may score low.

The underlying pilot prompts often request several teaching steps or even a
10-second narration, although the run supplies 73 frames at 24 fps (3.04 s).
Many first frames already show the answer, leaving no state transition for
the video model to produce.
The latest stored first-frame review marks 49 PASS, 10 FAIL and 1 ERROR;
`art_exp_03` already contains wrong color-mixing equations and misspellings.
Regenerating from those inputs cannot produce a trustworthy teaching clip.

## Controlled probes

Five matched cases were rerun with the same model, seed, duration, size and
steps. Only the prompt treatment changed.

| Treatment | Observation from five contact sheets | Decision |
| --- | --- | --- |
| Original prompt | Some static output; wrong text or intrusive objects in several cases | Historical baseline only |
| Focused one-action prompt | Increased motion in some cases but introduced hands, altered text and malformed pyramid structure | Keep opt-in for research; do not deploy as a quality fix |
| Original prompt plus negative prompt | Suppressed many intrusions but often suppressed meaningful motion as well | Keep opt-in for research; do not deploy as a quality fix |

The comparison sheets are at `results/quality_probe_focused_5/comparison.jpg`
and `results/quality_probe_negative_5/comparison.jpg`.

## Code changes

- `scripts/audit_generated_videos.py` now records a coarse motion score and
  flags low-motion clips for review.
- `scripts.pipeline_preflight --first-frame-review <report>` can refuse a
  quality rerun unless every source frame has a PASS review. The existing
  report blocks 11/60; it is historical review evidence and does not include
  per-image hashes, so changed images require fresh review.
- `generation/runners/wan_ti2v_runner.py` accepts opt-in focused and negative
  prompts. Their inputs are recorded in generation provenance. Neither mode is
  enabled in the default pipeline.
- `generation/runners/diagram_overlay_runner.py` creates a separate, reviewed
  deterministic track for text-heavy diagrams. Four examples use exact source
  pixels and simple focus boxes, avoiding the model's text mutation and extra
  hands. This track is not pooled with Wan results or presented as evidence
  that Wan improved. Its current motion is visual emphasis, not a worked
  state transition. `results/quality_repair_overlay_v1/` contains the videos,
  manifest and contact sheet; 4/4 pass the artifact integrity gate.
- `eval/rubric_6x6.py` defines six checkable criteria for each of the existing
  six teaching dimensions. Each criterion requires a score, applicability,
  finding and frame evidence; code validates all 36 outputs and aggregates
  criterion means and low-score counts. Use `eval.run_eval --rubric-6x6`.
  Legacy scoring is unchanged. The runtime probe reached the scorer but could
  not obtain a fresh Azure token (AADSTS50173), so no model-based 6×6 result
  has been claimed.

## Next quality gate

Before a 60-case replacement run, review one observable change and an
answer-free opening frame per case. Render exact labels and equations outside
the generative video model or hold them in protected layers. For each candidate,
check conceptual correctness, text stability, motion, intrusions and final
state against the original clip. Publish paired clips and all rejected attempts.
