# Qwen 10-case strict five-second smoke run

The runner samples the same ten IDs from `candidate_400.jsonl` with seed
`20261102`. It preserves the complete current task record, including its
prompt, expected concepts, visual elements, narrative order, task prohibitions,
audience and rubric, in every planning, storyboard, coding and repair request.
It does not replace the current task with `original_prompt_text`, which may
describe an earlier task before curation.

The old five-minute planning template and redraw-from-reference storyboard
template are replaced for strict runs. One scene must explain the task in
five seconds. The renderer measures the complete animation event sequence,
then allocates integer frame budgets to those events and rerenders it. It
reserves one second for the final result and, for source-image tasks, one
second for the unchanged initial image. It does not trim an existing video.
The decoded result must have exactly 75 frames at 15 fps. A long or complex
explanation may still be unreadable in five seconds; this is a quality failure,
not permission to remove task requirements.

Source-image tasks receive the original image in every model request. The
renderer supplies the unchanged image as a fixed background. The storyboard
must declare normalized edit rectangles with total area at most 25% of the
canvas. Validation checks the initial frame against the supplied image and
compares every subsequent frame outside those rectangles with the initial
frame, with small allowances for rasterization and encoding. Missing images,
overbroad rectangles, changed backgrounds, incomplete scenes and incorrect
duration fail the run. This preserves the source outside declared edits; it
does not prove the edits are scientifically correct or correctly localized.
The eight-axis self-evaluation and saved evidence frames remain necessary.

## Run on this model server

The Code2Video checkout and Manim environment described in the research README
are prerequisites. `sample10-runtime-fixes.patch` applies after the existing
`code2video-local.patch`; it fixes safe filenames, invalid eager mutations in
`Scene.play`, missing-line-number repair errors and render-timeout reporting.

```bash
git -C research/code2video/Code2Video apply ../experiments/sample10-runtime-fixes.patch
CUDA_VISIBLE_DEVICES=0 QWEN_VISION=1 QWEN_MAX_SEQS=2 \
  bash research/code2video/experiments/start_qwen38.sh
# In a separate shell, using the existing Code2Video environment:
/root/code2video-env/bin/python -u scripts/run_qwen_sample10.py
```

The default output is `results/qwen38_gpu0_sample10_strict5s_20261102/`.
It is separate from the earlier nonconforming run. Each generated case has a
`task_contract.json`, actual model requests/responses, outline, storyboard,
code, timing-pass video, final video and strict diagnostics in the local
Code2Video `CASES` directory. The result JSON links to that directory.
`complete` in a generation result means structural and timing validation,
including source preservation when applicable, passed. It is not a semantic
quality pass. Batch `completion.json` requires ten accepted generations and
ten valid eight-axis evaluations. The evaluator is explicitly marked as a
debug subset and same-model self-evaluation, not an independent benchmark
ranking. Old videos are never reused as strict-run outputs.

```bash
/root/code2video-env/bin/python -m unittest discover -s tests -p test_strict_video_contract.py -v
/root/code2video-env/bin/python -m unittest discover -s tests -p test_benchmark_v2.py -v
```

The render regression checks a real 75-frame source-preserving video and
rejects a video that alters the full source background.
