# rise-teacher

Benchmark for evaluating video-generation models on **multi-discipline
knowledge-explanation + problem-solving** tasks. Derived from the RISE-Video
pipeline; broadened beyond STEM; with pedagogy-aware evaluation dimensions.

See [`plan.md`](plan.md) and [`survey.md`](survey.md) for the full design + literature review.
See [`TEACHQUIZ.md`](TEACHQUIZ.md) for the experimental TeachQuiz-T / Learning
Gain MVP.

## Environment

```bash
cd /home/azureuser/workspace-gzy/zyf/rise-teacher
source .envrc            # exports HF_HOME, AZURE_OPENAI_*, etc.
source .venv/bin/activate
```

Important paths:
- Code: `/home/azureuser/workspace-gzy/zyf/rise-teacher/`
- Data / models / generations / outputs: under `/data/zyf/rise-teacher/` (symlinked)
- Wan2.2-TI2V-5B model: `/data/zyf/rise-teacher/models/Wan2.2-TI2V-5B-Diffusers/` (~32 GB)

## End-to-end pipeline (v0.1, 60-case pilot)

```
data/prompts/pilot_v0_1.jsonl                                    # 60 cases × 12 disciplines
        │
        ▼ generation/runners/wan_runner.py  (Wan2.2-TI2V-5B)
generations/wan2_2_ti2v_5b/pilot_v0_1/{<id>.mp4, manifest.jsonl}
        │
        ▼ eval/frame_extractor.py  (8 evenly-spaced frames @ 384px max)
        ▼ eval/dimensions/{conceptual_correctness,narrative_structure,visual_quality}.py
        ▼ eval/judges/gpt55.py  (Azure OpenAI key-less, GPT-5.5 vision)
        ▼ eval/run_eval.py
outputs/eval_pilot_v0_1/{per_case.jsonl, aggregate.json}
```

Reproducing:

```bash
# 1. Build prompts (one-time)
python scripts/build_pilot_prompts.py

# 2. Generate
CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_runner \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --out /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1 \
    --num-frames 49 --height 480 --width 832 --steps 30

# 3. Evaluate
python -m eval.run_eval \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/eval_pilot_v0_1
```

## Current dimensions implemented (6 of 9)

| Dim | Status | Source |
|---|---|---|
| Conceptual Correctness | ✅ pilot | RISE-Video Reasoning Alignment prompt structure |
| Narrative Structure | ✅ pilot | PhyEduVideo Logic Flow + ordered-beat verification |
| Visual Quality | ✅ pilot | RISE-Video VQ; mean of 4 sub-axes |
| Pedagogical Clarity | ✅ extended | NEW; 4 sub-axes: chunking, emphasis, legibility, signposting |
| Didactic Affordances | ✅ extended | PhyEduVideo Element Layout; labels/arrows/equations/color |
| Audience Appropriateness | ✅ extended | NEW; 4 sub-axes: depth, vocabulary, prior knowledge, engagement |
| Audio–Narration Alignment | ⏳ todo (needs audio-capable model) | Adapts VABench |
| Triple-Modal Alignment | ⏳ todo | NEW |
| Learning Gain (TeachQuiz-T) | ⏳ todo (headline) | Port of Code2Video TeachQuiz |

## GPT-5.5 (keyless Azure CLI auth)

`eval/judges/gpt55.py` shells out to `az account get-access-token` and caches
the bearer token. No API key needed. Requires `az login` to be active.

```python
from eval.judges.gpt55 import chat
chat([{"role": "user", "content": "ping"}])
```

## Data layout

```
data/prompts/pilot_v0_1.jsonl   # 60 cases
  schema: id / discipline / subdomain / task_type / difficulty
          prompt_text / expected_concepts / expected_visual_elements
          expected_narrative_order / pedagogical_target_audience
          discipline_specific_rubric / audio_narration_required
```
