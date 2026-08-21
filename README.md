# rise-teacher

Benchmark for evaluating text-to-video models on **multi-discipline knowledge-explanation and problem-solving** tasks, with **two complementary metrics**:

1. **Standard eval** — GPT-5.5 scores 6 pedagogy-aware dimensions (Conceptual Correctness, Narrative Structure, Visual Quality, Pedagogical Clarity, Didactic Affordances, Audience Appropriateness).
2. **TeachQuiz-T** — a weak student VLM (Qwen3-VL-2B) takes pre/post quizzes around each generated video; we measure the *normalized learning gain*.

Pilot finding: **standard eval explains <5% of variance in normalized gain for one frozen VLM learner proxy**. This motivates studying TeachQuiz-T as a complementary metric; it is not yet evidence about human learning. See [`docs/STATUS.md`](docs/STATUS.md), [`docs/TEACHQUIZ_REPORT.md`](docs/TEACHQUIZ_REPORT.md), and the [`paper-readiness audit`](docs/PAPER_READINESS.md) for results and claim boundaries.

The in-progress 100-case GRADE + DisciplineGen-1M data expansion is documented
in [`docs/MULTISOURCE_PILOT.md`](docs/MULTISOURCE_PILOT.md). It is
schema-valid but intentionally remains outside the released benchmark until its
curation and redistribution gates pass.

---

## End-to-end pipeline

```
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│       DATA        │ ─▶ │    GENERATION     │ ─▶ │       EVAL        │ ─▶ │     ANALYSIS      │
├───────────────────┤    ├───────────────────┤    ├───────────────────┤    ├───────────────────┤
│ prompts (60-82)   │    │ Wan2.1-T2V-1.3B   │    │ standard 6-dim    │    │ paper_stats       │
│ first_frames      │    │ Wan2.2-TI2V-5B    │    │ (GPT-5.5 judge)   │    │ dim correlation   │
│ teachquiz probes  │    │ (3s or 5s, 24fps) │    │ TeachQuiz-T       │    │ eval↔TeachQuiz r² │
│                   │    │                   │    │ (Qwen3-VL learner)│    │ per-difficulty    │
└───────────────────┘    └───────────────────┘    └───────────────────┘    └───────────────────┘
       data/                  generation/                eval/                docs/{reports,analysis}/
```

### Stage 1 — DATA (`data/`)

| Subdir | Content |
|---|---|
| `data/prompts/` | 60-case pilot_v0_1 + 82-case pilot_v0_2 + 22 high-difficulty addon (12 disciplines × explanation/problem_solving × k12/undergrad/professional/graduate) |
| `data/first_frames/` | 60 PNG first-frame images (832×480) for TI2V conditioning. Currently from Azure GPT-Image-1 (25/60 judged PASS by the strict opening-frame judge). Optional inputs to the TI2V runner. |
| `data/first_frames_mmmu/` | Retrieval metadata for the alternative path that sources first frames from MMMU + AI2D benchmark datasets (candidates + GPT-5.5 selections). |
| `data/teachquiz/` | Pre/post quizzes and auto-generated visual probes (60×3 questions per model) for the TeachQuiz-T learning-gain metric. |

### Stage 2 — GENERATION (`generation/`)

```bash
# Pure text-to-video (Wan2.1-T2V-1.3B)
CUDA_VISIBLE_DEVICES=3 python -m generation.runners.wan_runner \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --out /data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1 \
    --num-frames 121 --height 480 --width 832 --steps 30 --fps 24    # 5s @ 24fps

# Text-Image-to-video (Wan2.2-TI2V-5B) — uses first frames
CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_ti2v_runner \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --first-frames data/first_frames \
    --out /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/pilot_v0_1 \
    --num-frames 121 --height 480 --width 832 --steps 30
```

Outputs `{<id>.mp4, manifest.jsonl}` per case.

### Stage 3 — EVAL (`eval/`)

**Standard eval** — GPT-5.5 vision judge scores 8 evenly-spaced frames per video:

```bash
python -m eval.run_eval \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/eval_pilot_v0_1 \
    --n-frames 8 --frame-max-px 384
# Produces per_case.jsonl + aggregate.json (per_dim_mean, per_discipline,
# per_task_type, per_difficulty)
```

**TeachQuiz-T** — weak student takes pre-video → post-video probe quiz, learning gain = (post − max(pre, random)) / (1 − max(pre, random)):

