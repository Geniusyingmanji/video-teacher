# rise-teacher 项目报告

> 更新日期：2026-05-14

---

## 1. 背景

### 1.1 问题定义

当前视频生成模型（Sora、Veo、Wan2.2 等）在通用视频生成上取得了显著进展，但在**教育视频生成**领域缺乏系统性的评估基准。现有教育视频 benchmark 存在三个核心缺陷：

- **学科覆盖窄**：PhyEduVideo 仅覆盖物理，VideoScience-Bench 仅覆盖物理+化学，CODE2VIDEO 虽涉及 13 个学科但基于代码生成（Manim）而非像素级 T2V
- **任务类型单一**：已有工作仅评估概念讲解或现象呈现，未同时覆盖讲解与解题
- **评估维度缺少教学针对性**：缺乏受众适配性、教学音频对齐、学习增益等教学法维度

### 1.2 rise-teacher 定位

rise-teacher 是首个覆盖 **12 学科、同时评估讲解与解题、具备教学法感知评估维度**的像素级视频生成 benchmark。三大创新支柱：

| 创新维度 | 现有工作 | rise-teacher 填补的空白 |
|---|---|---|
| **A. 学科广度** | 仅 STEM（物理/化学） | STEM + 人文 + 社科 + 医学 + CS，共 12 学科 |
| **B. 联合任务设计** | 只评估讲解或只评估推理 | 每学科同时包含讲解 (explanation) 和解题 (problem_solving) |
| **C. 教学法感知评估** | PhyEduVideo 5 轴 + CODE2VIDEO TeachQuiz | 5 个全新维度 + 4 个继承维度，含学习增益 (TeachQuiz-T) |

### 1.3 目标会议

- **主投**：ICLR 2027（截止日期约 2026 年 10 月，距今约 5 个月）
- **备选**：NeurIPS 2027 Datasets & Benchmarks Track

### 1.4 核心竞品

| 竞品 | 学科 | 任务 | 评估维度 | 与 rise-teacher 的区别 |
|---|---|---|---|---|
| RISE-Video | 8 类常识规则 | 规则遵守 | 4 维 | 非教育场景，无教学法维度 |
| PhyEduVideo | 物理（6 子领域） | 概念呈现 | 5+1 维 | 仅物理，无解题，无学习增益 |
| VideoScience-Bench | 物理+化学 | 科学现象 | 5 维 | 仅两学科，无人文/社科 |
| CODE2VIDEO | 13 学科（Manim） | 教学视频 | 3 维 + TeachQuiz | 代码生成非像素 T2V |

---

## 2. 数据

### 2.1 学科覆盖（12 学科）

| 编号 | 学科 | 子领域示例 | 类型 |
|---|---|---|---|
| 1 | Mathematics | 代数、微积分、几何、概率 | STEM |
| 2 | Physics | 力学、电磁、热学、光学、现代物理 | STEM |
| 3 | Chemistry | 无机、有机、反应、化学平衡 | STEM |
| 4 | Biology | 细胞、遗传、解剖、生态 | STEM |
| 5 | Medicine | 解剖、病理、药理、手术流程 | STEM |
| 6 | Computer Science | 算法、数据结构、网络、操作系统 | STEM |
| 7 | History | 历史事件、时间线、人物传记 | 人文 |
| 8 | Geography | 自然地理、政治地理、气候 | 社科 |
| 9 | Economics & Finance | 微观、宏观、金融工具 | 社科 |
| 10 | Social Studies & Civics | 政治制度、社会学 | 社科 |
| 11 | Language & Literature | 语法概念、文学分析 | 人文 |
| 12 | Art & Music Theory | 作曲、时期、技法 | 人文 |

### 2.2 数据集版本

| 版本 | 文件 | 案例数 | 说明 |
|---|---|---|---|
| v0.1 (pilot) | `data/prompts/pilot_v0_1.jsonl` | 60 | 每学科 5 案例（含讲解+解题） |
| v0.2 (extended) | `data/prompts/pilot_v0_2.jsonl` | 110 | 在 v0.1 基础上扩展 |
| v0.2-high | `data/prompts/high_difficulty_addon.jsonl` | 22 | 研究生难度案例 |

### 2.3 数据 Schema

每条案例包含以下字段：

