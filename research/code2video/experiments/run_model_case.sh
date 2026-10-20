#!/usr/bin/env bash
set -euo pipefail
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="/root/code2video-env/bin:$PATH"
export LOCAL_BASE_URL="${LOCAL_BASE_URL:-http://127.0.0.1:8000/v1}"
export LOCAL_MODEL="${LOCAL_MODEL:-qwen3.8-27b}"
exec python -u "$task_dir/run_model_case.py" "$@"