```bash
python -m eval.run_teachquiz \
    --student qwen3vl \
    --student-model-path /data/zyf/rise-teacher/models/Qwen3-VL-2B-Instruct \
    --probe data/teachquiz/visual_probe_auto_5b.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/teachquiz_5b_qwen3vl_autoprobe
```

### Stage 4 — ANALYSIS (`scripts/` → `docs/`)

```bash
python scripts/gen_paper_stats.py            # → docs/paper_stats.md / paper_stats.json
python scripts/dim_correlation.py            # → docs/analysis/dim_correlation_*.md
python scripts/eval_vs_teachquiz_correlation.py  # → docs/analysis/eval_vs_teachquiz_corr.md
python scripts/gen_teachquiz_report.py       # → docs/TEACHQUIZ_REPORT.md
python scripts/render_report.py              # → docs/reports/PILOT_REPORT*.md
python scripts/compare_standard_eval.py \     # paired CI/effect/permutation analysis
  --left results/eval_pilot_v0_1/per_case.jsonl \
  --right results/eval_pilot_v0_1_wan13b/per_case.jsonl \
  --left-label Wan5B-3s --right-label Wan1.3B-3s \
  --out docs/analysis/paired_wan5b_vs_wan13b_3s.md
```

---

## Headline results (current)

| Configuration | N | mean | CC | NS | VQ |
|---|---|---|---|---|---|
| Wan5B-3s | 60 | 1.754 | 1.45 | 1.50 | 2.896 |
| Wan5B-3s-ext6 (6 dims) | 60 | 1.820 | 1.567 | 1.517 | 2.946 |
| Wan1.3B-3s | 60 | **1.823** | 1.567 | 1.45 | 3.021 |
| Wan5B-5s | 60 | 1.789 | 1.567 | 1.70 | 2.479 |
| Wan1.3B-5s | 60 | 1.788 | 1.517 | 1.40 | 3.050 |
| **Wan1.3B-v0.2-high** (graduate) | 22 | **1.486** | 1.227 | **1.091** | 2.727 |

**TeachQuiz-T (Qwen3-VL-2B student, auto visual probes):**

| Model | N valid | NG | PGR |
|---|---|---|---|
| Wan5B | 52/60 | **0.760** | 88.5% |
| Wan1.3B | 53/60 | 0.730 | 83.0% |

**Standard eval vs TeachQuiz-T correlation:** r²(5B)=4.5%, r²(1.3B)=0.9%.

Paired uncertainty analysis does **not** establish an aggregate winner between
Wan5B-3s and Wan1.3B-3s: left-minus-right mean difference -0.0683, 95% case-
bootstrap CI [-0.1775, 0.0425]. See `docs/analysis/paired_*.md`; raw mean
differences should not be interpreted as significant without these paired
analyses.

---

## Repository layout

```
data/
├── prompts/              # case definitions (pilot_v0_1, pilot_v0_2, high-difficulty addon)
├── first_frames/         # 60 GPT-Image-1 first-frame PNGs + check_report.jsonl
├── first_frames_mmmu/    # MMMU/AI2D retrieval metadata (candidates, selections)
└── teachquiz/            # quizzes + auto-generated visual probes

generation/
└── runners/
    ├── wan_runner.py        # Wan2.1-T2V (pure text)
    └── wan_ti2v_runner.py   # Wan2.2-TI2V-5B (text + first frame)

eval/
├── dimensions/           # CC, NS, VQ + PC, DA, AA + learning_gain
├── judges/gpt55.py       # Azure OpenAI keyless GPT-5.5 client
├── students/             # qwen3vl, qwen25vl, smolvlm2, gpt55_student, dummy
├── run_eval.py           # standard 3/6-dim evaluation
└── run_teachquiz.py      # pre/post quiz with weak student

scripts/                  # 33 scripts: build prompts, generate/check/regen first frames,
                          # download MMMU/AI2D, run analyses, render reports, orchestrate
                          # full pipeline (run_full_pipeline.sh, finalize_*.sh)

docs/
├── STATUS.md             # current state (always up-to-date)
├── plan.md, survey.md    # design + literature review
├── REPORT.md             # narrative for paper
├── TEACHQUIZ.md          # TeachQuiz-T design + TEACHQUIZ_REPORT.md results
├── paper_stats.md        # headline numbers (auto-generated)
├── reports/              # 13 per-config pilot reports
└── analysis/             # 9 dim-correlation files + eval-vs-teachquiz
```

---

## Dimension status

All 6 standard-eval dimensions are pilot-ready; learning gain is the headline contribution:

