# rise-teacher — Project Plan

> Last updated: 2026-05-16.
> Companion docs: [`STATUS.md`](STATUS.md) (live state), [`survey.md`](survey.md) (related work), [`REPORT.md`](REPORT.md) (paper narrative), [`TEACHQUIZ.md`](TEACHQUIZ.md) (learning-gain design).

---

## 1. Positioning

**rise-teacher** is a benchmark for evaluating text-to-video models on **multi-discipline knowledge-explanation and problem-solving** tasks. Three novelty levers:

- **A. Discipline breadth** — first pixel-T2V edu benchmark to cover STEM + humanities + social sciences + medicine + CS (12 disciplines).
- **B. Joint task design** — each discipline contributes both *explanation* and *problem-solving* prompts under one unified protocol.
- **C. Two-metric pedagogy evaluation** — 6 GPT-5.5 dimensions + **TeachQuiz-T learning gain** (the headline contribution).

**One-line pitch.** *"PhyEduVideo + VideoScience-Bench, broadened from physics/chemistry to a 12-discipline pedagogy stress test, with both explanation and problem-solving tracks, and a complementary learning-gain metric that exposes a <5% r² gap between standard eval scores and actual student improvement."*

**Must-cite competitors.** RISE-Video, PhyEduVideo (5-axis pedagogy overlap), VideoScience-Bench, CODE2VIDEO (TeachQuiz idea ported to pixel-T2V), VABench (audio protocols, pending).

**Target venue.** ICLR 2027 (deadline Oct 2026). Backup: NeurIPS 2027 D&B (May 2027).

---

## 2. Current state at a glance

```
✅ Discipline breadth (12)        ✅ 60-case pilot complete
✅ Joint explanation + problem    ✅ 7 eval configurations
✅ 6 GPT-5.5 dimensions           ✅ TeachQuiz-T pipeline runs
✅ Wan5B + Wan1.3B × 3s/5s        ✅ v0.2 high-difficulty (22 cases)
✅ Per-difficulty breakdowns      ✅ First-frame iteration (GPT-Image-1)
✅ Dimension correlations          ⏳ TI2V generation runs
⏳ Audio-narration alignment       ⏳ Paper draft
⏳ Triple-modal alignment          ⏳ Human-rater validation
```

See [`STATUS.md`](STATUS.md) for the always-live snapshot. See [`paper_stats.md`](paper_stats.md) for headline numbers.

---

## 3. Scope

### 3.1 Disciplines (12, frozen)

| # | Discipline | Subdomains (examples) |
|---|---|---|
| 1 | mathematics | algebra, geometry, calculus, probability |
| 2 | physics | mechanics, electromagnetism, optics |
| 3 | chemistry | atomic structure, reactions, organic |
| 4 | biology | cell biology, genetics, ecosystems |
| 5 | medicine | anatomy, physiology, pathology |
| 6 | computer_science | algorithms, data structures, systems |
| 7 | economics | micro, macro, finance |
| 8 | civics | government, constitutional theory, law |
| 9 | language_literature | grammar, literary analysis |
| 10 | history | major eras, geopolitics |
| 11 | geography | physical geography, cartography |
| 12 | art_music | color theory, music notation |

### 3.2 Task types (5 cases × 2 types per discipline)

- **explanation** — concept introduction (e.g., "what are interior angles of a triangle").
- **problem_solving** — worked solution (e.g., "solve 2x + 5 = 17").

Per case: `id, discipline, subdomain, task_type, difficulty (k12/undergrad/professional/graduate), prompt_text, expected_concepts, expected_visual_elements, expected_narrative_order, pedagogical_target_audience, discipline_specific_rubric, audio_narration_required`.

### 3.3 Scale

| Phase | Cases | Status |
|---|---|---|
| **pilot_v0_1** | 60 (12 disc × 5) | ✅ complete |
| **pilot_v0_2** | 82 (60 + 22 high-difficulty graduate) | ✅ complete |
| **v1.0** | ~300 (target for paper) | ⏳ planned, gated on human-rater feedback |

---

## 4. Pipeline (current implementation)

```
DATA ─► GENERATION ─► EVAL ─► ANALYSIS
```

### 4.1 DATA

| Artifact | Path | Status |
|---|---|---|
| Prompts | `data/prompts/pilot_v0_{1,2}.jsonl` | ✅ |
| First frames (GPT-Image-1) | `data/first_frames/*.png` (60) | ✅ (25 PASS / 27 FAIL / 8 ERROR) |
| MMMU/AI2D candidate metadata | `data/first_frames_mmmu/{candidates,selections}.jsonl` | ✅ (explored, kept for negative finding) |
| TeachQuiz auto visual probes | `data/teachquiz/visual_probe_auto_{5b,1_3b}.jsonl` | ✅ (60 cases × 3 questions each) |

