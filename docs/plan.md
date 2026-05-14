# rise-teacher — Project Plan

> Last updated: 2026-05-12.
> Companion docs: `survey.md` (related work), `README.md` (TBD).

---

## 1. Positioning

**rise-teacher** is a benchmark for evaluating video generation models on **multi-discipline knowledge-explanation + problem-solving** tasks. It commits to all three novelty levers identified in the survey:

- **A. Discipline breadth** — first pixel-T2V edu benchmark to cover STEM + humanities + social sciences + medicine + CS.
- **B. Joint task design** — each discipline contributes both *explanation* and *problem-solving* prompts; evaluated in one unified protocol.
- **C. Pedagogy-aware evaluation** — 8 dimensions including audio-narration alignment and didactic-affordance scoring, novel relative to PhyEduVideo and VideoScience-Bench.

**One-line elevator pitch.** *"PhyEduVideo + VideoScience-Bench, but broadened from physics/chemistry to a 12-discipline pedagogy stress test, with both explanation and problem-solving tracks, and pedagogy-specific evaluation including audio narration."*

**Must-cite competitors** (see survey §2 + §6): RISE-Video, PhyEduVideo (the heaviest overlap — 5 axes overlap with our pedagogy dims), VideoScience-Bench, CODE2VIDEO (source of the TeachQuiz idea we port to pixel-T2V), VABench (source of audio-eval protocols we adapt to instructional narration). ⚠️ Earlier-cited "VisualEDU" is unverified — must re-check before citing.

**Target venue (primary):** ICLR 2027 (deadline ~Oct 2026, ~5 months from now).
**Backup:** NeurIPS 2027 Datasets & Benchmarks Track (May 2027).

---

## 2. Scope

### 2.1 Disciplines (12)

| # | Discipline | Subdomains (examples) |
|---|---|---|
| 1 | Mathematics | algebra, calculus, geometry, probability |
| 2 | Physics | mechanics, EM, thermo, optics, modern |
| 3 | Chemistry | inorganic, organic, reactions, equilibrium |
| 4 | Biology | cell, genetics, anatomy, ecology |
| 5 | Medicine | anatomy, pathology, pharmacology procedures |
| 6 | Computer Science | algorithms, data structures, networks, OS |
| 7 | History | events, timelines, biographical |
| 8 | Geography | physical, political, climatology |
| 9 | Economics & Finance | micro, macro, financial instruments |
| 10 | Social Studies & Civics | political systems, sociology |
| 11 | Language & Literature | grammar concepts, literary analysis |
| 12 | Art & Music Theory | composition, periods, technique |

Coverage rationale: groups 1–6 = STEM (overlap with competitors, but extended); 7–12 = humanities/social (entirely new territory for pixel-T2V edu eval).

### 2.2 Task types (per discipline)

- **Explanation:** "*Generate a 10-second video explaining mitosis at the high-school level.*" Output should depict the concept correctly, in a teaching style.
- **Problem-solving:** "*Generate a video that solves: find the derivative of x³ + 2x and explain each step.*" Output should walk through reasoning steps visually.

### 2.3 Target scale

- ~40 cases per discipline (20 explanation + 20 problem-solving) → **~480 total cases**.
- Difficulty mix per task: K-12 / undergrad / professional ≈ 50% / 35% / 15%.
- Each case = `(text prompt, optional first-frame image, ground-truth annotation)` triple.
- Models supporting both T2V and TI2V will be tested on both modes; the benchmark itself releases prompts + reference frames.

### 2.4 Out of scope (explicit)