| Dim | Status | Source |
|---|---|---|
| Conceptual Correctness | ✅ pilot | RISE-Video reasoning alignment |
| Narrative Structure | ✅ pilot | PhyEduVideo logic flow + ordered-beat verification |
| Visual Quality | ✅ pilot | RISE-Video VQ (mean of 4 sub-axes) |
| Pedagogical Clarity | ✅ extended | chunking / emphasis / legibility / signposting |
| Didactic Affordances | ✅ extended | PhyEduVideo element layout |
| Audience Appropriateness | ✅ extended | depth / vocabulary / prior knowledge / engagement |
| **Learning Gain (TeachQuiz-T)** | ✅ pilot | normalized pre→post gain, auto-probes |
| Audio–Narration Alignment | ⏳ pending | needs audio-capable model |
| Triple-Modal Alignment | ⏳ pending | needs audio + vision joint judge |

---

## Environment

First-time setup:

```bash
cd /home/azureuser/workspace-gzy/zyf/rise-teacher
conda env create -f environment.yml          # Python 3.10, torch 2.5.1+cu121, ~5 min
cp .envrc.example .envrc                     # then edit Azure endpoint + paths
```

Every shell:

```bash
source .envrc                # activates the `rise-teacher` conda env and exports HF / Azure / CUDA env vars
```

For exact pin-for-pin reproducibility (after `conda activate rise-teacher`):

```bash
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121
```

**Important paths:**

- Code: `/home/azureuser/workspace-gzy/zyf/rise-teacher/`
- Generations / eval outputs: `/data/zyf/rise-teacher/{generations,outputs}/`
- Models: `/data/zyf/rise-teacher/models/{Wan2.2-TI2V-5B-Diffusers, Wan2.1-T2V-1.3B-Diffusers, Qwen3-VL-2B-Instruct}`
- External datasets (MMMU 389M, AI2D 488M): `/home/azureuser/workspace-gzy/zyf/datasets/`

**GPT-5.5 keyless auth** — `eval/judges/gpt55.py` shells out to `az account get-access-token` and caches the bearer; requires `az login` to be active.

---

## Quick reproduction (60-case pilot, Wan1.3B, 3s)

```bash
# 1. Build prompts (one-time)
python scripts/build_pilot_prompts.py

# 2. Generate 60 videos
CUDA_VISIBLE_DEVICES=3 python -m generation.runners.wan_runner \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --out /data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1 \
    --num-frames 73 --height 480 --width 832 --steps 30 --fps 24    # 3s

# 3. Standard eval (≈30 min via GPT-5.5)
python -m eval.run_eval \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b

# 4. TeachQuiz-T (≈20 min via local Qwen3-VL)
CUDA_VISIBLE_DEVICES=2 python -m eval.run_teachquiz \
    --student qwen3vl \
    --student-model-path /data/zyf/rise-teacher/models/Qwen3-VL-2B-Instruct \
    --probe data/teachquiz/visual_probe_auto_1_3b.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_1_t2v_1_3b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/teachquiz_13b_qwen3vl_autoprobe

# 5. Analysis & reports
python scripts/gen_paper_stats.py
python scripts/dim_correlation.py \
    --per-case /data/zyf/rise-teacher/outputs/eval_pilot_v0_1_wan13b/per_case.jsonl \
    --label "Wan1.3B-3s" --out docs/analysis/dim_correlation_13b_3s.md
python scripts/eval_vs_teachquiz_correlation.py
python scripts/gen_teachquiz_report.py
```

Or run the full chained pipeline:

```bash
bash scripts/run_full_pipeline.sh
```

---

## See also

- [`docs/STATUS.md`](docs/STATUS.md) — always-current project state
- [`docs/plan.md`](docs/plan.md) — original design doc
- [`docs/survey.md`](docs/survey.md) — literature review
- [`docs/REPORT.md`](docs/REPORT.md) — paper narrative
- [`docs/TEACHQUIZ.md`](docs/TEACHQUIZ.md) — TeachQuiz-T design
- [`docs/TEACHQUIZ_REPORT.md`](docs/TEACHQUIZ_REPORT.md) — learning-gain results
- [`docs/paper_stats.md`](docs/paper_stats.md) — headline numbers (auto-generated)
- [`docs/HUMAN_EVAL_PROTOCOL.md`](docs/HUMAN_EVAL_PROTOCOL.md) — blinded human-validation protocol
- [`docs/PAPER_READINESS.md`](docs/PAPER_READINESS.md) — evidence gaps and allowed claim language
