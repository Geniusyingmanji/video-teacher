#!/usr/bin/env bash
# Matched Wan5B T2V/TI2V research run. Requires a reviewed shared quiz and GPU.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PROMPTS="${PROMPTS:-data/prompts/pilot_v0_1.jsonl}"
FIRST_FRAMES="${FIRST_FRAMES:-data/first_frames}"
QUIZ="${QUIZ:-data/teachquiz/pilot_v0_1_quiz.jsonl}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
GEN_BASE="${GEN_BASE:-$PROJECT_DIR/results/new_generations/$RUN_ID}"
EVAL_BASE="${EVAL_BASE:-$PROJECT_DIR/results/new_evaluations/$RUN_ID}"
WAN_MODEL_PATH="${WAN_MODEL_PATH:-$PROJECT_DIR/models/Wan2.2-TI2V-5B-Diffusers}"
STUDENT_MODEL_PATH="${STUDENT_MODEL_PATH:-$PROJECT_DIR/models/Qwen3-VL-2B-Instruct}"
SEED="${SEED:-42}"
STEPS="${STEPS:-30}"
RUN_MODE="${RUN_MODE:-full}"

if [[ "$RUN_MODE" != "full" && "$RUN_MODE" != "generation-only" ]]; then
    echo "RUN_MODE must be full or generation-only" >&2
    exit 2
fi

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--check" ) ]]; then
    echo "Usage: bash scripts/run_full_pipeline.sh [--check]" >&2
    exit 2
fi

preflight_args=()
if [[ "$RUN_MODE" == "generation-only" ]]; then preflight_args+=(--generation-only); fi
if [[ -n "${FIRST_FRAME_REVIEW:-}" ]]; then
    preflight_args+=(--first-frame-review "$FIRST_FRAME_REVIEW")
fi
python -m scripts.pipeline_preflight \
    --prompts "$PROMPTS" --first-frames "$FIRST_FRAMES" --quiz "$QUIZ" \
    --model "$WAN_MODEL_PATH" --student-model "$STUDENT_MODEL_PATH" \
    "${preflight_args[@]}" --strict

if [[ "${1:-}" == "--check" ]]; then exit 0; fi

mkdir -p "$GEN_BASE" "$EVAL_BASE"
for duration in 3 5; do
    if [[ "$duration" == 3 ]]; then frames=73; else frames=121; fi
    for arm in t2v ti2v; do
        out="$GEN_BASE/wan5b_${arm}_${duration}s"
        if [[ "$arm" == ti2v ]]; then
            python -m generation.runners.wan_ti2v_runner \
                --prompts "$PROMPTS" --first-frames "$FIRST_FRAMES" \
                --out "$out" --model-path "$WAN_MODEL_PATH" \
                --num-frames "$frames" --fps 24 --height 480 --width 832 \
                --steps "$STEPS" --seed "$SEED"
        else
            python -m generation.runners.wan_runner \
                --prompts "$PROMPTS" --out "$out" --model-path "$WAN_MODEL_PATH" \
                --num-frames "$frames" --fps 24 --height 480 --width 832 \
                --steps "$STEPS" --seed "$SEED"
        fi
        python -m scripts.pipeline_artifacts --prompts "$PROMPTS" \
            --manifest "$out/manifest.jsonl" --kind generation

        if [[ "$RUN_MODE" == "generation-only" ]]; then continue; fi

        scored="$EVAL_BASE/wan5b_${arm}_${duration}s"
        python -m eval.run_eval --prompts "$PROMPTS" \
            --manifest "$out/manifest.jsonl" --out "$scored/standard" \
            --extended --sample-fps 2 --frame-max-px 832 --detail-frame-max-px 832
        python -m scripts.pipeline_artifacts --prompts "$PROMPTS" \
            --manifest "$scored/standard/per_case.jsonl" --kind standard

        python -m eval.run_teachquiz --prompts "$PROMPTS" --quiz "$QUIZ" \
            --probe-origin frozen_shared --manifest "$out/manifest.jsonl" \
            --student qwen3vl --student-model-path "$STUDENT_MODEL_PATH" \
            --out "$scored/teachquiz" --sample-fps 2 --frame-max-px 832
        python -m scripts.pipeline_artifacts --prompts "$PROMPTS" \
            --manifest "$scored/teachquiz/per_case.jsonl" --kind teachquiz
    done
    if [[ "$RUN_MODE" == "generation-only" ]]; then continue; fi
    python scripts/compare_standard_eval.py \
        --left "$EVAL_BASE/wan5b_ti2v_${duration}s/standard/per_case.jsonl" \
        --right "$EVAL_BASE/wan5b_t2v_${duration}s/standard/per_case.jsonl" \
        --left-label "TI2V-${duration}s" --right-label "T2V-${duration}s" \
        --out "$EVAL_BASE/paired_ti2v_vs_t2v_${duration}s.md"
    python scripts/compare_teachquiz.py \
        --left "$EVAL_BASE/wan5b_ti2v_${duration}s/teachquiz" \
        --right "$EVAL_BASE/wan5b_t2v_${duration}s/teachquiz" \
        --left-label "TI2V-${duration}s" --right-label "T2V-${duration}s" \
        --out "$EVAL_BASE/paired_teachquiz_${duration}s.json"
done

if [[ "$RUN_MODE" == "generation-only" ]]; then
    echo "60-case matched generation complete; evaluation and shared TeachQuiz are pending."
    exit 0
fi
echo "Matched generation, scoring, shared TeachQuiz, and paired standard analysis complete."
echo "Human validity and release review remain separate gates."
