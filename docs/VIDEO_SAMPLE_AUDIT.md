# `data/videos` sample audit

Audited 2026-10-20. These eight MP4s are 854×480 at 15 fps and run **50.3–97.3 seconds**. Their source scene or rendering scripts are absent from this repository, so this pass does not claim to repair or regenerate the MP4s. The pilot prompts ask for short tasks, and the current research plan evaluates 3–5 second clips. Compare these long code-style videos only after selecting a duration-matched task or as a separate Code2Video reference.

Run `python scripts/audit_generated_videos.py --videos data/videos --out results/video_audit` to reproduce the metadata report and timestamped source-resolution frames. `results/video_audit/audit.jsonl` records machine-checkable facts; the observations below are manual and need expert confirmation before becoming benchmark labels.

| Video | Observable defect in sampled frames | Review priority |
|---|---|---|
| `math_prob_02` | At about 65%, formula glyphs and coloured terms overlap, making the worked derivative unreadable. | Layout and symbolic fidelity |
| `phys_exp_02` | At about 65%, the three rays converge below the drawn principal axis while the narration text says the focus lies on that axis; the rays are not shown parallel before the lens in this shot. | Conceptual correctness and state continuity |
| `chem_exp_01` | At about 65%, ion labels overlap with charge graphics and low-contrast labels; the final lattice scene is an isolated stylised icon rather than a clear NaCl lattice. | Legibility and scientific diagram fidelity |
| `math_prob_01` | The balance analogy and verification occupy small areas amid large empty regions. A learner must read small text to follow the steps. | Layout and pacing |
| `math_exp_01` | Small curve and labels in early shots; the graph changes position and scale across scenes, making the tangent relationship hard to track. | Layout and visual state continuity |
| `math_exp_02` | Triangle construction occupies a small portion of the frame; angle markers and labels are hard to read at playback size. | Layout and proof visibility |
| `chem_prob_02` | The pH scale and formula labels are too small at playback size; some labels cluster on the scale. | Layout and symbolic fidelity |
| `phys_prob_01` | Free-body and substitution diagrams are small; the sequence spends substantial time on prerequisites and an application beyond the requested single acceleration step. | Task scope and diagram legibility |

## Code changes started

1. `scripts/audit_generated_videos.py` now rejects silent duration drift and exports reproducible evidence frames for manual step-level annotation. It deliberately does not infer scientific correctness from pixels.
2. `eval/frame_extractor.py` decodes only sampled frames, so the long samples can be reviewed without loading all frames into memory.
3. `eval/run_eval.py` now uses 832-pixel frames by default for new correctness and layout judgments. A separate detail resolution remains available for clarity and diagram checks when reproducing a 384-pixel core run. Evaluation configuration is stored per case so resume cannot silently reuse scores from a different resolution. Keep old and new scores separate when reporting results.

## Next implementation gates

1. Recover or add the scene source for these eight MP4s before editing their animations. Require a per-scene state specification with fixed positions, minimum text size, safe margins, and no overlapping boxes. Render a still of every scene before the full video.
2. Split long lessons into a separate track. For the 3–5 second benchmark, select one observable change or one checkable algebra step; reject prompts that imply a complete multi-scene lesson.
3. Add expert-reviewed expected states for the target step (equation, charge count, ray intersection) and compare sampled final frames against them. Record `wrong`, `missing`, and `unobservable` separately with timestamps. Do not treat an attractive layout as correctness.
4. After the scene source exists, rerender the affected clips and run the artifact audit, expert defect check, and then the established six-dimension evaluation. A duration fix by speeding up the existing 50–97 second videos would make the text less readable and is not a valid repair.
