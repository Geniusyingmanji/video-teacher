# Standard-eval paired comparison: Wan1.3B-5s - Wan1.3B-3s

Positive differences favour the left configuration. Cases are paired by exact case ID.

Shared cases: 60; bootstrap/permutation draws: 10000; seed: 20260821.

| Metric | N | Mean difference | 95% bootstrap CI | Cohen's dz | Permutation p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| aggregate_score | 60 | -0.0342 | [-0.1317, 0.0583] | -0.091 | 0.5017 | 1.0000 |
| conceptual_correctness | 60 | -0.0500 | [-0.1833, 0.0833] | -0.088 | 0.6446 | 1.0000 |
| narrative_structure | 60 | -0.0500 | [-0.2000, 0.1000] | -0.084 | 0.6694 | 1.0000 |
| visual_quality | 60 | 0.0292 | [-0.1250, 0.1792] | 0.047 | 0.7506 | 1.0000 |

Cohen's dz is undefined when every paired difference is identical. Holm p-values control the family-wise error rate across the metrics in this table.
