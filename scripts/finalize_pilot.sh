#!/usr/bin/env bash
# Waits for the Wan generation PID to exit, then runs eval + render_report.
# Usage:  finalize_pilot.sh <generation_pid>
#
# Idempotent: if eval was already run it will resume from per_case.jsonl.

set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

GEN_PID="${1:-}"
if [ -z "$GEN_PID" ]; then
  echo "ERR: missing gen_pid"
  exit 1
fi

source .envrc
source .venv/bin/activate

echo "[finalize] waiting for generation pid=$GEN_PID to exit ..."
while kill -0 "$GEN_PID" 2>/dev/null; do
  sleep 30
done
echo "[finalize] generation pid=$GEN_PID exited at $(date -Is)"

OUT=/data/zyf/rise-teacher/outputs/eval_pilot_v0_1
MANIFEST=/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl
PROMPTS=data/prompts/pilot_v0_1.jsonl

echo "[finalize] running core eval -> $OUT"
python -m eval.run_eval \
  --prompts "$PROMPTS" --manifest "$MANIFEST" --out "$OUT" \
  --n-frames 8 --frame-max-px 384 --max-workers 4

echo "[finalize] running extended eval -> ${OUT}_extended"
python -m eval.run_eval --extended \
  --prompts "$PROMPTS" --manifest "$MANIFEST" --out "${OUT}_extended" \
  --n-frames 8 --frame-max-px 384 --max-workers 4 || echo "[finalize] extended eval failed (non-fatal)"

echo "[finalize] rendering report"
python scripts/render_report.py \
  --prompts "$PROMPTS" --manifest "$MANIFEST" --eval-dir "$OUT" \
  --out PILOT_REPORT.md --model-label "Wan2.2-TI2V-5B"

# Also render the extended report
if [ -d "${OUT}_extended" ]; then
  python scripts/render_report.py \
    --prompts "$PROMPTS" --manifest "$MANIFEST" --eval-dir "${OUT}_extended" \
    --out PILOT_REPORT_extended.md --model-label "Wan2.2-TI2V-5B (5-dim)" || true
fi

echo "[finalize] saving sample frames for top/bottom cases"
python scripts/save_sample_frames.py \
  --manifest "$MANIFEST" --out /data/zyf/rise-teacher/outputs/sample_frames \
  --n-frames 4 --frame-max-px 512 || true

echo "[finalize] DONE at $(date -Is)"
echo "    PILOT_REPORT.md            -> overall summary"
echo "    PILOT_REPORT_extended.md   -> 5-dim summary"
echo "    $OUT/aggregate.json"
echo "    /data/zyf/rise-teacher/outputs/sample_frames/  -> per-case frame previews"
