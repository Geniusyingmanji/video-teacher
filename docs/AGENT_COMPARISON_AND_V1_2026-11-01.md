# 教学视频 Agent：顶会对比与本项目 v1

更新时间：2026-11-01。论文机制来自原论文或官方项目；“借鉴”是本项目设计判断，不代表原论文验证了本项目的结果。

| 工作 | 发表状态 | 主要分工与可复用机制 | 本项目借鉴 | 直接套用的缺口 |
|---|---|---|---|---|
| [Code2Video](https://proceedings.mlr.press/v306/chen26bx.html)；[代码](https://github.com/showlab/Code2Video) | ICML 2026 | Planner 分镜、Coder 生成可运行 Manim、VLM Critic 修布局 | 可执行中间表示、局部修复、代码后端基线 | 以代码渲染为主，不能代替像素 T2V/I2V 的实验 |
| [LASEV](https://arxiv.org/abs/2602.11790) | KDD 2026 Applied Data Science Track，论文自述 | Orchestrator 协调解题、插画、旁白；区分语义、规则和编译检查 | 解题事实先于画面；声音单独验收 | 教育题目为主，知识点解释仍需覆盖 |
| [TeachMaster](https://aclanthology.org/2026.acl-industry.7/) | ACL 2026 Industry Track | 教学意图驱动规划、设计、渲染，代码作为可编辑中间媒介 | 主调度器与声音/画面分工；保留可编辑产物 | 面向课程制作，短视频 benchmark 的预算与时长不同 |
| [GENMAC](https://ojs.aaai.org/index.php/AAAI/article/view/37418) | AAAI 2026 | Design–Generation–Redesign，多 agent 按失败类型改写 | 失败分类后只修受影响镜头 | 通用组合属性正确性不等于教学正确性 |
| [PIVOT](https://arxiv.org/abs/2609.24083) | 2026 预印本；不按已录用顶会计 | 教学原则、代码生成、教学验证、误解补救 | 教学评估和误解类型可进入 critic | 需独立验证最终学习效果，避免用评测题调 prompt |

## 本项目选择

`LessonDirector` 为主 agent，管理题目 ID、预算、状态和产物。下层是 `TeachingPlanner`（答案与知识点、镜头顺序）、可替换 `VideoBackend`（T2V/I2V 或代码渲染）、可替换 `AudioBackend`（旁白/TTS）、`ContractCritic`（生成前的事实材料、学科规则和素材检查）。后续加入独立的视觉、事实与音画同步 critic，失败记录定位到镜头，限额重试。后端接口定义在 [generation/lesson_agent.py](../generation/lesson_agent.py)。

选择本地薄编排层而非直接复制 Code2Video：现有 Wan runner 与 benchmark 已按 JSONL/manifest 工作，代码渲染和像素模型需要共用相同题目、时长和成本协议。Code2Video 可作为独立后端与强基线；其许可证和依赖应在实际集成时再核对。当前 v1 已能编译逐镜头计划、决定有图/无图路径、阻止缺素材执行，并通过注入后端执行；**尚未接入真实视频、TTS、合成和视频后验 critic**，不能称为端到端生成结果。

示例：

```bash
python scripts/prepare_agent_400.py
python -m generation.lesson_agent --prompts data/prompts/candidate_400_agent_ready.jsonl --id math_exp_02 --out results/agent_plan_math_exp_02.json
```

## 400 题下一轮内容工作

保持原始 `candidate_400.jsonl` 和来源清单不动。派生的 `candidate_400_agent_ready.jsonl` 为每题标注 `knowledge_point` 或 `solve_problem`，只有本地确有且可解码的输入图才标 `available_optional`；当前 **238 有图可选、162 无图**（GRADE before 图 178、已修复首帧 57、DisciplineGen 输入图 3）。图像提纲和包含答案的 gt 图均不算首帧。`candidate_400_agent_coverage.json` 提供 14 学科 × 2 视频目标的逐格计数与每格 14 题的缺口。当前艺术/音乐 13、思政 12、文学 13、体育 25 且体育知识点解释为 0，不能宣称学科或题型已均衡。

补题优先级：体育知识点解释 14；数学知识点解释 7；艺术/音乐、思政、文学各补到约 28–29 题，且两类视频都至少 14。优先从本地 GRADE 完整题图和 DisciplineGen 元数据挑候选，逐题核对题干、答案、图像前后状态、授权与 3–5 秒可表现性；不足的学科需要额外可信来源或专家编写。每个候选记录原始 ID、来源、答案依据和审核结论，然后等量替换重复/过宽/事实错误的旧题，保持总数 400。**不能简单改 `task_type` 把解题题伪装成知识点解释。**

### 2026-11-01 平衡改编草稿

执行 `python scripts/build_balanced_400_draft.py` 会生成 `data/prompts/candidate_400_balanced_draft.jsonl` 和 `data/curated/candidate_400_balanced_draft_report.json`。当前草稿为 **400 题、14 学科各 28–29 题、每学科两类各 14–15 题、211 题有可选输入图**。87 道改编题有来源锚点，另有 87 道旧候选暂时退出草稿；后续复核又将 68 道范围过宽的继承题替换为单步新题，并收窄 17 道艺术、思政、语言题。改编与新题分别见 `scripts/balanced_rewrites.py`、`scripts/scope_replacements.py`。与新题画面不匹配的旧图绑定已移除。当前所有改编/新题仍是候选，原始答案、学科事实、图片语义与来源许可仍需逐题复核；报告中的配额达标不等于发布审核通过。原 `candidate_400.jsonl` 仍保留作溯源。

实验建议：同题同预算比较单次 Wan、固定流水线、Code2Video 后端和本 agent；对状态约束、音频 agent、定点修复做消融。报告答案正确率、可见证据、音画同步、失败率、成本和独立 TeachQuiz-T；生成 agent 不得读取评测 quiz。现有 400 题仍是候选集，大部分尚需学科/图像人工复核，不能作为发布版 benchmark。
