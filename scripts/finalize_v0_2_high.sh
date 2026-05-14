#!/usr/bin/env bash
# Wait for the v0.2 high-difficulty generation job to finish,
# then run eval + render a report.
# Usage: finalize_v0_2_high.sh <gen_pid>
set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

source .envrc
source .venv/bin/activate

GEN_PID="${1:?need gen pid}"
echo "[finalize_v0_2_high] waiting for gen pid=$GEN_PID ..."
while kill -0 "$GEN_PID" 2>/dev/null; do sleep 30; done
echo "[finalize_v0_2_high] gen exited at $(date -Is)"

PROMPTS=data/prompts/pilot_v0_2.jsonl
MANIFEST=/data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_2_high/manifest.jsonl
EVAL_DIR=/data/zyf/rise-teacher/outputs/eval_pilot_v0_2_high

echo "[finalize_v0_2_high] checking manifest ..."
python3 -c "
import json
m = [json.loads(l) for l in open('$MANIFEST')]
ok = sum(1 for r in m if r.get('status')=='ok')
err = len(m) - ok
print(f'  {ok} ok, {err} failed')
"

echo "[finalize_v0_2_high] running eval -> $EVAL_DIR"
PYTHONUNBUFFERED=1 python -m eval.run_eval \
  --prompts "$PROMPTS" --manifest "$MANIFEST" --out "$EVAL_DIR" \
  --n-frames 8 --frame-max-px 384 --max-workers 2

echo "[finalize_v0_2_high] rendering report"
python scripts/render_report.py \
  --prompts "$PROMPTS" --manifest "$MANIFEST" \
  --eval-dir "$EVAL_DIR" --out PILOT_REPORT_v0_2_high.md \
  --model-label "Wan1.3B @ v0.2 high-difficulty"

echo "[finalize_v0_2_high] dim correlation"
python scripts/dim_correlation.py \
  --per-case "$EVAL_DIR/per_case.jsonl" \
  --label "Wan1.3B-v0.2-high" \
  --out analysis/dim_correlation_v0_2_high.md

echo "[finalize_v0_2_high] DONE at $(date -Is)"
echo "  PILOT_REPORT_v0_2_high.md"
echo "  analysis/dim_correlation_v0_2_high.md"
