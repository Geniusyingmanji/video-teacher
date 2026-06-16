# Defect-Oriented v1 Plan

_Updated: 2026-06-03._

## Goal

Extend rise-teacher from broad pilot coverage into targeted stress tests that expose where current T2V and agentic long-video workflows fail as teaching media: symbolic fidelity, state continuity, causal order, transition correctness, and learning gain.

## Starting Point

- Existing first-frame iteration improved the 60-case pilot from 25/60 PASS to 49/60 PASS under the strict opening-frame judge.
- Existing `sleep2_20260601_180854` long run produced 847 accepted first-frame-first candidates; it is useful as a pool, but it is skewed toward medicine and computer science.
- Existing TI2V first-frame runs are already available for the 60-case pilot: `eval_wan2_2_ti2v_5b_ff` mean 2.017 and `eval_wan2_2_ti2v_5b_ff_5s` mean 2.013.
- The main TI2V failure pattern is not generic visual quality: low-dimension counts are concentrated in conceptual correctness, narrative structure, pedagogical clarity, and didactic affordances while visual quality is usually higher.

## Seed Set

The initial seed is `data/prompts/candidates_defect_oriented_v1_seed.jsonl`, one case per frozen discipline. Each row includes a concrete `first_frame` spec and defect-target metadata:

- symbolic text and notation fidelity
- multi-step reasoning state consistency
- causal sequence and role consistency
- graph/diagram direction fidelity
- temporal ordering and transition correctness
- safety or caveat retention for medical/civic tasks

## Next Runs

1. Validate and review the seed set. Done: 12/12 schema-valid with `--require-first-frame`.
2. Generate first frames for the seed set with GPT-Image-1 high quality. Done: 12/12 generated.
3. Run strict first-frame checks; repair any FAIL/ERROR rows before video generation. Done first pass plus one repair pass: 6 PASS / 4 FAIL / 2 ERROR.
4. Generate 3s Wan TI2V videos for rows that passed strict first-frame review. Done: 6/6 generated after installing missing `ftfy`.
5. Run standard 6-dim eval and TeachQuiz-T probes. Done for pass6: standard mean 2.512, SmolVLM2 TeachQuiz normalized gain 0.5833.
6. Next: repair or redesign the remaining 6 first frames, then rerun the same pipeline. For long-video agents, expand selected cases to 30-60s storyboard prompts and score transitions separately.

## Current Results

### First Frames

| Stage | PASS | FAIL | ERROR | Notes |
|---|---:|---:|---:|---|
| Initial GPT-Image-1 high quality | 5 | 5 | 2 | Failures: wrong formula text, incomplete ECG grid, wrong Dijkstra graph, cropped poetry line, over-solved history timeline. |
| One repair pass | 6 | 4 | 2 | Math repaired. Persistent failures: ECG, Dijkstra, poetry scansion, Cuban Missile timeline; SN2 and circle-of-fifths still judge ERROR. |

### Video And Standard Eval

Pass-only prompt file: `data/prompts/defect_oriented_v1_seed_pass6.jsonl`.

Video manifest: `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/defect_oriented_v1_seed_pass6/manifest.jsonl`.

Standard eval output: `/data/zyf/rise-teacher/outputs/eval_defect_oriented_v1_seed_pass6_ti2v_ff/aggregate.json`.

| Metric | Value |
|---|---:|
| N | 6 |
| Mean aggregate | 2.512 |
| Strict accuracy | 0.0% |
| Conceptual correctness | 2.667 |
| Narrative structure | 2.167 |
| Visual quality | 2.583 |
| Pedagogical clarity | 2.167 |
| Didactic affordances | 2.417 |
| Audience appropriateness | 3.083 |

Best case: geography rain-shadow, aggregate 3.853. Weak cases: economics AD-AS 1.820 and math chain rule 1.895. The pattern remains useful: videos can be visually acceptable while still weak on narrative steps, graph direction, or symbolic reasoning.

### TeachQuiz-T Smoke

Probe file: `data/teachquiz/visual_probe_defect_oriented_v1_seed_pass6_ti2v_ff.jsonl`.

Output: `/data/zyf/rise-teacher/outputs/teachquiz_defect_oriented_v1_seed_pass6_smolvlm2/aggregate.json`.

The canonical Qwen3-VL-2B student is not present at `/data/zyf/rise-teacher/models/Qwen3-VL-2B-Instruct`, so this run used the local `models_students/SmolVLM2-2.2B-Instruct` as a smoke student. Results: N valid 6, normalized gain 0.5833, positive gain rate 0.6667.

## Reporting

Report by defect target first, then by discipline. A useful result is not only that a model scores low; it should say what kind of teaching failure occurred, for example "kept the circuit visually stable but inverted the RC voltage/current relationship" or "preserved the graph style while the Dijkstra table silently changed."
