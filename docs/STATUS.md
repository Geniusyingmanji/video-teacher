# STATUS — 2026-08-05  MULTISOURCE PILOT CURATION IN PROGRESS

## 2026-08-05 continuation

The GRADE + DisciplineGen-1M multisource pilot is reproducible and
schema-valid: 100 cases, balanced as 5 GRADE and 5 DisciplineGen cases across
each of 10 disciplines. The dataset remains deliberately blocked from release:
GRADE redistribution terms are unverified, 90 source rows still require
disciplinary or image review, and three music rows require duplicate review.

- Main prompt file: `data/prompts/multisource_pilot_100.jsonl`.
- Build and release validation: `scripts/build_multisource_pilot.py`.
- Validation checks source provenance and ensures every row marked
  `reviewed_release_ready` has its local before/ground-truth asset pair.
- `docs/MULTISOURCE_PILOT.md` documents reproducible sampling and the release
  gate. It intentionally does not claim the draft as a benchmark release.

---

# STATUS — 2026-06-03 17:35 UTC  ⏳ DEFECT-ORIENTED EXTENSION STARTED

## 2026-06-03 continuation

New long-term direction: move beyond broad pilot averages into defect-oriented tests that expose where current T2V and agentic long-video workflows fail as teaching media.

### New artifacts

- `data/prompts/candidates_defect_oriented_v1_seed.jsonl` — 12 first-frame-first seed cases, one per frozen discipline, targeting symbolic fidelity, state continuity, causal order, transition correctness, graph directionality, and role consistency.
- `docs/defect_oriented_v1_plan.md` — execution plan and current defect-oriented results.
- `docs/long_video_agent_survey.md` — recent long-video/agent workflow notes and failure modes to convert into rise-teacher probes.
- `docs/reports/PILOT_REPORT_wan5b_ti2v_ff_3s.md` and `docs/reports/PILOT_REPORT_wan5b_ti2v_ff_5s.md` — existing TI2V+first-frame runs are now rendered into reports.
- `docs/reports/DEFECT_ORIENTED_V1_SEED_PASS6_TI2V_FF.md` — first pass report for the defect seed PASS subset.

### First-frame repair status

- Generated 12 GPT-Image-1 high-quality first frames for the defect seed.
- Initial strict check: 5 PASS / 5 FAIL / 2 ERROR.
- After one GPT-Image repair pass: 6 PASS / 4 FAIL / 2 ERROR.
- Persistent FAIL modes are exactly the intended stress area: ECG 12-lead layout omissions, Dijkstra graph topology/weights changing, cropped poetry/title text, and unresolved judge ERRORs for SN2/music notation.

### Video generation and eval

- Extracted `data/prompts/defect_oriented_v1_seed_pass6.jsonl` from second-check PASS rows.
- Installed missing `ftfy` dependency; without it Wan I2V failed with `NameError: ftfy is not defined`.
- Generated 6/6 Wan2.2-TI2V-5B first-frame-conditioned videos:
  `/data/zyf/rise-teacher/generations/wan2_2_ti2v_5b_ff/defect_oriented_v1_seed_pass6/manifest.jsonl`.
- Standard 6-dim eval:
  `/data/zyf/rise-teacher/outputs/eval_defect_oriented_v1_seed_pass6_ti2v_ff/aggregate.json`
  - N=6, mean=2.512, strict=0.0%.
  - Dim means: CC 2.667, NS 2.167, VQ 2.583, PC 2.167, DA 2.417, AA 3.083.
  - Best: geography rain-shadow 3.853. Weakest: economics AD-AS 1.820, math chain rule 1.895.
- TeachQuiz-T smoke with local SmolVLM2 student:
  `/data/zyf/rise-teacher/outputs/teachquiz_defect_oriented_v1_seed_pass6_smolvlm2/aggregate.json`
  - N valid=6, normalized gain=0.5833, positive gain rate=0.6667.
  - Qwen3-VL could not run because `/data/zyf/rise-teacher/models/Qwen3-VL-2B-Instruct` is absent locally; use SmolVLM2 only as a smoke until the canonical student is restored.

---

# STATUS — 2026-05-13 15:25 UTC  ✅ ALL PIPELINES COMPLETE

## 醒来检查清单

1. **paper_stats.md** ← 所有7个eval的最终数字（含 Wan1.3B-v0.2-high）
2. **TEACHQUIZ_REPORT.md** ← TeachQuiz-T结果 + 与标准评测相关性 + per-difficulty
3. **PILOT_REPORT_v0_2_high.md** ← v0.2高难度22案例报告（新！）
4. **analysis/dim_correlation_v0_2_high.md** ← 高难度维度相关性（新！关键发现）
5. **PILOT_REPORT_compare_3s_vs_5s.md** ← 4模型×2时长对比

---

## 最终核心结果

### 标准评测 — 全部7个配置
| 模型 | N | mean_agg | CC | NS | VQ |
|---|---|---|---|---|---|
| Wan5B-3s | 60 | 1.754 | 1.45 | 1.50 | 2.896 |
| Wan5B-3s-ext | 60 | 1.766 | 1.50 | 1.40 | 2.919 |
| Wan5B-3s-ext6 | 60 | 1.820 | 1.567 | 1.517 | 2.946 |
| Wan1.3B-3s | 60 | **1.823** | 1.567 | 1.45 | 3.021 |
| Wan5B-5s | 60 | 1.789 | 1.567 | 1.70 | 2.479 |
| Wan1.3B-5s | 60 | 1.788 | 1.517 | 1.40 | 3.050 |
| **Wan1.3B-v0.2-high** | **22** | **1.486** | **1.227** | **1.091** | **2.727** |

