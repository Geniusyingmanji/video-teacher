#!/usr/bin/env bash
# Waits for both 5s generation jobs to exit, then runs eval + renders 3 reports:
# - PILOT_REPORT_5s.md           (5B at 5s)
# - PILOT_REPORT_wan13b_5s.md    (1.3B at 5s)
# - PILOT_REPORT_compare_3s_vs_5s.md (length comparison)
# Usage:  finalize_5s.sh <5B_pid> <1.3B_pid>

set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

P5B="${1:?need 5B pid}"; P13="${2:?need 1.3B pid}"

source .envrc
source .venv/bin/activate

echo "[finalize_5s] waiting for 5B pid=$P5B ..."
while kill -0 "$P5B" 2>/dev/null; do sleep 30; done
echo "[finalize_5s] 5B exited at $(date -Is)"

echo "[finalize_5s] waiting for 1.3B pid=$P13 ..."
while kill -0 "$P13" 2>/dev/null; do sleep 30; done
echo "[finalize_5s] 1.3B exited at $(date -Is)"

PROMPTS=data/prompts/pilot_v0_1.jsonl
GEN5B=/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_5s/pilot_v0_1/manifest.jsonl
GEN13=/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b_5s/pilot_v0_1/manifest.jsonl
EVAL5B=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_5s
EVAL13=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b_5s

echo "[finalize_5s] running 5B eval -> $EVAL5B"
python -m eval.run_eval --prompts "$PROMPTS" --manifest "$GEN5B" --out "$EVAL5B" \
  --n-frames 8 --frame-max-px 384 --max-workers 4

echo "[finalize_5s] running 1.3B eval -> $EVAL13"
python -m eval.run_eval --prompts "$PROMPTS" --manifest "$GEN13" --out "$EVAL13" \
  --n-frames 8 --frame-max-px 384 --max-workers 4

echo "[finalize_5s] rendering per-model reports"
python scripts/render_report.py --prompts "$PROMPTS" --manifest "$GEN5B" \
  --eval-dir "$EVAL5B" --out PILOT_REPORT_5s.md --model-label "Wan2.2-TI2V-5B @ 5s"
python scripts/render_report.py --prompts "$PROMPTS" --manifest "$GEN13" \
  --eval-dir "$EVAL13" --out PILOT_REPORT_wan13b_5s.md --model-label "Wan2.1-T2V-1.3B @ 5s"

echo "[finalize_5s] rendering 3s-vs-5s comparison"
python scripts/render_comparison.py \
  --runs \
    "Wan5B-3s=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1" \
    "Wan5B-5s=$EVAL5B" \
    "Wan1.3B-3s=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b" \
    "Wan1.3B-5s=$EVAL13" \
  --out PILOT_REPORT_compare_3s_vs_5s.md

echo "[finalize_5s] saving sample frames at 5s (for visual inspection of long-form drift)"
python scripts/save_sample_frames.py \
  --manifest "$GEN5B" --out /data/zyf/rise-teacher/outputs/sample_frames_5b_5s \
  --n-frames 6 --frame-max-px 512 || true
python scripts/save_sample_frames.py \
  --manifest "$GEN13" --out /data/zyf/rise-teacher/outputs/sample_frames_13b_5s \
  --n-frames 6 --frame-max-px 512 || true

echo "[finalize_5s] DONE at $(date -Is)"
echo "  PILOT_REPORT_5s.md"
echo "  PILOT_REPORT_wan13b_5s.md"
echo "  PILOT_REPORT_compare_3s_vs_5s.md  ★ length-effect study"
