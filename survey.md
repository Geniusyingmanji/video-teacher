# rise-teacher — Related Work Survey

> Living document. Last updated: 2026-05-12.
> Scope: prior art for a benchmark that evaluates **multi-discipline knowledge-explanation + problem-solving video generation**, derived from the RISE-Video pipeline with pedagogy-aware evaluation dimensions.

---

## 1. Parent benchmark: RISE-Video

- **Paper:** "RISE-Video: Can Video Generators Decode Implicit World Rules?" — arXiv 2602.05986 (VisionXLab; Liu, Ma, Meng, Zhao et al.). https://arxiv.org/abs/2602.05986
- **Task setting:** Text-Image-to-Video (TI2V). Each case = first-frame image + text prompt. Model must produce a video that obeys an *implicit* world rule (not just look pretty).
- **Data:** 467 human-annotated cases, 8 knowledge categories — Commonsense, Subject, Perceptual, Societal, Logical Capability, Experiential, Spatial, Temporal. Schema is fixed; adding a new category requires re-curation from scratch.
- **Evaluation:** Four LMM-as-judge dimensions, all OpenAI-API driven.

  | Dimension | Weight | What it measures |
  |---|---|---|
  | Reasoning Alignment | 0.40 | Did the video respect the implicit rule? |
  | Temporal Consistency | 0.25 | Frame-to-frame coherence |
  | Physical Rationality | 0.25 | Plausible physics |
  | Visual Quality | 0.10 | Aesthetic / artifact-free |

- **Code:** https://github.com/VisionXLab/Rise-Video — modules `reasoning_eval/`, `phy_rationality_eval/`, `img_quality_eval/`, `consis.py`, generic `fps_clip.py` + `eval.py`. **License not declared in README — must confirm via issue before forking.**
- **Data release:** https://huggingface.co/datasets/VisionXLab/RISE-Video
- **Models evaluated (11):** Hailuo2.3, Veo3.1, Sora-2, Wan2.6, Kling2.6, Seedance1.5-pro, Kandinsky-5.0 (variants), HunyuanVideo-1.5, CogVideoX1.5-5B. Headline: Hailuo2.3 79.4% weighted / 22.5% strict; CogVideoX1.5-5B 49.5% / 1.9% — large "looks-ok vs. actually-obeys-rule" gap.
- **Reusability for rise-teacher:** Frame extraction (`fps_clip.py`) and LMM-judge loop (`eval.py`) are generic. The 8-category schema, rubric prompts, and per-dimension scorers are **hard-coded** and must be rewritten for pedagogy.

---

## 2. Adjacent prior work: education / instructional video generation benchmarks

This subspace exploded in late 2025–early 2026. All four works below must be cited and contrasted in rise-teacher's related work.

### 2.1 PhyEduVideo (arXiv 2601.00943, Jan 2026 / WACV 2026)
- **Closest direct precedent.** https://arxiv.org/html/2601.00943
- **Scope:** 205 prompts, 60 physics concepts, 6 sub-domains (mechanics, waves, thermo, EM, fluids, optics).
- **Eval dimensions (5 — corrected after deep-dive):** Element Layout, Attractiveness, Logic Flow, Visual Consistency, Accuracy & Depth — VLM-as-Judge. Plus a separate **3-stage LLM judge for Physics Commonsense** (phenomenon detection → ordering → naturalness), mirroring PhyGenEval. Plus a 500-video human rating study. Spearman with humans: 0.509 Semantic Adherence / 0.392 Physics Commonsense.
- **Models:** 5 T2V models. Finding: T2V looks smooth but fails conceptual accuracy on EM/thermo.
- **Code:** https://github.com/meghamariamkm/PhyEduVideo
- **⚠ Implication for rise-teacher:** PhyEduVideo's 5 axes overlap heavily with our originally-proposed pedagogy dims (Logic Flow ≈ Narrative Structure; Element Layout ≈ Didactic Affordances; Accuracy & Depth ≈ Conceptual Correctness). To stay novel we must lean on: (a) Audience Appropriateness, (b) Audio-Narration Alignment, (c) Learning Gain (TeachQuiz-style port), (d) discipline breadth — see §6 + plan.md §4.

