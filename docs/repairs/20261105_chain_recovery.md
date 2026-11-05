# Generation and evaluation recovery, 2026-11-05

The first fixed-ten round stopped before finalizing three rendered videos. Two
physics cases exhausted generation attempts because narration rewrites remained
shorter than their chapter slots. The old rewrite prompt imposed a fixed word
ceiling inconsistent with the measured voice speed and required minimum length.

Narration now calibrates rewrite length from measured speech and script words.
Drafts can slow speech to at least 0.8x or speed it up to at most 1.35x using
FFmpeg atempo. All speech is preserved; chapter boundaries, non-silence and total
coverage checks remain active. Large duration errors still require rewriting.

Workers now save evaluation checkpoints, retain completed windows and axes, and
reuse a completed video only after checking the contract, frame count and FPS.
A process crash gets two bounded restarts on the same artifacts. Failed cases
and original rounds remain intact.

Task completion uses per-requirement structured schemas with enumerated local
citations. Unresolved broad consistency checks receive a literal per-statement
verification. Uncertainty still invalidates the score; low valid scores are not
replaced by defaults. The evaluation fingerprint includes both verification
implementations. FFmpeg falls back to the evaluator interpreter's bin directory
when it is absent from PATH.

Validation: 64 existing regression tests passed, plus three crash/render-reuse
tests and one bounded speech slowdown regression. Actual repaired physics videos
are under results/optimization_20261105/chain_repair_validation. Both narrated
videos passed exact duration/frame checks with approximately 90.8% speech
coverage. The convex-lens video also exercises the live evaluation chain; its
checkpoint and final report are stored beside the video. These measurements do
not constitute teaching-quality acceptance.
