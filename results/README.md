# results/

Tracked canonical eval / TeachQuiz-T outputs. Each subdirectory contains:

- `aggregate.json` — per-dim mean, per-discipline, per-task-type, per-difficulty rollups
- `per_case.jsonl` — one row per case with raw scores

These are the **evidence chain** behind every number in `docs/paper_stats.md`,
`docs/STATUS.md`, `docs/reports/*`, and `docs/analysis/*`. The raw videos and
frame samples that produced them live at `/data/zyf/rise-teacher/{generations,outputs}/`
and are not git-tracked (too large + easily regenerated from the manifests).

| Dir | Model · duration · dims | Used by |
|---|---|---|
| `eval_pilot_v0_1/` | Wan5B · 3s · 3-dim | baseline |
| `eval_pilot_v0_1_extended6/` | Wan5B · 3s · 6-dim (CC/NS/VQ + PC/DA/AA) | extended-dim analysis |
| `eval_pilot_v0_1_5s/` | Wan5B · 5s · 3-dim | 3s vs 5s compare |
| `eval_pilot_v0_1_wan13b/` | Wan1.3B · 3s · 3-dim | model compare |
| `eval_pilot_v0_1_wan13b_5s/` | Wan1.3B · 5s · 3-dim | 3s vs 5s compare |
| `eval_pilot_v0_2_high/` | Wan1.3B · 3s · 3-dim · 22 graduate cases | high-difficulty analysis |
| `teachquiz_5b_qwen3vl_autoprobe/` | Wan5B · TeachQuiz-T (Qwen3-VL-2B student, auto visual probes) | learning gain |
| `teachquiz_13b_qwen3vl_autoprobe/` | Wan1.3B · TeachQuiz-T (Qwen3-VL-2B student, auto visual probes) | learning gain |

Non-canonical runs (smoke tests, abandoned student models, intermediate dim
versions) stay only at `/data/zyf/rise-teacher/outputs/` and are not tracked.

Regenerate everything from these files:

```bash
python scripts/gen_paper_stats.py            # → docs/paper_stats.{md,json}
python scripts/gen_teachquiz_report.py       # → docs/TEACHQUIZ_REPORT.md
python scripts/eval_vs_teachquiz_correlation.py
```