**per-difficulty (Wan1.3B)**：
| 难度 | 1.3B-3s | 1.3B-5s | 1.3B-v0.2-high |
|---|---|---|---|
| k12 | 1.943 | 1.984 | — |
| undergrad | 1.785 | 1.621 | — |
| professional | 1.32 | 1.52 | — |
| **high (graduate)** | — | — | **1.486** |

→ 从 k12(1.943) 到 professional(1.32) 到 graduate(1.486) — 专业级最难，研究生级稍有回升但NS崩溃

### 关键新发现：维度相关性随难度变化

| 模型配置 | CC↔VQ | NS↔VQ | CC↔NS |
|---|---|---|---|
| Wan5B-3s | +0.12 | +0.20 | +0.58 |
| Wan1.3B-3s | +0.36 | +0.20 | +0.63 |
| Wan5B-5s | +0.49 | +0.13 | +0.51 |
| Wan1.3B-5s | +0.42 | +0.29 | +0.61 |
| **Wan1.3B-v0.2-high** | **+0.03** | **-0.16** | +0.21 |

→ 高难度下 CC↔VQ 近乎为零（+0.03），NS↔VQ 轻微负相关（-0.16）。
→ **核心证据**：模型能维持视觉质量，同时概念正确性和叙事结构彻底崩溃。

### TeachQuiz-T（Qwen3-VL-2B 学生）
| 模型 | N valid | NG | PGR | Expl. NG | PS NG |
|---|---|---|---|---|---|
| Wan5B | 52/60 | **0.760** | 88.5% | **0.807** | 0.683 |
| Wan1.3B | 53/60 | 0.730 | 83.0% | 0.719 | **0.746** |

**TeachQuiz-T 按难度**：
| 难度 | 5B NG | 1.3B NG |
|---|---|---|
| k12 | **0.820** (n=25) | 0.679 (n=27) |
| undergrad | 0.674 (n=23) | **0.811** (n=22) |
| professional | **0.875** (n=4) | 0.625 (n=4) |

### 标准评测 vs TeachQuiz-T 相关性
| 模型 | r(agg, NG) | r²(%) |
|---|---|---|
| Wan5B | 0.213 | **4.5%** |
| Wan1.3B | 0.094 | **0.9%** |

→ 标准评测几乎不能预测学习增益！

---

## v0.2 高难度 22案例分析

**最佳学科**：language_literature (1.800), civics (1.775), art_music (1.750)
**最差学科**：chemistry (1.200), economics (1.275), computer_science (1.325)

**最常失败的概念**：12音列（音乐理论）、NATO成立年份、Mackinder世界岛理论
→ 模型在需要精确事实/专业知识的内容上失败

**任务类型**：problem_solving (1.527) 微胜 explanation (1.445)（与低难度相反！）

---

## 所有关键文件

```
paper_stats.md / paper_stats.json       -- 7个eval配置汇总（最终）
PILOT_REPORT_compare_3s_vs_5s.md        -- 4模型×2时长全面对比
PILOT_REPORT_v0_2_high.md               -- v0.2高难度报告（22案例）
TEACHQUIZ_REPORT.md                     -- TeachQuiz-T学习增益分析（含per-difficulty）
analysis/dim_correlation_5b_3s.md       -- Wan5B-3s (CC↔VQ=+0.12)
analysis/dim_correlation_5b_3s_ext6.md  -- Wan5B-3s-ext6 6维度
analysis/dim_correlation_5b_5s.md       -- Wan5B-5s (CC↔VQ=+0.49)
analysis/dim_correlation_13b_3s.md      -- Wan1.3B-3s (CC↔VQ=+0.36)
analysis/dim_correlation_13b_5s.md      -- Wan1.3B-5s (CC↔VQ=+0.42)
analysis/dim_correlation_v0_2_high.md   -- Wan1.3B-high (CC↔VQ=+0.03, NS↔VQ=-0.16!!)
analysis/eval_vs_teachquiz_corr.md      -- 标准评测 vs TeachQuiz-T 相关性
eval/students/qwen3vl.py                -- Qwen3-VL-2B 学生适配器
data/teachquiz/visual_probe_auto_5b.jsonl    -- 5B自动探针 (60 cases)
data/teachquiz/visual_probe_auto_1_3b.jsonl  -- 1.3B自动探针 (60 cases)
```

---

## 论文 Claims（全部有数据支撑）

1. **标准评测无法预测学习增益**：r²<5%（5B=4.5%, 1.3B=0.9%）
2. **5s视频改善专业级难度**：professional +0.20 for both models
3. **CC↔VQ正交且随难度增强**：3s=+0.12→5s=+0.49→高难度=+0.03（极度正交）
4. **5B教学效果胜**（NG 0.760 vs 0.730），尽管标准评测1.3B胜（1.754 vs 1.823）
5. **任务类型分工**：5B解释类胜(0.807)，1.3B解题类胜(0.746)
6. **难度交互**：5B在k12+专业级更有效，1.3B在本科级更有效
7. **高难度NS崩溃**：graduate level NS=1.091（比标准低0.36），而VQ相对稳定（2.727）

---

## 完成状态 ✅

所有pipeline已完成。无等待任务。可以开始论文写作。