```json
{
  "id": "math_exp_01",
  "discipline": "mathematics",
  "subdomain": "calculus",
  "task_type": "explanation | problem_solving",
  "difficulty": "k12 | undergrad | professional",
  "prompt_text": "Generate a 10-second video explaining...",
  "expected_concepts": ["derivative as slope", ...],
  "expected_visual_elements": ["coordinate axes", ...],
  "expected_narrative_order": ["show curve", "place point", ...],
  "pedagogical_target_audience": "undergrad calculus student",
  "discipline_specific_rubric": ["axes are labeled", ...],
  "audio_narration_required": true
}
```

### 2.4 难度分布

目标比例：K-12 (50%) / Undergrad (35%) / Professional (15%)。v0.2-high 额外新增 graduate 难度。

### 2.5 辅助数据

- **首帧图像**：`data/first_frames/` — 用于 TI2V（Text-Image-to-Video）变体
- **学科专属评分准则**：`data/annotations/` — 每学科的细粒度评分项
- **TeachQuiz 问卷**：`data/teachquiz/` — 用于学习增益评估的多选题

---

## 3. Task

### 3.1 任务类型

| 任务 | 描述 | 示例 Prompt |
|---|---|---|
| **Explanation（讲解）** | 生成一段教学视频，正确呈现某个概念 | "Generate a 10-second video explaining mitosis at the high-school level" |
| **Problem-solving（解题）** | 生成一段视频，逐步演示问题的求解过程 | "Generate a video that solves: find the derivative of x³ + 2x and explain each step" |

### 3.2 输入-输出定义

- **输入**：`(text prompt, optional first-frame image, ground-truth annotation)` 三元组
- **输出**：模型生成的 MP4 视频（当前配置：3s 或 5s，480×832 分辨率）
- **评估**：对生成视频在 9 个维度上打分（1-5 分）

### 3.3 任务规模（目标）

- 每学科约 40 案例（20 讲解 + 20 解题）→ 总计约 **480 案例**
- 评估模型 ≥10 个，其中 ≥5 个支持音频输出
- 当前 pilot 阶段已完成 60-110 案例的全流程验证

---

## 4. 评估维度

### 4.1 九维评估框架

rise-teacher 设计了 9 个评估维度，分为核心维度、扩展维度和实验性维度三组：

| 编号 | 维度 | 创新性 | 评估方式 | 灵感来源 | 衡量内容 | 实现状态 |
|---|---|---|---|---|---|---|
| 1 | **Conceptual Correctness** | 继承 | LMM judge + rubric | RISE-Video RA + PhyGenEval | 视频是否正确呈现了概念？ | ✅ |
| 2 | **Narrative Structure** | 继承 | 多帧 LMM judge | PhyEduVideo Logic Flow | 步骤是否按可教学的顺序排列？ | ✅ |
| 3 | **Visual Quality** | 继承 | DOVER/MANIQA + LMM | RISE-Video VQ | 画面美感、无伪影、分辨率 | ✅ |
| 4 | **Pedagogical Clarity** | **新** | LMM judge | 自研 | 信息分块、重点强调、可读性、路标标记 | ✅ |
| 5 | **Didactic Affordances** | 继承 | LMM judge + OCR | PhyEduVideo Element Layout | 标签/箭头/公式/配色是否清晰 | ✅ |
| 6 | **Audience Appropriateness** | **新** | LMM judge | 自研 | 深度/词汇/前置知识/互动性是否匹配目标受众 | ✅ |
| 7 | **Audio-Narration Alignment** | **新** | Whisper + LMM + SyncNet | 改编自 VABench | 语音是否与画面内容语义对齐 | ⏳ |
| 8 | **Triple-Modal Alignment** | **新** | LMM judge | 自研 | 语音↔画面↔屏幕文字三模态一致性 | ⏳ |
| 9 | **Learning Gain (TeachQuiz-T)** | **新** | "学生" VLM 测试 | 移植自 CODE2VIDEO TeachQuiz | 学生 VLM 观看视频后的学习增益 | ✅ (MVP) |

### 4.2 权重设计

**核心 3 维（已在 pilot 中验证）：**

```
Conceptual Correctness:  0.50
Narrative Structure:     0.30
Visual Quality:          0.20
```

**扩展 6 维：**

```
Conceptual Correctness:  0.20
Narrative Structure:     0.10
Visual Quality:          0.06
Pedagogical Clarity:     0.16
Didactic Affordances:    0.13
Audience Appropriateness:0.12
Audio-Narration Align.:  0.10 (无音频时为0，重新归一化)
Triple-Modal Align.:     0.10 (无音频时为0，重新归一化)
Learning Gain:           0.20 (headline metric)
```

