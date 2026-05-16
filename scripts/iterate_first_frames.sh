#!/usr/bin/env bash
# Iteratively regenerate first frames until PASS or max iters reached.
#
# Loop: for each iter, regen FAIL cases with FLUX.1-dev + check.
# Stops when no FAIL cases left, or after MAX_ITERS rounds.
#
# Usage:
#     CUDA_VISIBLE_DEVICES=2 bash scripts/iterate_first_frames.sh [MAX_ITERS]
set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher
source .envrc
source .venv/bin/activate
export HF_HUB_OFFLINE=1  # FLUX.1-dev is gated; use the cached snapshot only

MAX_ITERS="${1:-3}"
PROMPTS=data/prompts/pilot_v0_1.jsonl
FF_DIR=data/first_frames
CHECK_REPORT="$FF_DIR/check_report.jsonl"

echo "[iter] start at $(date -Is) — max ${MAX_ITERS} iterations"

prev_fail_count() {
    if [[ -f "$CHECK_REPORT" ]]; then
        grep -c '"verdict": "FAIL"' "$CHECK_REPORT" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

# Snapshot starting state
START_FAILS=$(prev_fail_count)
echo "[iter] starting FAIL count: ${START_FAILS} / 60"

for iter in $(seq 1 "$MAX_ITERS"); do
    N_FAIL=$(prev_fail_count)
    echo ""
    echo "==== iter ${iter} / ${MAX_ITERS} ===="
    echo "[iter ${iter}] current FAIL = ${N_FAIL}"
    if [[ "$N_FAIL" -eq 0 ]]; then
        echo "[iter ${iter}] no FAIL cases left — stopping"
        break
    fi

    # 1. Regenerate FAILs (overwrites originals after backup)
    BACKUP="$FF_DIR/_backup_before_iter${iter}"
    echo "[iter ${iter}] regenerating ${N_FAIL} cases with FLUX.1-dev..."
    python scripts/regen_failed_frames.py \
        --prompts "$PROMPTS" \
        --check-report "$CHECK_REPORT" \
        --first-frames "$FF_DIR" \
        --backup-dir "$BACKUP" \
        --iter "$iter" \
        --steps 28 \
        --guidance-scale 3.5

    # 2. Move old check report aside and re-check (only newly-overwritten ones)
    OLD_REPORT="$FF_DIR/check_report_iter$((iter-1)).jsonl"
    mv "$CHECK_REPORT" "$OLD_REPORT"
    # We re-check all cases so PASSes stay PASS (already-fine images skipped if we limit)
    # Simplest: re-check everything against the current frames.
    echo "[iter ${iter}] re-checking all 60 frames against requirements..."
    python scripts/check_first_frames.py \
        --prompts "$PROMPTS" \
        --first-frames "$FF_DIR" \
        --out "$CHECK_REPORT"

    NEW_FAIL=$(prev_fail_count)
    DELTA=$((N_FAIL - NEW_FAIL))
    echo "[iter ${iter}] result: FAIL ${N_FAIL} -> ${NEW_FAIL} (Δ=${DELTA})"
done

FINAL_FAIL=$(prev_fail_count)
FINAL_PASS=$((60 - FINAL_FAIL))
echo ""
echo "==== ALL DONE at $(date -Is) ===="
echo "[iter] starting PASS rate: $((60 - START_FAILS)) / 60"
echo "[iter]   ending PASS rate: ${FINAL_PASS} / 60"
echo "[iter] backups in: $FF_DIR/_backup_before_iter*"
echo "[iter] history reports: $FF_DIR/check_report_iter*.jsonl"
