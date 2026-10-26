# rise-teacher — Project Plan

> Research direction updated: 2026-10-12. [`STATUS.md`](STATUS.md) is the evidence ledger; [研究方向规划](项目研究方向_相关工作综合建议.md) is the current decision document; [new survey](教学视频生成_统计调研.html) is the related-work table. The implementation inventory below is historical and must be checked against `STATUS.md` before use.

> Execution audit (2026-10-26): [`PAPER_EXECUTION_GATES.md`](PAPER_EXECUTION_GATES.md) gives the current acceptance criteria for item review, layout evidence, human validation, and matched experiments. The 400 rows are a candidate pool, with zero items passing the new independent-review export gate so far. Older checkmarks below describe infrastructure or pilot observations, not a submission-ready benchmark.

---

## 1. Positioning

**rise-teacher** currently evaluates short instructional clips on knowledge-explanation and problem-solving tasks. The research position after the October 2026 survey is:

- **A. Diagnostic evidence** — localize visible knowledge errors by step and frame, with explicit unobservable cases. Breadth alone is insufficient: EduVideoBench already spans seven subjects and five grade bands.
- **B. Measurement validity** — test whether a frozen proxy-student quiz measures transferable learning, beyond Code2Video's TeachQuiz and Video-MMMU's perception/comprehension/adaptation questions.
- **C. Conditional generation** — test whether verified executable teaching states improve the *final pixel video*, beyond correct code or a correct first frame. Code2Video and ALGOGEN are code-side references, not duration-matched pixel-T2V baselines.
- **D. Multi-shot state repair** — a later-stage method question; compare with existing storyboard, repair, and memory systems, including PIVOT and ManimAgent.

**Near-term paper scope.** A diagnostic benchmark for 3–5 s instructional clips, with expert defect labels and an independently validated proxy-learning analysis. The pilot's low rubric/proxy correlation does not establish a gap with human learning.

**Direct comparisons.** PhyEduVideo, VideoScience-Bench, Sci-VBench, EduVideoBench (educational scoring); Code2Video and Video-MMMU (quiz protocols); Code2Video, ALGOGEN, ManimAgent, and PIVOT (method positioning). See the [survey](教学视频生成_统计调研.html) for task scale, prompt source, and duration definitions.

**Venue and claim language.** Recheck deadlines and current related work before submission. Do not claim a first multi-discipline educational-video benchmark, first TeachQuiz, or human learning gains from current proxy data.

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

### 3.2 Task types (both represented across the 12 disciplines)

- **explanation** — concept introduction (e.g., "what are interior angles of a triangle").
- **problem_solving** — for 3–5 s clips, one checkable step of a worked solution, with the full problem, prior state, expected next state, and answer recorded. Full step-by-step solutions belong to the later multi-shot study.

The 60-case pilot contains five prompts per discipline, not five prompts per discipline-task cell. Audit its 24 discipline × task cells before using it to claim balanced joint-task coverage. A proposed frozen extension is at least five cases per cell (120 total), subject to source and expert review.

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

## 5. Evaluation framework (six video dimensions, one proxy metric, two planned audio dimensions)

The six implemented video-only rubric dimensions form the current scorecard. TeachQuiz-T is a separate proxy-student outcome on a different scale and must not be added to the rubric aggregate. Audio–Narration Alignment and Triple-Modal Alignment remain designs until audio-capable outputs and human validation exist.

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

### 6.3 Pilot observations and limits

1. In the 60-case pilot, rubric score and Qwen3-VL-2B normalized proxy gain have low observed correlation: r²=4.5% for Wan5B and 0.9% for Wan1.3B. This is not a human-learning result.
2. The paired aggregate difference between Wan5B-3s and Wan1.3B-3s is -0.0683; its 95% CI [-0.1775, 0.0425] includes zero. There is no established aggregate winner.
3. Wan5B 5s versus 3s shows a visual-quality decrease of 0.4167 (95% CI [-0.6000, -0.2417]); the narrative-structure increase does not survive Holm correction. Other subgroup patterns remain exploratory.
4. The 22-case graduate stress result covers Wan1.3B only. Matched Wan5B generation and canonical proxy evaluation are still required.

