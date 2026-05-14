#!/usr/bin/env bash
# Second-model pipeline: Wan 2.1 1.3B for comparison with the 5B.
# Waits for the download PID to finish, then runs gen on GPU 2 + eval.

set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

DL_PID="${1:-}"
if [ -z "$DL_PID" ]; then echo "ERR: missing dl_pid"; exit 1; fi

source .envrc
source .venv/bin/activate

echo "[wan13b] waiting for download pid=$DL_PID ..."
while kill -0 "$DL_PID" 2>/dev/null; do sleep 20; done
echo "[wan13b] download exited at $(date -Is)"

# Verify weights exist
test -f /data/zyf/rise-teacher/models/Wan2.1-T2V-1.3B-Diffusers/model_index.json \
  || { echo "[wan13b] model_index.json missing — abort"; exit 2; }

GEN_OUT=/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1
EVAL_OUT=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b

echo "[wan13b] launching generation on GPU 2 -> $GEN_OUT"
CUDA_VISIBLE_DEVICES=2 python -m generation.runners.wan_runner \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --out "$GEN_OUT" \
  --model-path /data/zyf/rise-teacher/models/Wan2.1-T2V-1.3B-Diffusers \
  --num-frames 49 --height 480 --width 832 --steps 30 --guidance-scale 5.0 --seed 42 \
  --dtype bfloat16

echo "[wan13b] gen done at $(date -Is). Running core eval -> $EVAL_OUT"
python -m eval.run_eval \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest "$GEN_OUT/manifest.jsonl" \
  --out "$EVAL_OUT" \
  --n-frames 8 --frame-max-px 384 --max-workers 4

echo "[wan13b] rendering report -> PILOT_REPORT_wan13b.md"
python scripts/render_report.py \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --manifest "$GEN_OUT/manifest.jsonl" \
  --eval-dir "$EVAL_OUT" \
  --out PILOT_REPORT_wan13b.md \
  --model-label "Wan2.1-T2V-1.3B"

echo "[wan13b] DONE at $(date -Is)"
