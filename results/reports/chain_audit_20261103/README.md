# Chain quality audit evidence — 2026-11-03

`previous_completion.json` and `previous_cases.json` refer to the previous two-GPU
contract-v4 / scoring-v5 run: 6 generated, 2 quality-passed, out of 10.
The seven JPG sheets (six accepted renders and one rejected ECG diagnostic render) show actual source-resolution frames 1, 15, 30, 45, 60, 75.
They support the visual review, not a claim of complete video inspection by a human expert.

`control_negative.json` and `control_positive.json` apply the same current Markov
task to actual wrong/omitted-answer and repaired videos, respectively. Both expected
outcomes match. They preserve video hashes, code identity and judge configuration.
The sampling is 3 FPS including the exact last frame. No historical score was changed.

`medical_task_omissions.json` rejects the nephron clip for missing sequential labeling and visible flow direction. The test records concrete obligations and evidence, independently of the old 85-point score.

`chemistry_layout_regression.json` comes from a real rerender of the old chemical
scene: timing passes but two captions are occluded by the molecule image. The
new guard rejects it. `preflight400.json` covers structure and asset resolution
for all current 400 tasks; this is not 400 video generations or semantic approvals.

`exploratory_task_reviews.json` preserves summaries of the earlier investigation,
including erroneous judgments that motivated changes. These are not final scores
or calibration ground truth. Raw exploratory responses and all renders stay local.

Reproduce controls with `scripts/validate_completion_controls.py`, providing
`--prompts`, `--case`, `--negative`, `--positive`, and `--out`; run task-only reviews
with `scripts/review_task_completion.py --run ... --out ... [--ids ...]`.
Configure a vision judge using the same `VIDEO_TEACHER_*` variables as evaluation.
Run all regression checks with `python -m unittest discover -s tests -v` in the
Manim environment with `requirements-local-generation.txt` installed.

For policy details and remaining limitations, see
[`docs/CHAIN_QUALITY_AUDIT_2026-11-03.md`](../../../docs/CHAIN_QUALITY_AUDIT_2026-11-03.md).
