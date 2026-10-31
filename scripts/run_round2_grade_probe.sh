#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo"
py=${PYTHON:-python}
model=${MODEL_PATH:-$repo/models/Wan2.2-TI2V-5B-Diffusers}
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

"$py" -m scripts.prepare_round2_grade_probe
if [ ! -f "$model/model_index.json" ]; then
  "$py" -m scripts.fetch_round2_model --out "$model"
fi
"$py" -m scripts.pipeline_preflight \
  --prompts data/round2_grade_probe11/prompts.jsonl \
  --first-frames data/round2_grade_probe11/first_frames \
  --model "$model" --generation-only --strict
"$py" -u -m generation.runners.wan_ti2v_runner \
  --prompts data/round2_grade_probe11/prompts.jsonl \
  --first-frames data/round2_grade_probe11/first_frames \
  --out results/round2_grade_probe11 \
  --model-path "$model" --num-frames 81 --fps 16 \
  --height 480 --width 832 --steps 30 --seed 42 \
  --cpu-offload --limit "${ROUND2_LIMIT:-1}"
