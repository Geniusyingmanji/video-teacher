# TeachQuiz-T / Learning Gain MVP

TeachQuiz-T estimates whether a generated educational video helps a small
student VLM answer case-specific quiz questions.

For cross-model comparisons, freeze the quiz before video generation and use
the exact same file for every model. The runner records its SHA-256 fingerprint
and whether the output is cross-model comparable. Probes built from a model's
own output must be declared with `--probe-origin output_adaptive`; they are
diagnostic only and must not be used to rank models.

For each case:

1. `pre`: answer quiz with no video.
2. `post_video`: answer after seeing frames from the generated video.
3. `random_video`: answer after seeing a mismatched video.

The reported gain is:

```text
learning_gain = post_video - max(pre, random_video)
normalized_gain = learning_gain / (1 - max(pre, random_video))
```

The output additionally reports `raw_gain = post - pre` and
`control_adjusted_gain = post - random_video`. Random controls are selected
deterministically, preferring the same discipline, task type, and difficulty.

Cases with baseline score at or above `--max-baseline-score` are marked invalid
by default because the student already knows the answer.

## Build the pilot quiz

```bash
python scripts/build_teachquiz_pilot.py
```

This writes `data/teachquiz/pilot_v0_1_quiz.jsonl` with 10 cases and 30
multiple-choice questions.

There is also a harder visual-evidence probe:

```bash
python scripts/build_teachquiz_visual_probe.py
```

This writes `data/teachquiz/pilot_v0_1_visual_probe.jsonl` with questions that
ask what appears in the generated frames. Use this when the student model
already knows the concept questions in the no-video condition.

## Smoke test without a local VLM

```bash
python -m eval.run_teachquiz \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --quiz data/teachquiz/pilot_v0_1_quiz.jsonl \
  --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
  --student dummy \
  --out outputs/teachquiz_smoke_dummy_5b \
  --limit 3 --n-frames 2 --frame-max-px 256

python scripts/render_teachquiz_report.py \
  --eval-dir outputs/teachquiz_smoke_dummy_5b \
  --out TEACHQUIZ_SMOKE_REPORT.md \
  --title "TeachQuiz-T smoke report (dummy student)"
```

The dummy student is deterministic and ignores video frames. It is only for
testing the plumbing; expected gain is zero.

## Run with SmolVLM2

After placing a local SmolVLM2 checkpoint on disk:

```bash
python -m eval.run_teachquiz \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --quiz data/teachquiz/pilot_v0_1_quiz.jsonl \
  --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
  --student smolvlm2 \
  --student-model-path models_students/SmolVLM2-2.2B-Instruct \
  --out outputs/teachquiz_smolvlm2_5b \
  --n-frames 8 --frame-max-px 384

python scripts/render_teachquiz_report.py \
  --eval-dir outputs/teachquiz_smolvlm2_5b \
  --out TEACHQUIZ_SMOLVLM2_5B.md \
  --title "TeachQuiz-T pilot — Wan2.2 5B / SmolVLM2"
```

For a slow CPU-only smoke test:

```bash
python -m eval.run_teachquiz \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --quiz data/teachquiz/pilot_v0_1_quiz.jsonl \
  --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
  --student smolvlm2 \
  --student-model-path models_students/SmolVLM2-2.2B-Instruct \
  --out outputs/teachquiz_smolvlm2_smoke \
  --limit 1 --max-questions 1 --skip-random \
  --n-frames 1 --frame-max-px 128 --max-new-tokens 4 \
  --torch-dtype float32
```

## Run with Qwen2.5-VL

After placing a local Qwen2.5-VL checkpoint on disk:

```bash
python -m eval.run_teachquiz \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --quiz data/teachquiz/pilot_v0_1_quiz.jsonl \
  --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
  --student qwen25vl \
  --student-model-path /path/to/Qwen2.5-VL-3B-Instruct \
  --out outputs/teachquiz_qwen25vl3b_5b \
  --n-frames 8 --frame-max-px 384

python scripts/render_teachquiz_report.py \
  --eval-dir outputs/teachquiz_qwen25vl3b_5b \
  --out TEACHQUIZ_QWEN25VL3B_5B.md \
  --title "TeachQuiz-T pilot — Wan2.2 5B / Qwen2.5-VL-3B"
```

## Current limitations

- No unlearning/fine-tuning yet; the `pre` and `random_video` controls filter
  out questions the student already knows.
- No transcript/audio condition yet.
- The pilot quiz is hand-curated and intentionally small.