### 2.2 VideoScience-Bench (arXiv 2512.02942, Dec 2025)
- **Scope:** 200 prompts, 14 topics, 103 concepts across physics + chemistry. T2V and I2V. 7 models.
- **Eval dimensions (5):** Prompt Consistency, Phenomenon Congruency, Correct Dynamism, Immutability, Spatio-Temporal Continuity. VLM judge + expert annotation.
- **Framing:** Video generation as "reasoner + generator" — explicitly treats T2V as a scientific reasoning task.
- **Code:** https://github.com/hao-ai-lab/VideoScience
- **Relevance:** Overlaps physics + chemistry. Their 5-dim breakdown is the strongest competitor for our eval design; we must propose strictly broader or pedagogy-specific dimensions.

### 2.3 CODE2VIDEO (arXiv 2510.01174, Oct 2025)
- **Scope:** 13 subject categories of educational videos generated via **Manim code** rather than pixel-level T2V. https://arxiv.org/pdf/2510.01174
- **Relevance:** Multi-discipline tutorial benchmark — but a different modality (code → animation). Easy differentiation since rise-teacher targets pixel-level T2V (Sora/Veo/Hailuo class models). Still must be cited as the closest "multi-subject" precedent.

### 2.4 VisualEDU (EMNLP 2025 Findings) — ✅ verified
- **Citation:** Hao Chen, Tianyu Shi, Pengran Huang, Zeyuan Li, Jiahui Pan, Qianglong Chen, Lewei He. "VisualEDU: A Benchmark for Assessing Coding and Visual Comprehension through Educational Problem-Solving Video Generation." Findings of EMNLP 2025. https://aclanthology.org/2025.findings-emnlp.889
- **Scope:** Benchmarks VLM ability to generate step-by-step educational videos via **Manim** code for complex reasoning tasks (math-heavy). 9 VLMs evaluated.
- **Headline:** Even Claude / GPT-4o-class models score < 56 % on the harder problems. Proposes evaluation metrics targeting code generation and tool-use weaknesses.
- **Relevance to rise-teacher:** Like CODE2VIDEO, it's *code-driven* not *pixel-T2V*. Differentiation: rise-teacher evaluates the raw pixel-T2V models (Sora/Veo/Hailuo/Wan) under the same educational lens — so VisualEDU and rise-teacher are complementary, not redundant. Must-cite as the closest "educational problem-solving video benchmark" precedent.

### 2.5 V-ReasonBench (arXiv 2511.16668, Nov 2025)
- **Scope:** 4 reasoning dimensions — structured problem-solving, spatial cognition, pattern inference, physical dynamics. No explicit education category. https://arxiv.org/abs/2511.16668
- **Relevance:** Methodologically close (reasoning-style eval), but framed as general reasoning, not pedagogy.

### 2.6 Paper2Video (arXiv 2510.05096)
- **Scope:** Generates presentation videos from scientific papers; metrics for presentation quality. https://arxiv.org/pdf/2510.05096
- **Relevance:** Adjacent — *generation system* with quality metrics, not a benchmark per se. Useful for borrowing presentation-quality eval design.

---

## 3. General T2V benchmarks (no education axis, but rich eval-dim inventory)