### 4.2 GENERATION

| Runner | Model | Status |
|---|---|---|
| `generation/runners/wan_runner.py` | Wan2.2-TI2V-5B (T2V mode) | ✅ 60 cases, 3s + 5s |
| `generation/runners/wan_runner.py` | Wan2.1-T2V-1.3B | ✅ 60 cases, 3s + 5s, + 22 v0.2-high |
| `generation/runners/wan_ti2v_runner.py` | Wan2.2-TI2V-5B w/ first frame | ⏳ infrastructure ready, not yet run |

### 4.3 EVAL

| Track | Script | Status |
|---|---|---|
| Standard 3-dim (CC/NS/VQ) | `eval/run_eval.py --core` | ✅ |
| Standard 6-dim (+ PC/DA/AA) | `eval/run_eval.py --extended` | ✅ on Wan5B-3s |
| TeachQuiz-T (Qwen3-VL student, auto probes) | `eval/run_teachquiz.py` | ✅ |
| Audio-narration alignment | — | ⏳ pending (needs audio-capable model) |

### 4.4 ANALYSIS

| Script | Output | Status |
|---|---|---|
| `scripts/gen_paper_stats.py` | `docs/paper_stats.{md,json}` | ✅ |
| `scripts/dim_correlation.py` | `docs/analysis/dim_correlation_*.md` | ✅ (9 configs) |
| `scripts/eval_vs_teachquiz_correlation.py` | `docs/analysis/eval_vs_teachquiz_corr.md` | ✅ |
| `scripts/gen_teachquiz_report.py` | `docs/TEACHQUIZ_REPORT.md` | ✅ |
| `scripts/render_report.py` | `docs/reports/PILOT_REPORT_*.md` | ✅ |

---

## 5. Evaluation framework (9 dimensions)

| # | Dim | Status | Notes |
|---|---|---|---|
| 1 | Conceptual Correctness (CC) | ✅ pilot | Mean ≈ 1.45–1.57 across configs; **collapses to 1.23 at graduate level** |
| 2 | Narrative Structure (NS) | ✅ pilot | Mean ≈ 1.40–1.70; **collapses to 1.09 at graduate level** |
| 3 | Visual Quality (VQ) | ✅ pilot | Mean ≈ 2.48–3.05; **most resilient across difficulty** |
| 4 | Pedagogical Clarity (PC) | ✅ extended | Lowest of the 6 in extended-6 eval (1.44) |
| 5 | Didactic Affordances (DA) | ✅ extended | 1.58 |
| 6 | Audience Appropriateness (AA) | ✅ extended | 2.17 — second-highest after VQ |
| 7 | **Learning Gain (TeachQuiz-T)** | ✅ pilot | **Headline contribution**. NG = 0.760 (5B) vs 0.730 (1.3B) |
| 8 | Audio–Narration Alignment | ⏳ pending | needs audio-capable model |
| 9 | Triple-Modal Alignment | ⏳ pending | needs audio + vision joint judge |

### 5.1 Judge

- GPT-5.5 via Azure key-less (Azure CLI bearer); `eval/judges/gpt55.py`.
- 8 evenly-spaced frames per video, 384 px max side, JSON-structured output.
- Student model for TeachQuiz: **Qwen3-VL-2B-Instruct** (chosen for ceiling-effect resistance; GPT-5.5 students saturate the quiz pre-watch).

---

## 6. Headline results (current)

### 6.1 Standard eval

| Config | N | mean | CC | NS | VQ |
|---|---|---|---|---|---|
| Wan5B-3s | 60 | 1.754 | 1.45 | 1.50 | 2.896 |
| Wan5B-3s-ext6 | 60 | 1.820 | 1.567 | 1.517 | 2.946 |
| **Wan1.3B-3s** | 60 | **1.823** | 1.567 | 1.45 | 3.021 |
| Wan5B-5s | 60 | 1.789 | 1.567 | 1.70 | 2.479 |
| Wan1.3B-5s | 60 | 1.788 | 1.517 | 1.40 | 3.050 |
| **Wan1.3B-v0.2-high** | 22 | **1.486** | 1.227 | **1.091** | 2.727 |

### 6.2 TeachQuiz-T

| Model | N valid | Normalized gain | PGR |
|---|---|---|---|
| **Wan5B** | 52/60 | **0.760** | 88.5% |
| Wan1.3B | 53/60 | 0.730 | 83.0% |

### 6.3 Key claims (all data-backed)

