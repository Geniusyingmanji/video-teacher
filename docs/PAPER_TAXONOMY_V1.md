# 投稿题库分类标准 v1（待专家标定）

本标准用于 **3–5 秒教学片段**的题库审核和分层报告。400 题是候选池，不代表已审定基准。旧题的 `discipline`、`task_type`、`difficulty` 保留原值；正式集合另存审核后的字段，不回写历史 pilot。

## 正交分类轴

| 轴 | 审核值与判定规则 |
| --- | --- |
| 标准学科 | `music` 统一报告为 `art_music`，原始标签仍保留；`sports` 单列候选轨道，尚不计入 12 学科主榜。跨学科题按目标知识判定主学科，并记录次学科。 |
| 教学任务 `teaching_task` | `concept_mechanism`：解释一个概念或机制；`worked_step`：给定问题，演示一个可核验的求解步骤；`evidence_interpretation`：根据图、表、文本等证据作判断；`procedure_strategy`：演示一项操作或策略。只能按片段实际教学目标标注，不能从学科或旧二分标签推断。 |
| 认知技能 `cognitive_skill` | `recall`、`application`、`multi_step_reasoning`、`transfer`。按学习者完成目标所需操作标注；多步推理题仍须收窄成一个可见片段。 |
| 难度与受众 | `target_audience` 写明目标学习者及先修知识；`difficulty` 用 `introductory`、`intermediate`、`advanced`，依据推理负担与试答证据裁定。旧 `undergrad/k12` 仅是受众线索。 |
| 可观察证据 | `atomic_target`、`expected_final_state`、`observable_evidence`、`failure_criteria` 分开填写。证据须能在成片中定位到帧或时间戳；音频必需、片长不足或需多镜头者转其他轨道。 |

旧 `explanation/problem_solving` 只供历史对照，不再作为唯一任务分类。尤其体育策略演示、谱面标注、历史证据解读不能因为有“答案”就自动归为 `problem_solving`。判不清任务或缺可观察证据时，保留在审核队列，不硬填主榜格子。

## 审核与报告

两名独立审核者分别标难度、认知技能、教学任务和六个质量门槛；独立裁决者记录最终标签、受众、可观察证据、参考答案、终态、失败条件、来源与许可。分歧必须记录理由。`scripts/curate_paper_items.py` 只导出完整且与当前题目哈希匹配的题；`normalized_disciplines` 统计只做标签归并，不代表内容审核通过。

主结果按教学任务与可观察错误类型报告，学科、受众和难度作为分层变量；同时公布各格分母、排除原因、无法判定率及标注一致性。旧 12 学科 × 2 任务 × 每格 5 题只作历史候选数量对照，不作为所有正式格子必须填满的论证。缺陷标签应另含 `beat_id`、错误类型、严重度、证据时间戳及 `assessable`；六维视频评分和 TeachQuiz-T 分别报告。

## 现状与依据

当前候选池有 400 题、14 个原始学科标签；`music` 21 题、`art_music` 13 题、`sports` 25 题。旧任务标签为讲解 155、解题 245，体育 25 题均标为解题。290 题 `undergrad` 与 6 题 `k12` 尚不能用于难度比较。审核协议下尚无正式接纳题。数字以 `data/curated/candidate_400_report.json` 和运行时审核报告为准。

相关工作中，[EduVideoBench](https://arxiv.org/abs/2605.26918) 已覆盖跨学科教学知识、技能与态度，[Sci-VBench](https://arxiv.org/abs/2608.09873) 已测试科学知识与推理视频。因此论文应检验可定位的教学错误及证据是否比已有评分提供增量信息，不以学科数或维度名称宣称首创。参见 [相关工作综合建议](项目研究方向_相关工作综合建议.md) 与 [六维评测卡](RISE_TEACHER_SIX_DIMENSIONS.md)。