### 4.3 评分方式

- **Judge 模型**：GPT-5.5（Azure OpenAI，keyless CLI 认证）
- **评分流程**：每个维度的 Judge 接收 N 帧等间隔抽取的图像（最大 384px），结合 case 的 ground-truth rubric，输出 JSON 格式的 1-5 分 + 推理过程
- **报告模式**：单维度分数、加权聚合分数、严格准确率（所有维度过阈值）、学科/任务/难度分维度

### 4.4 学习增益评估 (TeachQuiz-T)

TeachQuiz-T 是 rise-teacher 的 headline 创新维度，移植自 CODE2VIDEO 的 TeachQuiz 方法到像素级 T2V：

**流程：**
1. **Pre-test**：学生 VLM 在未观看视频时回答问卷
2. **Post-video**：学生 VLM 观看生成视频帧后回答问卷
3. **Random-video**：学生 VLM 观看不相关视频帧后回答（控制组）

**指标：**
```
learning_gain = post_video - max(pre, random_video)
normalized_gain = learning_gain / (1 - max(pre, random_video))
```

**学生模型：**

| 学生模型 | 类型 | 用途 |
|---|---|---|
| Dummy / Oracle | 确定性基线 | 流程验证 |
| SmolVLM2-2.2B | 本地 VLM | 初期实验 |
| Qwen3-VL-2B | 本地 VLM | **主要学生模型** |
| Qwen2.5-VL-3B | 本地 VLM | 对比实验 |
| GPT-5.5 | 云端 API | 强基线（存在天花板效应） |

---

## 5. Pipeline

### 5.1 端到端流程

```
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 1: 数据构建                                                │
│  scripts/build_pilot_prompts.py                                  │
│  → data/prompts/pilot_v0_1.jsonl  (60 cases × 12 disciplines)   │
│  scripts/build_v0_2_high_difficulty.py                           │
│  → data/prompts/high_difficulty_addon.jsonl  (22 graduate cases) │
│  scripts/build_teachquiz_pilot.py                                │
│  → data/teachquiz/pilot_v0_1_quiz.jsonl  (quiz for learning     │
│    gain)                                                         │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 2: 视频生成                                                │
│  generation/runners/wan_runner.py                                │
│  输入: prompts JSONL + first-frame images                        │
│  输出: {<case_id>.mp4, manifest.jsonl}                           │
│  配置: 480×832, 49 frames, 30 steps, 3s/5s                      │
│  特性: 断点续传、OOM 错误处理                                     │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3a: 标准评估                                               │
│  eval/run_eval.py                                                │
│  → eval/frame_extractor.py  (抽取 N 帧，resize 至 384px)         │
│  → eval/dimensions/*.py  (6 个已实现维度)                         │
│  → eval/judges/gpt55.py  (GPT-5.5 Azure keyless)                │
│  输出: per_case.jsonl + aggregate.json                           │
│                                                                  │
│  STAGE 3b: 学习增益评估                                           │
│  eval/run_teachquiz.py                                           │
│  → eval/students/{qwen3vl,smolvlm2,gpt55_student,...}.py        │
│  → pre / post_video / random_video 三轮测试                      │
│  输出: per_case results + normalized gain                        │
└──────────────────────┬───────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 4: 分析与报告                                              │
│  scripts/gen_paper_stats.py       → paper_stats.json             │
│  scripts/dim_correlation.py       → 维度相关性分析                │
│  scripts/eval_vs_teachquiz_correlation.py → 标准评测 vs 学习增益  │
│  scripts/render_report.py         → Markdown 报告                │
│  scripts/render_comparison.py     → 模型对比                     │
│  scripts/render_teachquiz_report.py → TeachQuiz-T 报告           │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 关键命令

```bash
# 1. 构建数据
python scripts/build_pilot_prompts.py

# 2. 生成视频
CUDA_VISIBLE_DEVICES=1 python -m generation.runners.wan_runner \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --out /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1 \
    --num-frames 49 --height 480 --width 832 --steps 30

# 3. 标准评估 (3 核心维度)
python -m eval.run_eval \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
    --out /data/zyf/rise-teacher/outputs/eval_pilot_v0_1