- Code-to-video (Manim-style — owned by CODE2VIDEO / VisualEDU).
- Long-form lecture (>60 seconds — current SOTA models don't support; revisit in v2).
- Interactive / multi-turn video.
- Music generation quality (we evaluate music *theory* visualizations, not music generation itself).

---

## 3. Data construction pipeline

```
[1] Discipline expert curates concept/problem list (from textbooks + standards)
       ↓
[2] Two annotators independently draft prompts + ground-truth rubric
       ↓
[3] First-frame image generation (Imagen / FLUX / Midjourney) for TI2V variant
       ↓
[4] Cross-review + IRR check (target Cohen's κ ≥ 0.7 on rubric items)
       ↓
[5] Pilot generation with 2 models → rubric stress-test → revise
       ↓
[6] Freeze v1 release set
```

**Annotation schema (per case):**
- `discipline`, `subdomain`, `task_type` ∈ {`explanation`, `problem_solving`}, `difficulty` ∈ {`k12`, `undergrad`, `professional`}
- `prompt_text` (50–200 words)
- `first_frame_image_path` (optional)
- `expected_concepts`: list of key concepts the video must depict correctly
- `expected_visual_elements`: list of objects/diagrams that should appear
- `expected_narrative_order`: ordered step list (esp. for problem-solving)
- `pedagogical_target_audience`
- `discipline_specific_rubric`: 3–5 yes/no checks (e.g., "molecule has correct stoichiometry")
- `audio_narration_required`: bool — does this case test audio quality?

**Source materials (for discipline experts):**
- K-12: Khan Academy concept index, CCSS / NGSS, IB / A-Level syllabi
- Undergrad: open textbook indices (OpenStax), MIT OCW, Coursera course outlines
- Question banks: discipline-appropriate sources (math competitions, MedQA, Bar Exam framings, etc.) for problem-solving difficulty calibration

**Estimated annotator workload:** ~1 case/hour with cross-review → 480 cases × 2 annotators × 1h ≈ **960 person-hours**. Budget for ~6 paid expert annotators (one per 2 disciplines), ~30h each.

---

## 4. Evaluation framework

> **Post deep-dive update (2026-05-12):** PhyEduVideo's 5 axes (Element Layout / Attractiveness / Logic Flow / Visual Consistency / Accuracy & Depth) overlap heavily with our originally-proposed pedagogy dims. The framework has been re-stacked around **5 strictly-novel dims + 4 inherited dims**, and we add **Learning Gain** as the headline novelty (pixel-T2V port of Code2Video's TeachQuiz, never before applied across disciplines).

### 4.1 Nine evaluation dimensions

🆕 = strictly novel relative to all verified prior work. 📐 = inherited (with proper attribution).

| # | Dimension | Novelty | Type | Source / Inspiration | What it scores |
|---|---|---|---|---|---|
| 1 | **Conceptual Correctness** | 📐 | LMM judge + rubric | RISE-Video Reasoning Alignment prompt structure + PhyGenEval 3-stage + discipline-tuned retrieval-augmented judge | Did the video depict the concept correctly under the discipline's canonical knowledge? |
| 2 | **Narrative Structure** | 📐 | Multi-frame LMM judge | PhyEduVideo Logic Flow; new in problem-solving context | Are steps presented in a teachable order (hook → body → summary; worked-example progression)? |
| 3 | **Didactic Affordances** | 📐 | LMM judge + OCR | PhyEduVideo Element Layout | Are labels / arrows / on-screen text legible and informative? |
| 4 | **Audience Appropriateness** | 🆕 | LMM judge | NEW — verified gap | Does vocabulary, depth, pacing match `pedagogical_target_audience` (K-12 / undergrad / professional)? |
| 5 | **Audio–Narration Alignment** | 🆕 | Whisper + LMM judge + SyncNet/AVSync15 | Adapts VABench (Veo 3/Sora 2/Wan 2.5 audio benchmark) to instructional narration | If audio present: does narration match on-screen content semantically, terminologically, and in pacing? |
| 6 | **Triple-Modal Alignment** | 🆕 | LMM judge over narration + frames + OCR | NEW — verified gap | Are narration ↔ visual ↔ on-screen text mutually consistent (no contradictions across modalities)? |
| 7 | **Learning Gain (TeachQuiz-T)** | 🆕 | "Student" VLM unlearn → watch → re-quiz | Port of Code2Video TeachQuiz to pixel-T2V; never applied across humanities/medicine/CS | A "student" VLM is concept-unlearned, watches the generated video, then is quizzed; recovery % = pedagogical effectiveness |
| 8 | **Temporal Consistency** | 📐 | VBench primitives | RISE-Video; VBench-2.0 | Frame-to-frame coherence; subject persistence |
| 9 | **Visual Quality** | 📐 | DOVER/MANIQA + LMM aesthetic | RISE-Video | Aesthetic, artifact-free, resolution adequacy |

**Headline framing for the paper:** rise-teacher is the first benchmark to combine (a) audience-aware pedagogical eval, (b) instructional audio-narration eval (extending VABench from generic audio to teaching narration), (c) triple-modal consistency, (d) **learning-gain estimation via a "student" VLM**, and (e) **discipline-tuned correctness judges** for non-STEM disciplines (history, language, civics, etc.).

