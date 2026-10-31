#!/usr/bin/env bash
set -euo pipefail
base=/mnt/data1/azureuser/video_teacher_round2_grade_probe11
code=/mnt/data1/azureuser/video_teacher_60_20261031/code_main_e301256
py=/home/azureuser/.conda/envs/rise-teacher/bin/python
model=/data/zyf/rise-teacher-code/models/Wan2.2-TI2V-5B-Diffusers
cd "$code"
"$py" scripts/pipeline_preflight.py \
  --prompts "$base/prompts.jsonl" --first-frames "$base/first_frames" \
  --model "$model" --generation-only --strict
export CUDA_VISIBLE_DEVICES=1
exec "$py" -u -m generation.runners.wan_ti2v_runner \
  --prompts "$base/prompts.jsonl" --first-frames "$base/first_frames" \
  --out "$base/videos" --model-path "$model" \
  --num-frames 81 --fps 16 --height 480 --width 832 --steps 30 --seed 42 \
  --cpu-offload --limit 1
