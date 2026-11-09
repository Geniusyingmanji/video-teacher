#!/usr/bin/env bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
IFS=',' read -ra task_gpu_ids <<< "$CUDA_VISIBLE_DEVICES"
for task_gpu_id in "${task_gpu_ids[@]}"; do
  if [[ ! "$task_gpu_id" =~ ^[0-3]$ ]]; then
    echo "Expected a local GPU ID from 0 through 3." >&2
    exit 64
  fi
done
export VLLM_USE_FLASHINFER_SAMPLER=0
modality_args=(--language-model-only)
if [[ "${QWEN_VISION:-0}" == "1" ]]; then
  modality_args=(--limit-mm-per-prompt '{"image":24,"video":0}'
    --mm-processor-kwargs '{"size":{"longest_edge":262144,"shortest_edge":4096}}')
fi
exec "${QWEN_PYTHON:-/root/qwen38-env/bin/python}" -m vllm.entrypoints.openai.api_server \
  --model /root/models/Qwen3.8-27B --served-model-name qwen3.8-27b \
  --host 127.0.0.1 --port "${QWEN_PORT:-8000}" --dtype bfloat16 \
  --max-model-len 32768 --max-num-seqs "${QWEN_MAX_SEQS:-16}" --gpu-memory-utilization 0.9 \
  --enforce-eager --reasoning-parser qwen3 \
  --structured-outputs-config '{"backend":"xgrammar","disable_any_whitespace":true}' \
  "${modality_args[@]}"