### 4.2 Weights (initial proposal — to be re-tuned vs. human ratings in pilot M3)

```
Conceptual Correctness:   0.20
Narrative Structure:      0.10
Didactic Affordances:     0.08
Audience Appropriateness: 0.08
Audio-Narration Alignment:0.10   (0 if model has no audio; re-normalize)
Triple-Modal Alignment:   0.10   (0 if model has no audio; re-normalize)
Learning Gain:            0.20   (headline metric; high weight)
Temporal Consistency:     0.08
Visual Quality:           0.06
                          ----
                          1.00
```

### 4.3 Judge model strategy

- **Primary judge:** GPT-5.4 (cross-model from generators — avoid self-preference).
- **Ensemble cross-validation:** Gemini-2.5 + Qwen2.5-VL-72B + InternVL3.5 on a 20% random sample. Disagreements > 1.5σ → human adjudication.
- **Discipline-tuned correctness judge (dim #1):** retrieval-augmented prompt — judge has access to textbook passages for the case's specific concept. Novel for video eval.
- **Audio judge (dim #5):** Whisper-Large-v3 transcribe → semantic alignment via SBERT; pacing via word-rate vs. on-screen change rate; SyncNet/AVSync15 for lip/speech-event sync.
- **Student VLM for dim #7:** open-weights VLM (Qwen2.5-VL-7B baseline) that we can controllably "unlearn" via task-vector subtraction or fine-tuning on negation examples. (Implementation detail to validate in M2-M3.)
- **Human baseline:** 100 cases × all 9 dimensions × 3 raters → Cohen's κ + Krippendorff's α vs. judge models. Target: α ≥ 0.6 (objective dims) and α ≥ 0.4 (subjective dims like Audience Appropriateness) to claim eval is reliable.

### 4.4 Reporting modes

- Per-dimension scores (mean ± seed std)
- Aggregate weighted score (audio-bearing models normalized)
- **Strict accuracy** (RISE-Video style): all dimensions pass threshold → 1, else 0
- **Pedagogy-only score:** weighted aggregate of dims 1–7 (excludes generic Temporal/Visual primitives) — the "did this actually teach?" axis
- Per-discipline / per-task-type / per-difficulty breakdowns
- Per-modality breakdown (audio-capable vs. silent models)

---

## 5. Models to evaluate

| Tier | Model | Audio? | Notes |
|---|---|---|---|
| Closed | Sora 2 | ✓ | OpenAI |
| Closed | Veo 3.1 | ✓ | Google |
| Closed | Hailuo 2.3 | varies | MiniMax — top scorer on RISE-Video |
| Closed | Kling 2.6 | varies | Kuaishou |
| Closed | Seedance 1.5-pro | ✓ | ByteDance |
| Open | HunyuanVideo-1.5 | — | Tencent |
| Open | CogVideoX1.5-5B | — | Zhipu |
| Open | Wan 2.6 | — | Alibaba |
| Open | Kandinsky 5.0 | — | Sber |
| Open | StepVideo (latest) | — | StepFun |

Target: **≥10 models**, ≥5 of which produce audio (to power the audio-narration dim).

**Inference cost estimate:** ~480 cases × 10 models × 1 video (8s @ 720p) ≈ 4,800 generations. Closed APIs: ~$0.5–$2/video → $2.5K–$10K. Open models: GPU compute, ~200 GPU-hours.

**Evaluation cost estimate:** ~4,800 videos × 8 dims × GPT-5.4 judge calls ≈ 38K calls × ~$0.05 avg → ~$2K.

**Total compute/API budget:** ~$8K–$15K + 200 GPU-hours.

---

## 6. Timeline & milestones (≈20 weeks)

Targeting **ICLR 2027** (deadline ~early Oct 2026 ⇒ ~21 weeks from 2026-05-12).

| Wk | Milestone | Deliverable |
|---|---|---|
| 1–2 | Lock taxonomy + dimension definitions + pilot 30 cases | `taxonomy.md`, pilot data, agreed rubric |
| 3–4 | Recruit 6 discipline experts + annotation training | Signed annotator pool, training docs |
| 5–8 | Build full 480-case dataset + dual annotation | `data/` v0.9 |
| 9–10 | Build eval pipeline (fork RISE-Video skeleton) + pilot judge prompts | `eval/` v0.9 |
| 11 | Run pilot eval on 2 models × 30 cases, validate dims with 5 human raters | Pilot report, IRR numbers |
| 12 | Freeze v1.0 dataset + eval prompts | Frozen artifacts |
| 13–15 | Full inference: 10 models × 480 cases × {T2V, TI2V where supported} | All generations |
| 16–17 | Full evaluation: 8 dims × ensemble judge | Score matrices |
| 18 | Human evaluation study (100 cases × 5 dims × 3 raters) | Human-vs-judge κ |
| 19 | Analysis + paper draft | Draft v1 |
| 20–21 | Polish, ablations, submit | ICLR 2027 submission |

**Critical-path risks:**
- Annotator availability for humanities/social → if blocked, descope to 8 disciplines for v1, add 4 in v2.
- Audio-track support uneven across closed APIs → if <4 models produce audio, demote dim #6 weight or move to an "audio supplement" track.

---

## 7. Deliverables

| Artifact | Channel | Format |
|---|---|---|
| Prompts + first-frame images + annotations | HuggingFace dataset `rise-teacher/rise-teacher-v1` | JSONL + images |
| Generated videos | HuggingFace dataset `rise-teacher/generations-v1` | MP4 with metadata |
| Eval code + judge prompts | GitHub `rise-teacher/rise-teacher` | Python; MIT or Apache-2 |
| Leaderboard | Project site (HF Space) | Web UI |
| Paper | ICLR 2027 / NeurIPS 2027 D&B | LaTeX + arXiv |

---

## 8. Repository layout (proposed)

```
rise-teacher/
├── README.md
├── plan.md                   ← this file
├── survey.md                 ← related work
├── taxonomy.md               ← discipline + difficulty schema (TBD)
├── data/
│   ├── prompts/              ← .jsonl per discipline
│   ├── first_frames/         ← .png per case
│   └── annotations/          ← .jsonl rubrics
├── generation/
│   ├── runners/              ← per-model inference scripts
│   └── outputs/              ← .mp4 (gitignored — uploaded to HF)
├── eval/
│   ├── dimensions/           ← one module per dim
│   ├── judges/               ← LMM judge prompts + clients
│   ├── audio/                ← Whisper + sync metrics
│   └── aggregate.py
├── analysis/                 ← plots, leaderboard generator
├── paper/                    ← LaTeX
└── tests/
```

---

## 9. Risks & contingencies

| Risk | Likelihood | Mitigation |
|---|---|---|
| A direct competitor (e.g., "EduVideo-Bench" by another lab) lands during Q2–Q3 2026 | Med | Move fast on humanities + audio dims — those are the hardest to copy quickly |
| RISE-Video repo license is restrictive | Low–Med | Reimplement eval skeleton from scratch (~2 weeks); pipeline isn't complex |
| Annotator IRR low on subjective dims (Clarity, Affordances) | Med | Add rubric-anchored examples; merge or remove the worst-performing dim |
| Audio support sparser than expected | Med | Reweight audio dim to zero for non-audio models; report separately |
| API budget overrun | Low | Cap closed-API runs at 1 seed; only open models get multi-seed |
| Reviewer pushback on "yet another T2V benchmark" | High | Lean on humanities + joint-task framing in story; explicitly position as the *first* of those |

---

## 10. Immediate next actions (this week)

1. ☐ Confirm RISE-Video repo license — open GitHub issue.
2. ☐ Read RISE-Video `reasoning_eval/` source — verify prompt design we plan to adapt (structure confirmed via deep-dive: restate-rule → cite-frames → binary+1-5+reasoning).
3. ☐ **Read Code2Video TeachQuiz implementation** — we need the "VLM unlearning" protocol to port it to pixel-T2V (rise-teacher's headline dim #7).
4. ☐ **Read VABench source** — adapt audio-eval protocols from generic audio quality to instructional narration.
5. ☑ ~~Verify VisualEDU citation~~ — verified real (EMNLP 2025 Findings, Hao Chen et al., Manim, 9 VLMs).
6. ☐ Draft `taxonomy.md` v0.1 with the 12 disciplines × subdomain trees.
7. ☐ Recruit 1–2 humanities/social-science annotators (hardest to source).
8. ☐ Pilot 5 cases (math explanation, math problem-solving, history explanation, biology explanation, CS problem-solving) → generate with Sora 2 + Hailuo 2.3 → manually rate to stress-test the 9-dim rubric.
9. ☐ ✅ `survey.md` §5 deep dive completed (2026-05-12).
