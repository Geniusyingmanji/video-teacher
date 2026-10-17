#!/usr/bin/env bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export VLLM_USE_FLASHINFER_SAMPLER=0
exec /root/qwen38-env/bin/python -m vllm.entrypoints.openai.api_server \
  --model /root/models/Qwen3.8-27B --served-model-name qwen3.8-27b \
  --host 127.0.0.1 --port "${QWEN_PORT:-8000}" --dtype bfloat16 \
  --max-model-len 32768 --max-num-seqs "${QWEN_MAX_SEQS:-16}" --gpu-memory-utilization 0.9 \
  --enforce-eager --reasoning-parser qwen3 --language-model-only
