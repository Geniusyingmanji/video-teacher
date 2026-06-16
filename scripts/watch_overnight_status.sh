#!/usr/bin/env bash
# Periodically log long-data and first-frame regeneration status.
set -euo pipefail

DATA_PREFIX="${1:?data prefix required}"
FF_ITER="${2:?first-frame iter required}"
LOG_PATH="${3:?log path required}"
INTERVAL_SECONDS="${4:-600}"
ROUNDS="${5:-60}"

cd /home/azureuser/workspace-gzy/zyf/rise-teacher
mkdir -p "$(dirname "$LOG_PATH")"

for _ in $(seq 1 "$ROUNDS"); do
  {
    date -Is
    echo "DATA_STATUS"
    cat "data/prompts/longrun_${DATA_PREFIX}/status.json" 2>/dev/null || true
    echo "FF_REGEN"
    python3 - "$FF_ITER" <<'PY'
import collections
import json
import pathlib
import sys

ff_iter = sys.argv[1]
manifest = pathlib.Path(f"data/first_frames/manifest_regen_{ff_iter}.jsonl")
rows = [json.loads(line) for line in manifest.open()] if manifest.exists() else []
print(json.dumps({
    "regen_rows": len(rows),
    "regen_status": dict(collections.Counter(row.get("status") for row in rows)),
    "last_ids": [row.get("id") for row in rows[-5:]],
}, ensure_ascii=False))

report = pathlib.Path(f"data/first_frames/check_report_{ff_iter}.jsonl")
if report.exists():
    checks = [json.loads(line) for line in report.open() if line.strip()]
    print(json.dumps({
        "check_rows": len(checks),
        "check_verdicts": dict(collections.Counter(row.get("verdict") for row in checks)),
    }, ensure_ascii=False))
PY
    echo "----"
  } | tee -a "$LOG_PATH"
  sleep "$INTERVAL_SECONDS"
done
