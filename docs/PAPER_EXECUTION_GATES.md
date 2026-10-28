# 投稿执行门槛（2026-10-26）

本页把 `plan.md` 的研究方向改写为可验收工作。`STATUS.md` 记录已有实验；此处的脚本完成不代表实验或专家审查完成。主论文建议聚焦 **3–5 秒教学片段的可定位知识错误与测量效度**。长视频修复作为独立后续实验，避免把 50–97 秒 Code2Video 样例与短片模型直接比较。

## 实验入口现状

`python -m scripts.pipeline_preflight` 在生成前检查 60 题、首帧、共用测验、模型目录、Python 依赖、CUDA 与 Azure CLI/端点。`bash scripts/run_full_pipeline.sh --check` 用相同门槛；正式运行会在单独的时间戳目录生成同模型同题的 T2V/TI2V、3 秒/5 秒四臂，并在每阶段检查逐题完整性。评测使用六维评分与同一份生成前冻结的测验，最后计算配对差异。脚本已修复旧版缺少 `--student-model-path`、固定服务器路径和跳过失败仍打印完成的问题。

2026-10-28 链路复核：预检也校验共用测验的非空题目、题号、选项和答案；阶段验收拒绝意外题号及非有限分数。TeachQuiz 失败题可在恢复运行时重试，随机对照按题号固定选择；配对分析现在读取完整的 TeachQuiz 运行目录。以上是工程修复，不代表真实实验已运行。

**当前机器预检不通过，完整实验尚未执行。** 共用 quiz 仅 10/60 题；本机缺 Wan/Qwen 权重、`diffusers`/`transformers`、可用 CUDA 与 Azure 评分凭据。先由专家制作并冻结剩余 50 题测验，再在模型服务器配置环境并预检通过，才能运行这一昂贵实验。预检不会把输出后生成的视觉题冒充共用测验。离线 `python -m scripts.build_v1` 仍可运行，复用的是既有实验记录。

## 题库先于扩量

| 门槛 | 现状 | 通过条件 |
| --- | --- | --- |
| 候选多样性 | 400 候选混合 14 个原始学科标签，任务/难度不均衡 | 冻结标签映射；对学科 × 任务 × 认知技能列出目标格子和缺口；以缺口补题，不按总数凑数 |
| 逐题质量 | 候选中的 `reviewed_release_ready` 仅 4 行，原 pilot 也未按新门槛复审 | 两名独立专家检查来源、答案、原子片段、可观察终态、评分规则和授权；第三人裁决。`scripts/curate_paper_items.py` 只导出满足完整记录且输入哈希未变的题 |
| 难度效度 | `low/medium/high` 与 `k12/undergrad` 混用 | 统一为经人工标定的三级难度，并另记认知技能、试答正确率和先修知识；报告评分者一致性 |
| 短片可执行性 | 140 题标记需人工收窄 | 每题仅一个可观察状态变化；完整原题和答案留作溯源；超时任务转长视频轨道 |
| 发布权利 | GRADE 图片权利未核实 | 逐资产来源、许可、哈希和可再分发范围核验后再打包 |

运行 `python scripts/curate_paper_items.py` 可生成 `results/paper_item_curation/{report.json,review_queue.jsonl,accepted.jsonl}`。当前没有满足新协议的双人审核记录，因此 `accepted.jsonl` 为空；原有四题状态不能替代新门槛。`data/curated/paper_item_reviews.jsonl` 的每条记录需含 `case_id`, `role`, `reviewer_id`, `item_sha256`。两名 `reviewer` 各自填写六个布尔门槛、`difficulty` 和 `cognitive_skill`；独立 `adjudicator` 填 `decision`, `source_url`, `license`, `reference_answer`, `atomic_target`, `expected_final_state`, `failure_criteria`, `difficulty_rationale`, 最终难度与技能，分歧时填写 `disagreement_resolution`。难度值为 `introductory/intermediate/advanced`；技能值为 `recall/application/multi_step_reasoning/transfer`。审核输入变动会使旧记录失效。

按计划中 12 学科 × 2 任务、每格至少 5 题计算，**候选数量**只有 `medicine/problem_solving` 差 1 题；但这不是质量覆盖。另有 `music` 21 题和 `sports` 30 题在该 12 学科口径之外，须先决定分类，不应暗中混进原格子。对已审题执行同一矩阵后目前全部 24 格都未达标。下一轮补题先补医学解题，再依据实际审核淘汰后的缺口补足，并检查四类认知技能是否均衡。

## 视频与排版

1. **规划与知识状态。** 先定义参考答案、前后状态及不变量，再写镜头和视觉锚点。代码式片段用现有教学契约编译，像素视频将契约作为提示与事后核查依据。这样落实了 Code2Video 的分镜/视觉锚点和 ALGOGEN 的状态/渲染分离，但这两项论文结果不能直接推断本项目收益。[Code2Video, ICML 2026](https://proceedings.mlr.press/v306/chen26bx.html)；[ALGOGEN, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.156/)。
2. **渲染前门槛。** `generation/teaching_contract.py` 已检查安全边距、文本尺寸、文本框和同阶段重叠；现增加文字与背景至少 4.5:1 对比度。此阈值为工程筛查规则，需在实际播放尺寸人工复核。
3. **渲染后反馈。** `scripts/audit_generated_videos.py` 保存原分辨率固定时间点证据帧，并新增画面变化大的自适应关键帧，以减少固定抽帧漏掉过渡遮挡。再由审查者逐帧标注重叠、遮挡、字号、文本/图形冲突、对象漂移与科学错误；修复出错镜头后重跑审查。VisualEDU 把视觉与代码反馈、时间一致性和清晰度纳入系统评估。[VisualEDU, Findings EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.889/)。
   本地八条长视频重跑后，每条共得到 9–10 个审查帧（原来固定 6 个），`math_prob_02` 新增 20.27、40.00、49.60、66.67 秒等变化点；接触表见 `results/video_audit_adaptive/contact_sheets/`。这些时间点仅是人工复核入口，不是自动判错或质量提升分数。
4. **效果验证。** 对受控子集保留修复前后同分辨率截图、缺陷标注和人工盲评；统计减少的缺陷与新增错误。仅通过自动几何/对比度检查不能宣称视频更会教学。

## 仍需完成的真实实验

| 优先级 | 工作 | 交付证据 |
| --- | --- | --- |
| P0 | 冻结审定题、原子目标和诊断错误标签 | 逐题审核记录、双人一致性、排除日志、来源权利 |
| P0 | 60 视频 × 3 人评分及缺陷子集双标 | 匿名原始数据、不可判定率、alpha、与自动评分的相关区间 |
| P0 | 生成前冻结共用感知/理解/迁移题包 | 同一题包供所有模型，哈希、泄漏检查、随机视频对照 |
| P1 | 独立非 Wan 模型、配对 TI2V/T2V、第二代理学生 | 相同题目交集、配置与种子、成片哈希、配对区间 |
| P1 | 多种子与高难压力集 | 生成方差、同题对照、全部失败与重试 |
| P1 | 发表包 | 可重建表格、模型修订、许可、数据卡、附录与排除清单 |

排版优化与题库规模增加均不能代替这些证据门槛。当前工作是把工程接口补齐，尚未完成投稿研究。
