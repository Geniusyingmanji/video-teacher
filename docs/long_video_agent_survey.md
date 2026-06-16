# Long-Video Agent Survey Notes

_Updated: 2026-06-03. Scope: recent long-form video generation and agent/planner workflows, with emphasis on failure modes that rise-teacher can turn into educational-video tests._

## Verified Recent Threads

| Work | What it adds | Reported quality signal | Failure modes relevant to rise-teacher |
|---|---|---|---|
| DirectorBench (arXiv:2605.30090) | Diagnostic benchmark for long-form workflows with personalized multi-agent evaluation across script, visual, audio, cross-modal, and stability checkpoints. | Reports that transition quality is the key bottleneck: average 0.256, best workflow 0.356, while prompt-level user fulfillment averages 0.71. | Between-shot transitions, user-intent drift, aggregate scores hiding local defects. |
| CoAgent (arXiv:2512.22536) | Plan-synthesize-verify framework: storyboard planner, global context manager, visual consistency controller, verifier, and pacing-aware editor. | Claims improved coherence, visual consistency, and narrative quality in long-form generation. | Identity/diagram drift across shots, verifier misses, regenerate loops that improve appearance but not correctness. |
| LoCoT2V-Bench (arXiv:2510.26412, ICML 2026) | Benchmark for long-form, multi-scene prompts with metadata for characters, scenes, camera behavior, and HERD evaluation. | Finds models maintain perceptual/background quality better than fine-grained alignment and character consistency. | Fine-grained prompt following, persistent entity labels, long-range state consistency. |
| MemoryPack + Direct Forcing (arXiv:2510.01784) | Retrieval-like memory and inference alignment for minute-level autoregressive consistency. | Targets long-range dependencies and error accumulation. | Memory can preserve visual style while still losing instructional state, such as table values or proof assumptions. |
| LoL / multi-head RoPE jitter (arXiv:2601.16914) | Training-free mitigation for sink-collapse in streaming/infinite-length generation. | Demonstrates very long continuous streams and identifies sink-collapse: resets or cyclic motion around sink frames. | Scene reset, cyclic animation, re-introducing already-explained setup, losing the current reasoning step. |
| Hybrid Forcing (arXiv:2604.10103) | Hybrid attention and decoupled distillation for long-horizon streaming video generation. | Reports real-time unbounded 832x480 generation at 29.5 FPS on a single H100. | Efficient streaming may preserve motion but still needs tests for conceptual continuity and text/symbol persistence. |
| SCOPE (arXiv:2604.02979) | Training-free acceleration for autoregressive video diffusion through cache, predict, and recompute scheduling. | Reports up to 4.73x speedup on MAGI-1 and SkyReels-V2 with comparable quality. | Acceleration can hide small semantic regressions: stale labels, wrong graph values, or skipped intermediate reasoning. |

## Defects To Target

1. **Transition correctness**: a later shot must inherit the right state from the previous shot, not simply look plausible. Educational probes: Dijkstra table updates, timeline ordering, chain-rule intermediate variables.
2. **Persistent symbolic text**: equations, labels, table values, ECG lead names, and music notation must remain stable across frames. This is a sharper test than generic text rendering.
3. **Causal order**: mechanisms must happen in the correct sequence. Educational probes: SN2 backside attack before leaving-group departure, CRISPR targeting before cutting before repair, RC charging before asymptotic graph.
4. **Graph/diagram directionality**: curves, arrows, and shifts need the correct direction. Educational probes: AD-AS supply shock, rain-shadow windward/leeward, RC voltage curve.
5. **Long-range role consistency**: entities cannot swap roles mid-video. Educational probes: guide RNA vs Cas9, court vs Congress vs states, nucleophile vs leaving group.
6. **Audio or narration alignment**: long-video systems increasingly include audio; instructional narration must match the visual step, not just sound fluent.
7. **Verifier blind spots**: agent workflows often verify visual coherence more than domain correctness. The benchmark should separate visual pass from conceptual and learning-gain pass.

## Immediate Benchmark Implication

Use `data/prompts/candidates_defect_oriented_v1_seed.jsonl` as a small seed set for 5s and longer 30-60s runs. The cases are designed so a video can look visually acceptable while failing the actual teaching task. Report failures by defect target, not only by discipline or aggregate score.
