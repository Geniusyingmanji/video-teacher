#!/usr/bin/env bash
# Wait for finalize_v0_2_high.sh to complete, then update paper stats.
# Usage: bash scripts/post_finalize_v0_2_high.sh
set -euo pipefail
cd /home/azureuser/workspace-gzy/zyf/rise-teacher

source .envrc
source .venv/bin/activate

echo "[post-finalize] waiting for finalize_v0_2_high.sh to finish ..."
until grep -q "\[finalize_v0_2_high\] DONE" /tmp/finalize_v0_2_high.log 2>/dev/null; do
    sleep 30
done
echo "[post-finalize] finalize done at $(date -Is)"

echo "[post-finalize] running gen_paper_stats.py ..."
python scripts/gen_paper_stats.py

echo "[post-finalize] checking v0.2 high aggregate ..."
python3 -c "
import json
d = json.load(open('/data/zyf/rise-teacher/outputs/eval_pilot_v0_2_high/aggregate.json'))
print(f'  n={d[\"n_total\"]}, mean={d[\"mean_aggregate\"]:.3f}')
pd = d.get('per_difficulty', {})
for diff, v in sorted(pd.items()):
    print(f'  {diff}: {v[\"mean\"]:.3f} (n={v[\"n\"]})')
"

echo "[post-finalize] printing dim correlation ..."
cat analysis/dim_correlation_v0_2_high.md 2>/dev/null || echo "  dim_correlation_v0_2_high.md not found"

echo "[post-finalize] printing PILOT_REPORT_v0_2_high summary ..."
head -40 PILOT_REPORT_v0_2_high.md 2>/dev/null || echo "  PILOT_REPORT_v0_2_high.md not found"

echo "[post-finalize] ALL DONE at $(date -Is)"
echo "  paper_stats.md updated with Wan1.3B-v0.2-high"
echo "  analysis/dim_correlation_v0_2_high.md ready"
echo "  PILOT_REPORT_v0_2_high.md ready"
