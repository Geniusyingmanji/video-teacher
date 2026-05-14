#!/usr/bin/env bash
# Run after both pipelines complete: produces PILOT_REPORT_compare.md.
set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

FINALIZE_PID="${1:-}"
WAN13_PID="${2:-}"

source .envrc
source .venv/bin/activate

if [ -n "$FINALIZE_PID" ]; then
  echo "[compare] waiting for finalize pid=$FINALIZE_PID ..."
  while kill -0 "$FINALIZE_PID" 2>/dev/null; do sleep 30; done
  echo "[compare] finalize done at $(date -Is)"
fi
if [ -n "$WAN13_PID" ]; then
  echo "[compare] waiting for wan13b pipeline pid=$WAN13_PID ..."
  while kill -0 "$WAN13_PID" 2>/dev/null; do sleep 30; done
  echo "[compare] wan13b pipeline done at $(date -Is)"
fi

WAN5B=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1
WAN13B=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b

if [ -f "$WAN5B/aggregate.json" ] && [ -f "$WAN13B/aggregate.json" ]; then
  python scripts/render_comparison.py \
    --runs "Wan2.2-TI2V-5B=$WAN5B" "Wan2.1-T2V-1.3B=$WAN13B" \
    --out PILOT_REPORT_compare.md
  echo "[compare] wrote PILOT_REPORT_compare.md"
else
  echo "[compare] one of the two eval runs missing; aborting compare"
  ls -la "$WAN5B" "$WAN13B" 2>&1 || true
fi