---

## 7. TODO (prioritized)

### 7.1 Must-have for paper submission

- [x] **Paired uncertainty machinery for existing standard-eval comparisons** — case-level effect size, 95% bootstrap CI, paired sign-flip test, and Holm correction are implemented in `scripts/compare_standard_eval.py`; all future final comparisons must run it too.
- [ ] **Freeze diagnostic evidence** — define visible teaching steps, error types, evidence timestamps, and an explicit unobservable label; double-rate the defect subset. Compare error localization with the existing six dimensions and EduVideoBench-style educational scoring.
- [ ] **Independent model family** — evaluate the same frozen prompts with at least one non-Wan T2V system; report paired results by error type, discipline, task, and difficulty.
- [ ] **Frozen learning questions** — separate perception, comprehension, and transfer questions, following Video-MMMU's structure; keep the final quiz unavailable to generation and repair systems.

- [ ] **TI2V vs T2V comparison** — run `wan_ti2v_runner.py` with current 60 GPT-Image-1 first frames; eval; compare to pure T2V on standard + TeachQuiz-T. *Hypothesis: TI2V improves CC/NS even when first frames are imperfect.*
- [ ] **v0.2 high-difficulty TeachQuiz-T** — re-run TeachQuiz on the 22 graduate cases (we only have standard eval for these so far).
- [ ] **Wan5B v0.2 high-difficulty** — only Wan1.3B has been evaluated at graduate level; missing a 5B baseline.
- [ ] **Human rater study** — collect the planned 60-video × 3-rater packet; report agreement, unobservable rates, and judge-vs-human correlation. Infrastructure alone is not validation.

### 7.2 Should-have

- [ ] **Code2Video feasibility check** — run the author's implementation on 8–12 matching, Manim-expressible tasks; record task coverage, actual video duration, render success, time, tokens, and quiz outcomes. Treat it as a separate code-video reference because current pixel clips last 3–5 s.
- [ ] **Executable-state pixel test** — on the same tasks, compare pure T2V, ordinary first-frame TI2V, verified human/template first-frame TI2V, and verified code-rendered first-frame TI2V. Measure final-video fact retention and cost; keep ALGOGEN-style trace correctness separate from pixel correctness.
- [ ] **Improve first-frame PASS rate** — current 25/60 with GPT-Image-1 medium quality. Options: re-run FAIL set at high quality (~$3, expected 40+ PASS), or accept current state and proceed.
- [ ] **Audio-narration alignment dim** — adapt VABench protocol; needs Wan model variant with audio (or post-hoc TTS + sync judge).
- [ ] **Triple-modal alignment dim** — combines text + visual + audio.
- [ ] **Closed-model T2V baseline** — pick 1–2 commercial APIs (Kling 2.0, Veo 2, Sora) for the 60-case pilot. Budget ≈ $500–1500.

### 7.3 Nice-to-have

- [ ] **Expand to 300-case v1.0** — gated on human-rater feedback validating prompt quality.
- [ ] **15–30s multi-shot study** — after the short-clip diagnostic gate, test knowledge-state transfer and dependency-aware repair against equal-budget storyboard, whole-video retry, and ManimAgent-style memory controls.
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

1. **Does TeachQuiz-T remain stable across student models and transfer questions, and does it track blinded human learning?** Until measured, report it as proxy gain.
2. **How to handle the "GPT-Image-1 frames are ours, MMMU frames are theirs" attribution** in the dataset release? Probably distribute the auto-probes + checkpoints, not the raw first-frame PNGs.
3. **Can a verified executable state survive pixel rendering?** First-frame success and code render success are intermediate checks; the final video is the outcome.
4. **Do we cite the negative MMMU finding** as a main contribution or as appendix material? Suggested: appendix + one paragraph in main text on dataset design choices.
