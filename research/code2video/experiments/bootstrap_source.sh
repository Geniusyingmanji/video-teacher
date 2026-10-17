#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -d "$task_root/Code2Video/.git" ]]; then
  git clone https://github.com/showlab/Code2Video.git "$task_root/Code2Video"
fi
git -C "$task_root/Code2Video" checkout 1142d8e14cdc2806df85aedb0fbb5dca474caa0f
if git -C "$task_root/Code2Video" apply --reverse --check "$task_root/experiments/code2video-local.patch" 2>/dev/null; then
  echo "Local patch already applied."
else
  git -C "$task_root/Code2Video" apply --check "$task_root/experiments/code2video-local.patch"
  git -C "$task_root/Code2Video" apply "$task_root/experiments/code2video-local.patch"
fi
for resource in assets json_files prompts; do
  if [[ ! -e "$task_root/Code2Video/src/$resource" ]]; then
    ln -s "../$resource" "$task_root/Code2Video/src/$resource"
  fi
done
