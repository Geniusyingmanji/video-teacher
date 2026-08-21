# Standard-eval paired comparison: Wan5B-3s - Wan1.3B-3s

Positive differences favour the left configuration. Cases are paired by exact case ID.

Shared cases: 60; bootstrap/permutation draws: 10000; seed: 20260821.

| Metric | N | Mean difference | 95% bootstrap CI | Cohen's dz | Permutation p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| aggregate_score | 60 | -0.0683 | [-0.1775, 0.0425] | -0.151 | 0.2532 | 0.9679 |
| conceptual_correctness | 60 | -0.1167 | [-0.2833, 0.0500] | -0.175 | 0.2462 | 0.9679 |
| narrative_structure | 60 | 0.0500 | [-0.0833, 0.1833] | 0.094 | 0.6252 | 0.9679 |
| visual_quality | 60 | -0.1250 | [-0.3208, 0.0750] | -0.156 | 0.2420 | 0.9679 |

Cohen's dz is undefined when every paired difference is identical. Holm p-values control the family-wise error rate across the metrics in this table.