| Benchmark | Scope | Why we cite it |
|---|---|---|
| **VBench / VBench-2.0** (https://vchitect.github.io/VBench-2.0-project/) | 16 → broader dim set, generic | Source of motion-smoothness / temporal-flickering / subject-consistency primitives we'll reuse |
| **EvalCrafter** | ~700 prompts, 17 metrics | Inventory for visual / motion / alignment metrics |
| **T2V-CompBench** | Compositional T2V | Borrow compositional alignment metric for multi-object educational scenes |
| **ChronoMagic-Bench** (https://github.com/PKU-YuanGroup/ChronoMagic-Bench) | Time-lapse, 4 categories | Metamorphic Strength Index — useful for "show me a chemical reaction over time" |
| **VideoScore** | Learned reward model | Could serve as one baseline among multiple judges |
| **VideoCon / FETV / T2VScore / AIGV-Assessor** | Various LMM-judge frameworks | Comparators for our LMM-judge methodology |

---

## 4. Understanding-side related (for question-source inspiration)

These are **video-comprehension** benchmarks (input = video → output = answer), not generation. We mine them for question pools, but they cannot be used as direct competitors.

- **Video-MMLU** (https://arxiv.org/html/2504.14693v1) — 1,065 multi-discipline lecture videos: math, physics, chemistry. Comprehension only.
- **SciVideoBench** (https://scivideobench.github.io/) — scientific video QA.
- **VideoMathQA** (https://arxiv.org/abs/2506.05349) — math QA over videos.

These are gold mines for **discipline coverage taxonomy** and **question difficulty calibration**.

---

## 5. Video Generation Evaluation Methods (deep dive)

### 5.1 Automatic distribution metrics

**FVD** ([Unterthiner et al., 2018](https://arxiv.org/abs/1812.01717)) computes Fréchet distance between Gaussian-fit distributions of I3D features on real vs. generated videos. **KVD** uses polynomial-kernel MMD over the same features (avoids Gaussianity assumption). **IS-V** reuses image-IS on sampled frames / C3D features. Now well-documented weaknesses: Ge et al. ([CVPR 2024](https://content-debiased-fvd.github.io/)) show FVD is dominated by per-frame content and largely insensitive to temporal distortion — FVD can be halved by selectively sampling even when motion is absent. [Beyond FVD](https://arxiv.org/abs/2410.05203) catalogs three flaws: non-Gaussian I3D features, temporal insensitivity, impractical sample sizes (~2048+) for stable estimates. [JEDi](https://oooolga.github.io/JEDi.github.io/) replaces I3D with JEPA features as a stronger alternative.

**CLIP-Score / CLIPSIM** ([ EMNLP 2021](https://aclanthology.org/2021.emnlp-main.595/)) — mean cosine between CLIP text and per-frame image embeddings. Reliable for nouns/colors, misses verbs/ordering/counting/physics. **VideoCLIP / X-CLIP / [InternVideo / ViCLIP](https://github.com/OpenGVLab/InternVideo)** jointly embed clips and text — stronger but trained for retrieval and weak on compositional/temporal queries.

**LPIPS / SSIM / PSNR** are full-reference metrics; meaningful only when ground-truth video exists (e.g., I2V continuation). LPIPS correlates best with human perception of distortion. Reference impls: https://github.com/JunyaoHu/common_metrics_on_video_quality. **Verdict for rise-teacher:** distribution metrics give a coarse global ranking but cannot score correctness or pedagogy — supplementary at best.

### 5.2 Frame / temporal quality

**DOVER / [MANIQA](https://github.com/IIGROUP/MANIQA) / MUSIQ / CLIP-IQA** are per-frame NR-VQA/NR-IQA models. Caveat: all were trained on real-photo distortions and systematically over-reward sharp/aesthetic frames while ignoring AIGC failure modes (warping, melting limbs, text gibberish) — see [VQA Survey](https://arxiv.org/html/2412.04508).

**VBench primitives** ([CVPR 2024](https://arxiv.org/abs/2311.17982); [GitHub](https://github.com/Vchitect/VBench)):
- *Temporal flickering* — inter-frame interpolation/reconstruction error on static regions
- *Motion smoothness* — frame-interpolation training-free motion priors
- *Dynamic degree* — [RAFT](https://github.com/princeton-vl/RAFT) optical flow (so videos aren't degenerately static)
- *Subject consistency* — DINO feature cosine across frames
- *Background consistency* — CLIP image features (DINO too instance-sensitive)
- *Aesthetic quality* — [LAION CLIP+MLP predictor](https://github.com/LAION-AI/aesthetic-predictor), known to bias toward Midjourney style

### 5.3 Semantic / instruction following

**VBench's 16 dimensions** ([CVPR 2024](https://github.com/Vchitect/VBench)) — subject/background consistency, temporal flickering, motion smoothness, dynamic degree, aesthetic quality, imaging quality, object_class (GRIT detection), multiple_objects (co-occurrence), human_action (UMT), color, spatial_relationship (rule-based on bboxes), scene (Tag2Text), temporal_style, appearance_style, overall_consistency (ViCLIP). **VBench-2.0** ([arXiv 2503.21755](https://arxiv.org/abs/2503.21755)) adds 18 fine-grained dims grouped as Human Fidelity, Controllability, Creativity, Physics, Commonsense.

**EvalCrafter** ([CVPR 2024](https://arxiv.org/abs/2310.11440)) — ~17 metrics across visual / content / motion / text-video buckets; learned coefficient fit to user opinions.

**T2V-CompBench** ([CVPR 2025](https://t2v-compbench.github.io/)) — 1,400 prompts × 7 compositional categories (attribute binding, spatial/motion/action binding, object interactions, generative numeracy).

**VideoScore / VideoScore-2** ([EMNLP 2024](https://arxiv.org/abs/2406.15252); [VideoScore-2](https://arxiv.org/html/2509.22799v1)) — learned Mantis/Qwen2.5-VL reward models trained on VideoFeedback (37K) and VideoFeedback2 (27K with CoT). Spearman 0.77 with humans — ~50 pts over CLIPSIM. **Usable as one judge ensemble member.**

**Physics-specific:** **VideoPhy** ([repo](https://github.com/Hritikbansal/videophy)) — 688 solid-solid/solid-fluid/fluid-fluid interaction captions; best model CogVideoX-5B passes only 39.6%. **PhyGenBench / PhyGenEval** ([ICML 2025, arXiv 2410.05363](https://arxiv.org/abs/2410.05363)) — 160 prompts × 27 physical laws; **3-stage VLM+LLM judge** (Key Phenomena Detection → Order Verification → Naturalness) — this is the prototype rise-teacher's Conceptual Correctness should follow.

**Time-lapse:** **ChronoMagic-Bench** ([NeurIPS 2024 D&B Spotlight, arXiv 2406.18522](https://arxiv.org/abs/2406.18522)) — MTScore (metamorphic amplitude) + CHScore (temporal coherence); useful for chemistry-reaction / biology-process explanations.

### 5.4 LMM-as-judge approaches

- **[T2VScore](https://showlab.github.io/T2VScore/)** — decomposes to alignment (GPT-generated VQA pairs + CoTracker trajectory checks) and quality (VLM mixture-of-experts).
- **FETV** ([NeurIPS 2023, arXiv 2311.01813](https://arxiv.org/html/2311.01813)) — fine-grained content/attribute/complexity categories with UMT metrics.
- **AIGV-Assessor** ([CVPR 2025, arXiv 2411.17221](https://arxiv.org/html/2411.17221v1)) — spatio-temporal features + LMM, scalar + pairwise.
- **VideoScore-2** ([project](https://tiger-ai-lab.github.io/VideoScore2/)) — explicit CoT then scalar scores; SFT + GRPO.

**Tradeoffs by judge input modality:**
| Modality | Cost ratio | Sees motion? | Use case |
|---|---|---|---|
| Single-frame | 1× | No | OCR / object presence |
| Multi-frame grid (4–9) | 5–10× | Coarse order | Most VBench-style dims |
| Full video input (Gemini-1.5-Pro / Qwen2.5-VL / InternVL3) | 20–50× | Yes, but opaque | Narrative / temporal reasoning |

**Judge-human agreement** ([MLLM-as-a-Judge](https://mllm-judge.github.io/)): GPT-4V scalar 0.557 / pairwise 0.806; Gemini-Pro-V scalar 0.332; LLaVA/CogVLM lower. Per [LLM Judge audit](https://arxiv.org/html/2510.09738v1), judge quality is more about training than size.

**Prompting strategies:** rubric anchors > naked scalar; pairwise > absolute for close generations. **Biases:** self-bias (GPT-4V rewards GPT-4V-like styles), position bias, verbosity bias.

**Cost rule of thumb:** $0.01–$0.05 / video / dim on GPT-4o-class with 8-frame 512px input. Full VBench-16 ≈ $0.15–$0.50 / video.

### 5.5 Audio-video / narration evaluation (CRITICAL for rise-teacher)

- **SyncNet** (Chung & Zisserman 2016) — two-stream CNN, contrastive on 100h speech; outputs Sync-C (confidence ↑) and Sync-D (offset ↓).
- **[AV-align](https://github.com/tavihalperin/AV-sync)** — dynamic speech-to-lips alignment.
- **AVSync15** ([ECCV 2024 Oral](https://lzhangbj.github.io/projects/asva/asva.html)) — 15-category VGGSound-derived benchmark; object-motion ↔ audio coupling (used by AVSyncD).
- **[VABench](https://arxiv.org/html/2512.09299v1)** — scores Veo 3 / Sora 2 / Wan 2.5 on audio quality, cross-modal alignment, lip-sync. **Headline:** Veo 3 leads audio quality + cross-modal alignment, Wan 2.5 leads lip-sync, Sora 2 leads realism but trails on audio aesthetics. **rise-teacher's audio dim can directly borrow VABench protocols and adapt to instructional narration.**

**Speech-visual semantic alignment** via Whisper transcript ↔ CLIP/SBERT text similarity is used ad-hoc — **no standardized benchmark exists for narration-content alignment**, especially not for instructional narration. ⇒ direct novelty space.

**Educational narration quality** (pace / terminology / scaffolding) — **verified gap**, no peer-reviewed benchmark.

### 5.6 Human evaluation protocols

- **Pairwise (A-vs-B)** more reliable than 5-point Likert for closely-matched generations.
- Field sample sizes: VBench ~100 raters across 16 dims; EvalCrafter ~10 raters × 700 prompts; VideoPhy 3 expert raters/sample.
- **Crowdsourced Elo leaderboards:** [VideoArena (Berkeley)](https://sky.cs.berkeley.edu/project/videoarena/), [Video Arena (Artificial Analysis)](https://artificialanalysis.ai/video/arena). Automated version: **VideoAutoArena** ([CVPR 2025, arXiv 2411.13281](https://arxiv.org/abs/2411.13281)).
- **IRR:** Cohen's κ for 2 raters; [Krippendorff's α](https://www.k-alpha.org/methodological-notes) for ≥2 raters / mixed measurement levels. Typical reported ranges: α 0.4–0.7 for subjective ("naturalness"), α 0.6–0.85 for objective ("object presence"). α ≥ 0.8 = high reliability.
- **Cost:** 30–90s / video / dim @ $0.08–$0.30 / min on Prolific/MTurk. 100 vids × 16 dims × 3 raters ≈ $400–$1500, 2–5 days wall clock.

### 5.7 Domain-specific pedagogical evaluation

**PhyEduVideo** ([WACV 2026, arXiv 2601.00943](https://arxiv.org/html/2601.00943)) — **5 axes** (not 4 as initially reported): Element Layout, Attractiveness, Logic Flow, Visual Consistency, Accuracy & Depth. Plus a **3-stage LLM judge for Physics Commonsense** mirroring PhyGenEval (phenomenon detection → ordering → naturalness). Reported Spearman with humans: 0.509 (Semantic Adherence), 0.392 (Physics Commonsense). **⚠ Implication for rise-teacher's design:** the 5 axes overlap heavily with several of our planned dims — see §6 below for adjusted novelty positioning.

**VideoScience-Bench** ([arXiv 2512.02942](https://arxiv.org/abs/2512.02942)) — 5 dims, all VLM judge: Prompt Consistency (PCS), Phenomenon Congruency (PCG), Correct Dynamism (CDN), Immutability (IMB), Spatio-Temporal Continuity (STC).

**Code2Video** ([arXiv 2510.01174](https://arxiv.org/pdf/2510.01174)) — three contributions:
1. VLM-as-Judge aesthetic + structural quality
2. Code efficiency (tokens + time)
3. **TeachQuiz** — a *learning-gain* metric: a VLM is "unlearned" on the target concept, then watches the video, then is re-tested; recovery percentage = teaching quality. **This is the closest operationalization of "did the student learn?" in current literature. We propose to port it to pixel-T2V (see updated plan §4).**

**VisualEDU** — ⚠️ **agent could not verify a paper of this name**. Earlier-cited link (`aclanthology.org/2025.findings-emnlp.889`) needs re-verification before any citation in our paper. Open question in `survey.md §7`.

**General pedagogy gap (verified):** no published video-generation benchmark systematically operationalizes "pedagogical clarity / narrative structure / didactic affordances / instructional design quality" beyond PhyEduVideo's Logic Flow + Element Layout and Code2Video's TeachQuiz.

### 5.8 Reasoning / world-rule evaluation

**[RISE-Video](https://github.com/VisionXLab/Rise-Video)** — 4 dims with weights {RA 0.4, TC 0.25, PR 0.25, VQ 0.1}. **Reasoning-Alignment prompt design** is the key transferable trick: judge must (i) restate the implicit rule, (ii) cite specific frames as evidence, (iii) deliver binary verdict + 1–5 score with reasoning. Structured-CoT prompting is the lift over naked scalar prompting. **Action item: replicate this prompt structure for our Conceptual Correctness dim.**

**V-ReasonBench** ([arXiv 2511.16668](https://arxiv.org/abs/2511.16668)) — 4 reasoning dims with hybrid eval (mask-based for object-region, grid-based for fine-grained, lightweight VLM for simple outputs).

**VideoCon-Physics** (VideoPhy-trained model) — implicit physical-rule violation detection via negation-prompt + discriminative VLM. The pattern (contrastive synthetic rule-breaks) is reusable for discipline-specific correctness in rise-teacher (e.g., "wrong stoichiometry," "anachronistic clothing in a historical scene").

⚠️ **CogVideoX-Eval** flagged by agent as **unverifiable** — CogVideoX is a model evaluated *on* VBench/VideoPhy, but has no standalone eval suite.

### 5.9 Practical & reproducibility

**Forkable open-source suites:**
- [VBench](https://github.com/Vchitect/VBench) (`pip install vbench`)
- [EvalCrafter](https://github.com/evalcrafter/EvalCrafter)
- [RISE-Video](https://github.com/VisionXLab/Rise-Video) — pipeline skeleton we plan to fork
- [T2V-CompBench](https://github.com/KaiyueSun98/T2V-CompBench)
- [VideoScore](https://github.com/TIGER-AI-Lab/VideoScore)

**Judge-model choice (agreement vs. humans):**
| Judge | Scalar | Pairwise | $/call | Notes |
|---|---|---|---|---|
| GPT-4V / 4o | 0.56 | 0.81 | High | Best agreement, self-bias risk |
| Gemini-1.5/2.0-Pro | 0.33–0.50 | 0.5–0.7 | Mid | Cheaper, full-video input |
| Qwen2.5-VL-72B | ~0.4–0.5 | ~0.7 | Low (self-host) | Open, ensemble member |
| InternVL3-78B | ~0.4–0.5 | ~0.7 | Low (self-host) | Open |

**Cost per 100 videos end-to-end:**
- VBench-style automatic: ~$5–$15 (compute, A100 ~6h)
- LMM judge × 16 dims: $30–$80 (GPT-4o-mini), $200–$500 (GPT-4o / Gemini-Pro)
- Full human pairwise × 16 dims × 3 raters: $600–$1500

**Variance / seeding:** VBench → 5 seeds/prompt; EvalCrafter → 1 seed, 700 prompts; VideoPhy → 3 seeds. **Statistical separability floor: 3–5 seeds × ≥100 prompts.**

### 5.10 Explicit gaps for multi-discipline educational video evaluation

Verified unaddressed problems that rise-teacher can claim:
1. **Pedagogical effectiveness** — only Code2Video TeachQuiz; no pixel-T2V port, no humanities/medicine/CS coverage
2. **Narrative / didactic structure** — no metric scores hook–body–summary scaffolding, worked-example progression, analogical bridging
3. **Audio-narration pedagogy** — pace, terminology calibration, signposting are unmeasured despite Veo 3.1 / Sora 2 producing speech
4. **Multi-discipline correctness** — current physics-only / phys+chem; legal-procedure, medical-protocol, code-execution, historical/literary canon correctness have no standardized judges
5. **Misconception detection** — distinguishing "wrong physics in a teaching video" from "correctly depicted counter-example" is unaddressed
6. **Triple-modal alignment** — narration ↔ visual ↔ on-screen text consistency
7. **Cognitive load / chunking** — no automatic measure of information density per second
8. **Domain-expert judges** — current LMM judges are generalists; medical/CS/math correctness needs domain-tuned or retrieval-augmented judges

---

## 6. Positioning gap analysis for rise-teacher (post deep-dive)

Of three novelty levers, **rise-teacher commits to all three (A + B + C)**. Deep-dive forced sharper scoping of C.

| Lever | Status in prior work | Gap rise-teacher fills |
|---|---|---|
| **A. Multi-discipline breadth** | All existing edu T2V benchmarks are STEM-only (PhyEduVideo: physics; VideoScience-Bench: phys+chem; CODE2VIDEO: 13 STEM subjects via code) | First pixel-T2V benchmark covering **STEM + humanities + social sciences + medicine + CS** |
| **B. Joint task: explanation + problem-solving** | Existing work picks one (PhyEduVideo/VideoScience-Bench evaluate phenomenon depiction; CODE2VIDEO evaluates instructional video quality; VisualEDU [unverified] evaluates problem solving) | First to evaluate **both** in one unified prompt set with paired metrics |
| **C. Pedagogy-aware eval dimensions** | PhyEduVideo already has Element Layout / Logic Flow / Visual Consistency / Accuracy & Depth. **Truly missing:** Audience Appropriateness; Audio-Narration Alignment (now feasible via VABench-style protocols); Learning Gain (only Code2Video's TeachQuiz on coded videos); narration ↔ visual ↔ on-screen-text triple alignment; discipline-tuned correctness judges | Propose **5 strictly-novel dims** stacked atop ~3 inherited dims. See plan.md §4. |

**C — sharpened novelty claim (post deep-dive):**
- Strictly novel: **Audience Appropriateness**, **Audio-Narration Alignment**, **Learning Gain (pixel-T2V port of TeachQuiz)**, **Triple-modal Alignment (Narration↔Visual↔OnScreenText)**, **Domain-Expert / Retrieval-Augmented Correctness Judges** (no existing video-eval benchmark uses these)
- Inherited (with attribution): Conceptual Correctness (from PhyGenEval 3-stage + RISE-Video Reasoning Alignment prompt design), Visual / Temporal primitives (from VBench)

**Must-cite-and-contrast set (verified):** RISE-Video, PhyEduVideo, VideoScience-Bench, CODE2VIDEO, V-ReasonBench, VBench-2.0, VideoPhy, PhyGenBench, Video-MMLU, VideoScore-2, VABench, T2VScore, FETV, AIGV-Assessor, VideoAutoArena. (VisualEDU = pending verification.)

---

## 7. Open questions for further survey passes

- [ ] What is RISE-Video's exact LMM-judge prompt for Reasoning Alignment? (Download repo and read `reasoning_eval/`.) → confirmed transferable structure: (1) restate rule, (2) cite frames, (3) binary verdict + 1–5 + reasoning.
- [ ] License confirmation for RISE-Video repo + dataset (open GitHub issue).
- [ ] Whether PhyEduVideo + VideoScience-Bench overlap on individual physics concepts (so we know what fraction of physics topics is already saturated).
- [ ] Audio-track support coverage across Sora 2 / Veo 3.1 / Hailuo 2.3 — which models actually produce synchronized audio? VABench already covers Veo 3 / Sora 2 / Wan 2.5.
- [ ] Inter-rater reliability protocols used in PhyEduVideo's 500-video human study — sample sizes and Cohen's kappa.
- [x] ~~Verify or replace VisualEDU citation~~ — **verified 2026-05-12**: real paper (EMNLP 2025 Findings) by Hao Chen et al., Manim-based, 9 VLMs, < 56 % SOTA on hard problems.
- [ ] **Verify or drop "CogVideoX-Eval" reference** — flagged as unverifiable; likely no standalone eval suite exists.
- [ ] **Read TeachQuiz implementation in Code2Video** — for pixel-T2V port we need the VLM "unlearning" protocol details.
- [ ] **Read VABench source** — adapt protocols for instructional narration vs. their generic audio-quality framing.
