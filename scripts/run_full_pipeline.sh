#!/bin/bash
# Full pipeline: TI2V video generation + evaluation with first-frame images
# NOTE: Only Wan2.2-TI2V-5B supports image conditioning.
#       Wan2.1-T2V-1.3B is text-only (VAE channel mismatch for TI2V).
#       Existing T2V results in wan2_2_ti2v_5b/ and wan2_1_t2v_1_3b/ serve as baselines.
# Usage: bash scripts/run_full_pipeline.sh
set -euo pipefail

cd /home/azureuser/workspace-gzy/zyf/rise-teacher
source .venv/bin/activate
source .envrc 2>/dev/null || true

PROMPTS=data/prompts/pilot_v0_1.jsonl
FIRST_FRAMES=data/first_frames
GEN_BASE=/data/zyf/rise-teacher/generations
EVAL_BASE=/data/zyf/rise-teacher/outputs
QUIZ=data/teachquiz/pilot_v0_1_quiz.jsonl

echo "=========================================="
echo "  rise-teacher full pipeline (TI2V)"
echo "=========================================="

# ---- Phase 3: Wan2.2-5B TI2V 3s ----
echo ""
echo "[PHASE 3] Wan2.2-5B TI2V 3s (49 frames @ fps=16)"
CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_ti2v_runner \
    --prompts $PROMPTS \
    --first-frames $FIRST_FRAMES \
    --out $GEN_BASE/wan2_2_ti2v_5b_ff/pilot_v0_1 \
    --model-path /data/zyf/rise-teacher/models/Wan2.2-TI2V-5B-Diffusers \
    --num-frames 49 --height 480 --width 832 --steps 30 \
    --fps 16 --seed 42

# ---- Phase 4: Wan2.2-5B TI2V 5s ----
echo ""
echo "[PHASE 4] Wan2.2-5B TI2V 5s (81 frames @ fps=16)"
CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_ti2v_runner \
    --prompts $PROMPTS \
    --first-frames $FIRST_FRAMES \
    --out $GEN_BASE/wan2_2_ti2v_5b_ff_5s/pilot_v0_1 \
    --model-path /data/zyf/rise-teacher/models/Wan2.2-TI2V-5B-Diffusers \
    --num-frames 81 --height 480 --width 832 --steps 30 \
    --fps 16 --seed 42

echo ""
echo "=========================================="
echo "  TI2V video generation complete!"
echo "=========================================="

# ---- Phase 5: Standard evaluation (6 dims, extended) on new TI2V configs ----
echo ""
echo "[PHASE 5] Running standard evaluation (6 dims) on 2 TI2V configs"

for config in wan2_2_ti2v_5b_ff wan2_2_ti2v_5b_ff_5s; do
    echo ""
    echo "  Evaluating: $config"
    python -m eval.run_eval \
        --prompts $PROMPTS \
        --manifest $GEN_BASE/$config/pilot_v0_1/manifest.jsonl \
        --out $EVAL_BASE/eval_${config} \
        --extended \
        --n-frames 8 --frame-max-px 384
done

echo ""
echo "=========================================="
echo "  Standard evaluations complete!"
echo "=========================================="

# ---- Phase 6: TeachQuiz-T evaluation ----
echo ""
echo "[PHASE 6] Running TeachQuiz-T (Qwen3-VL-2B) on TI2V 3s config"

if [ ! -f "$QUIZ" ]; then
    echo "  Quiz file not found, building..."
    python scripts/build_teachquiz_pilot.py
fi

for config in wan2_2_ti2v_5b_ff; do
    echo ""
    echo "  Building visual probes for $config..."
    python scripts/build_visual_probe_from_frames.py \
        --prompts $PROMPTS \
        --manifest $GEN_BASE/$config/pilot_v0_1/manifest.jsonl \
        --out data/teachquiz/visual_probe_auto_${config}.jsonl \
        --n-frames 4 --frame-max-px 256 \
        2>/dev/null || echo "  (visual probe build skipped or failed)"

    PROBE=data/teachquiz/visual_probe_auto_${config}.jsonl
    if [ ! -f "$PROBE" ]; then
        PROBE=$QUIZ
    fi
    echo ""
    echo "  TeachQuiz: $config"
    CUDA_VISIBLE_DEVICES=3 python -m eval.run_teachquiz \
        --prompts $PROMPTS \
        --quiz $PROBE \
        --manifest $GEN_BASE/$config/pilot_v0_1/manifest.jsonl \
        --student qwen3vl \
        --out $EVAL_BASE/teachquiz_qwen3vl_${config} \
        --n-frames 8 --frame-max-px 384
done

echo ""
echo "=========================================="
echo "  TeachQuiz evaluation complete!"
echo "=========================================="

# ---- Phase 7: Generate reports ----
echo ""
echo "[PHASE 7] Generating analysis reports"
python scripts/gen_paper_stats.py 2>/dev/null || echo "  (paper stats skipped)"
echo ""
echo "=========================================="
echo "  FULL PIPELINE COMPLETE"
echo "=========================================="