1. **Standard eval doesn't predict learning gain** — r²(5B)=4.5%, r²(1.3B)=0.9%.
2. **5s helps at professional difficulty** — +0.20 for both models.
3. **CC↔VQ orthogonality strengthens with difficulty** — 3s=+0.12, 5s=+0.49, graduate=+0.03 (NS↔VQ becomes negative at graduate level).
4. **5B teaches better than 1.3B** despite losing on standard eval (1.823 vs 1.754).
5. **Task-type specialization** — 5B better at explanations (NG=0.807), 1.3B better at problem-solving (NG=0.746).
6. **Difficulty interaction** — 5B leads at k12 + professional, 1.3B leads at undergrad.
7. **Graduate-level NS collapse** — 1.09 vs VQ holding at 2.73; concept failure not visual failure.

---

## 7. TODO (prioritized)

### 7.1 Must-have for paper submission

- [ ] **TI2V vs T2V comparison** — run `wan_ti2v_runner.py` with current 60 GPT-Image-1 first frames; eval; compare to pure T2V on standard + TeachQuiz-T. *Hypothesis: TI2V improves CC/NS even when first frames are imperfect.*
- [ ] **v0.2 high-difficulty TeachQuiz-T** — re-run TeachQuiz on the 22 graduate cases (we only have standard eval for these so far).
- [ ] **Wan5B v0.2 high-difficulty** — only Wan1.3B has been evaluated at graduate level; missing a 5B baseline.
- [ ] **Human rater study** — small (≤200 ratings) human validation of GPT-5.5 dimension scores; report inter-rater agreement and judge-vs-human correlation.

### 7.2 Should-have

- [ ] **Improve first-frame PASS rate** — current 25/60 with GPT-Image-1 medium quality. Options: re-run FAIL set at high quality (~$3, expected 40+ PASS), or accept current state and proceed.
- [ ] **Audio-narration alignment dim** — adapt VABench protocol; needs Wan model variant with audio (or post-hoc TTS + sync judge).
- [ ] **Triple-modal alignment dim** — combines text + visual + audio.
- [ ] **Closed-model T2V baseline** — pick 1–2 commercial APIs (Kling 2.0, Veo 2, Sora) for the 60-case pilot. Budget ≈ $500–1500.

### 7.3 Nice-to-have

- [ ] **Expand to 300-case v1.0** — gated on human-rater feedback validating prompt quality.
- [ ] **30–60s long video study** — current 5s max is well below real teaching content length; show how dimensions degrade with duration.
- [ ] **Ablation: visual probe quality** — does varying the number of probe questions (3 → 5 → 10) move learning gain estimates?
- [ ] **More student models** — currently Qwen3-VL-2B; add a second student (e.g. PaliGemma 2-3B) to test learner-dependence of TeachQuiz-T.

### 7.4 Known negative findings to preserve

- **MMMU/AI2D first-frame retrieval underperforms** — even with 86% lenient PICK rate, strict opening-frame judge accepts only 4/60 because MMMU images are exam questions, not pedagogical opening frames. Documented for the paper as evidence that *teaching-video generation needs purpose-built opening-frame resources*.
- **Open-source T2I (SD 3.5, FLUX.1-dev) cannot render educational text/symbols reliably** — 2 iterations of FLUX with judge-feedback prompts produced essentially zero net PASS improvement; only Azure GPT-Image-1 broke through (2 → 25 PASS).

---

## 8. Deliverables

| Artifact | Status | Path |
|---|---|---|
| 60-case + 82-case prompt set | ✅ | `data/prompts/` |
| 60 first-frame images | ✅ | `data/first_frames/` |
| Generation runners (T2V + TI2V) | ✅ | `generation/runners/` |
| 9-dim evaluation modules | ✅ 7 of 9 | `eval/dimensions/` |
| Multi-student TeachQuiz-T harness | ✅ | `eval/run_teachquiz.py` + `eval/students/` |
| Reproducibility orchestrator | ✅ | `scripts/run_full_pipeline.sh` |
| Paper draft | ⏳ | `docs/REPORT.md` (narrative skeleton) |
| Human-rater UI / data | ⏳ | not started |
| ICLR 2027 submission | ⏳ | target Oct 2026 |

---

## 9. Open questions

1. **Should TeachQuiz-T use multiple student models** in the final paper to show metric robustness, or stick with Qwen3-VL-2B for clean reporting?
2. **How to handle the "GPT-Image-1 frames are ours, MMMU frames are theirs" attribution** in the dataset release? Probably distribute the auto-probes + checkpoints, not the raw first-frame PNGs.
3. **Should 30–60s long videos be a separate paper or a section** of the main paper? Current 5s data is solid; longer videos need much more compute / API budget.
4. **Do we cite the negative MMMU finding** as a main contribution or as appendix material? Suggested: appendix + one paragraph in main text on dataset design choices.