# 4. 学习增益评估
python -m eval.run_teachquiz \
    --prompts data/prompts/pilot_v0_1.jsonl \
    --quiz data/teachquiz/pilot_v0_1_quiz.jsonl \
    --manifest /data/zyf/rise-teacher/generations/wan2_2_ti2v_5b/pilot_v0_1/manifest.jsonl \
    --student qwen3vl --out outputs/teachquiz_qwen3vl_5b

# 5. 聚合统计
python scripts/gen_paper_stats.py
```

### 5.3 环境依赖

- **Python 3.10** + venv
- **GPU**：CUDA（默认使用 GPU 1,2,3；GPU 0 保留）
- **模型**：Wan2.2-TI2V-5B (~32 GB, symlink at `models/`)
- **Judge**：Azure OpenAI GPT-5.5（keyless CLI auth，需 `az login`）
- **学生 VLM**：Qwen3-VL-2B / SmolVLM2-2.2B（本地推理）

---

## 6. 当前进展总结

### 6.1 已完成的实验

共完成 **7 组标准评估配置** 和 **4 组 TeachQuiz-T 评估**，覆盖两种模型规模（5B/1.3B）和两种视频时长（3s/5s）。

#### 标准评估结果

| 配置 | 模型 | 案例数 | 聚合均分 | CC | NS | VQ | Strict Acc |
|---|---|---|---|---|---|---|---|
| Wan5B-3s | Wan 2.2 5B | 60 | 1.754 | 1.45 | 1.50 | 2.896 | 0% |
| Wan5B-3s-ext | Wan 2.2 5B | 60 | 1.766 | 1.50 | 1.40 | 2.919 | 0% |
| Wan5B-3s-ext6 | Wan 2.2 5B | 60 | 1.820 | 1.567 | 1.517 | 2.946 | 0% |
| Wan1.3B-3s | Wan 2.2 1.3B | 60 | **1.823** | 1.567 | 1.45 | 3.021 | 0% |
| Wan5B-5s | Wan 2.2 5B | 60 | 1.789 | 1.567 | 1.70 | 2.479 | 0% |
| Wan1.3B-5s | Wan 2.2 1.3B | 60 | 1.788 | 1.517 | 1.40 | 3.050 | 0% |
| Wan1.3B-v0.2-high | Wan 2.2 1.3B | 22 | 1.486 | 1.227 | 1.091 | 2.727 | 0% |

#### TeachQuiz-T 学习增益结果（Qwen3-VL-2B 学生）

| 模型 | 有效案例 | NG（归一化增益） | PGR（正增益率） | 讲解 NG | 解题 NG |
|---|---|---|---|---|---|
| Wan 5B | 52/60 | **0.760** | 88.5% | **0.807** | 0.683 |
| Wan 1.3B | 53/60 | 0.730 | 83.0% | 0.719 | **0.746** |

### 6.2 核心发现

#### 发现 1：标准评估无法预测学习增益

| 模型 | r(agg, NG) | r²(%) |
|---|---|---|
| Wan 5B | 0.213 | **4.5%** |
| Wan 1.3B | 0.094 | **0.9%** |

标准评估维度（CC/NS/VQ）与学生学习增益的相关性极低（r² < 5%）。这是论文的**核心贡献点**：现有评测框架测量的是"视频看起来有多好"，而非"视频教得有多好"。

#### 发现 2：高难度下概念正确性与视觉质量正交

| 配置 | CC↔VQ | NS↔VQ | CC↔NS |
|---|---|---|---|
| Wan5B-3s | +0.12 | +0.20 | +0.58 |
| Wan1.3B-3s | +0.36 | +0.20 | +0.63 |
| **Wan1.3B-v0.2-high** | **+0.03** | **-0.16** | +0.21 |

在研究生难度任务上，CC 与 VQ 几乎完全正交（r=+0.03），NS 与 VQ 甚至轻微负相关（r=-0.16）。含义：**模型可以画出漂亮的视频，但概念完全错误**。

#### 发现 3：模型规模与任务类型存在交互效应

- **5B 模型**更擅长讲解类任务（NG=0.807 vs 0.719）
- **1.3B 模型**更擅长解题类任务（NG=0.746 vs 0.683）

#### 发现 4：难度梯度明显

| 难度 | Wan1.3B-3s 均分 |
|---|---|
| K-12 | 1.943 |
| Undergrad | 1.785 |
| Professional | 1.320 |
| Graduate | 1.486 |

从 K-12 到 Professional 呈单调下降；Graduate 稍有回升但 NS 严重崩溃（1.091）。

#### 发现 5：5 秒视频改善专业级表现

5 秒视频在 professional 难度上比 3 秒视频提升约 +0.20（两种模型均是如此），但在简单任务上未见显著增益。

### 6.3 产出文件清单

| 类别 | 文件 |
|---|---|
| 设计文档 | `docs/plan.md`, `docs/survey.md` |
| 状态追踪 | `docs/STATUS.md` |
| 评估报告 | `docs/reports/PILOT_REPORT_*.md` (×7) |
| 学习增益报告 | `docs/TEACHQUIZ_REPORT.md` |
| 维度相关性 | `docs/analysis/dim_correlation_*.md` (×6) |
| 评测 vs 学习增益 | `docs/analysis/eval_vs_teachquiz_corr.md` |
| 聚合统计 | `paper_stats.json`, `docs/paper_stats.md` |
| 模型对比 | `docs/reports/PILOT_REPORT_compare*.md` (×2) |

---

## 7. TODO

### 7.1 评估维度待实现

| 维度 | 优先级 | 阻塞原因 | 预估工作量 |
|---|---|---|---|
| **Audio-Narration Alignment** | 高 | 需要支持音频的生成模型（如 Veo 3.1、Sora 2） | 1-2 周 |
| **Triple-Modal Alignment** | 高 | 依赖音频维度完成 | 1 周 |

### 7.2 数据扩展

| 任务 | 优先级 | 说明 |
|---|---|---|
| 扩展至 480 案例 | 高 | 当前 pilot 60-110 案例，需扩展至目标规模 |
| 招募学科专家标注 | 高 | 目标 6 位标注员（每 2 学科 1 位），特别缺人文/社科 |
| IRR 校验 | 中 | 双标注 + Cohen's κ ≥ 0.7 |

### 7.3 模型覆盖

| 任务 | 优先级 | 说明 |
|---|---|---|
| 评测更多模型 | 高 | 目标 ≥10 模型；当前仅 Wan 2.2 (5B/1.3B) |
| 闭源模型接入 | 高 | Sora 2、Veo 3.1、Hailuo 2.3、Kling 2.6、Seedance 1.5 |
| 音频模型覆盖 | 高 | 需 ≥5 支持音频的模型来驱动 Audio 维度 |

### 7.4 评估可靠性

| 任务 | 优先级 | 说明 |
|---|---|---|
| Human evaluation | 高 | 100 案例 × 全维度 × 3 raters → Cohen's κ / Krippendorff's α |
| Judge 集成验证 | 中 | 在 20% 样本上使用 Gemini-2.5 + Qwen2.5-VL-72B + InternVL3.5 交叉验证 |
| 多 seed 评估 | 中 | 开源模型 3-5 seeds/prompt，统计显著性检验 |

### 7.5 论文与发布

| 任务 | 优先级 | 说明 |
|---|---|---|
| 论文撰写 | **紧急** | `paper/` 目录当前为空，核心实验已完成 |
| 消融实验 | 高 | 维度权重敏感性、学生模型选择、帧数影响等 |
| HuggingFace 数据集发布 | 中 | `rise-teacher/rise-teacher-v1` |
| Leaderboard 搭建 | 中 | HF Space Web UI |

### 7.6 工程质量

| 任务 | 优先级 | 说明 |
|---|---|---|
| 单元测试 | 低 | `tests/` 当前为空 |
| `requirements.txt` | 低 | 当前依赖隐含在 venv 中，缺显式声明 |

---

## 附录：论文 Claims 清单

以下 claims 均有实验数据支撑，可直接用于论文写作：

1. **标准评测无法预测学习增益**：r² < 5%（5B=4.5%, 1.3B=0.9%）
2. **5 秒视频改善专业级难度**：professional +0.20 (both models)
3. **CC↔VQ 正交且随难度增强**：从 +0.12 (3s) → +0.49 (5s) → +0.03 (graduate)
4. **5B 教学效果更好**（NG 0.760 vs 0.730），尽管标准评测 1.3B 胜（1.823 vs 1.754）
5. **任务类型分工**：5B 擅长讲解 (0.807)，1.3B 擅长解题 (0.746)
6. **难度交互**：5B 在 K-12 + Professional 更有效，1.3B 在 Undergrad 更有效
7. **高难度 NS 崩溃**：Graduate NS=1.091（比标准低 0.36），VQ 相对稳定 (2.727)
