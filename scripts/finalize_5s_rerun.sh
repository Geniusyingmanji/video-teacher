#!/usr/bin/env bash
# Re-runs the 5s evals with retry logic (429 errors fixed), then rebuilds reports.
# Usage: finalize_5s_rerun.sh  (no args; both evals run sequentially to avoid API contention)

set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

source .envrc
source .venv/bin/activate

PROMPTS=data/prompts/pilot_v0_1.jsonl
GEN5B=/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_5s/pilot_v0_1/manifest.jsonl
GEN13=/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b_5s/pilot_v0_1/manifest.jsonl
EVAL5B=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_5s
EVAL13=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b_5s

echo "[rerun] 5B 5s eval -> $EVAL5B"
PYTHONUNBUFFERED=1 python -m eval.run_eval \
  --prompts "$PROMPTS" --manifest "$GEN5B" --out "$EVAL5B" \
  --n-frames 8 --frame-max-px 384 --max-workers 2

echo "[rerun] 1.3B 5s eval -> $EVAL13"
PYTHONUNBUFFERED=1 python -m eval.run_eval \
  --prompts "$PROMPTS" --manifest "$GEN13" --out "$EVAL13" \
  --n-frames 8 --frame-max-px 384 --max-workers 2

echo "[rerun] rendering per-model reports"
python scripts/render_report.py --prompts "$PROMPTS" --manifest "$GEN5B" \
  --eval-dir "$EVAL5B" --out PILOT_REPORT_5s.md --model-label "Wan2.2-TI2V-5B @ 5s"
python scripts/render_report.py --prompts "$PROMPTS" --manifest "$GEN13" \
  --eval-dir "$EVAL13" --out PILOT_REPORT_wan13b_5s.md --model-label "Wan2.1-T2V-1.3B @ 5s"

echo "[rerun] rendering 3s-vs-5s comparison"
python scripts/render_comparison.py \
  --runs \
    "Wan5B-3s=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1" \
    "Wan5B-5s=$EVAL5B" \
    "Wan1.3B-3s=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b" \
    "Wan1.3B-5s=$EVAL13" \
  --out PILOT_REPORT_compare_3s_vs_5s.md

echo "[rerun] DONE at $(date -Is)"
echo "  PILOT_REPORT_5s.md"
echo "  PILOT_REPORT_wan13b_5s.md"
echo "  PILOT_REPORT_compare_3s_vs_5s.md"
