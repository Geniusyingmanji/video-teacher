# 固定十题四卡续跑最终报告（2026-11-02）

十题全部执行结束，四个 worker 正常退出。最终生成验收通过 **7/10**，生成验收失败
**3/10**，严格质量门槛通过 **0/10**。本轮没有达到“十题全部成功”；
`execution_finished=true` 仅表示任务执行完毕，`complete=false` 表示质量目标未实现。

## 范围与执行

- 固定题库 `candidate_400.jsonl`，seed `20261102`，保留原始十题及原质量标准。
- 生成与评分基线提交 `fe8a69b`；contract `strict-five-seconds-v3`，评分 `video-teacher-2x8-v4`。
- 保留此前已经结束的五题；继续化学题最后一次尝试，再运行剩余四题。
- GPU 0–3 各运行一个 Qwen3.8-27B vision 实例，端口 8000–8003。GPU 0 先化学、后医学，
  其他三卡分别运行算法、棋盘游戏、公民教育。尾部只有 GPU 0 工作。
- 每题最多三次外层尝试，共保留 **30 份完成尝试的结果/评分**。内部修复还会调用模型；
  不能把外层次数当成模型调用总数。中断时未完成的尝试日志另存于原目录。
- 同一模型生成并自评，没有独立人工验收或外部模型复核。

## 最终逐题结果

| 题目 ID | 生成验收 | 有效评分 /100 | 主要未通过项 |
| --- | --- | ---: | --- |
| grade_his_task_16 | 通过 | 60 | v4 静止门槛 |
| cand_med_cs_gap_05 | 通过 | 60 | v4 静止门槛 |
| grade_ComputerScience_task_17 | 通过 | 50 | 任务覆盖、正确性、可读性、v4 |
| grade_math_math_90 | 失败 | — | storyboard 原图修改区域校验失败 |
| grade_math_static_9 | 失败 | — | 编码前原图授权区域外像素改变 |
| disciplinegen_chemistry_32e43cbfb37a3402 | 通过 | 50 | 任务覆盖、正确性、可读性、v4 |
| cs_prob_02 | 通过 | 50 | 可读性、符号稳定性、v4 |
| grade_board_games_task_13 | 失败 | — | 原图保护失败；内部修复发生上下文超限 |
| cand_hs_civ_05 | 通过 | 60 | v4 静止门槛 |
| med_exp_01 | 通过 | 50 | 任务覆盖、正确性、可读性、v4 |

这里的“生成验收”包含结构、时长和必要的原图保护条件，不能等同于内容正确。
7 份通过生成验收的视频均再次实际解码验证为 **75 帧、15 fps、5.0 秒**，
视频 SHA-256 与对应评分记录匹配。失败题没有伪造为零分或从十题分母中剔除。

## 评分与解释限制

- 八轴评分有效 **7/10**；教学吸引力附加评分有效 **7/10**。
- 有效七题诊断均分 **54.2857**，只用于排查，不是全十题分数。
- `ranking_publishable=false`、`ranking_score=null`，不能发布完整基准排名。
- 教学吸引力可用结果诊断均值 **84.5286**，不参与总分或抵消正确性缺陷。
- 所有七题均触发 `requested_multistep_action_frozen`。其中三题最终仅此一项阻止质量通过；
  需要核查全画面差异阈值对局部高亮、答案揭示及最终停留的影响。报告保留原判定，未改阈值重算。
- 自评不同维度存在相互矛盾的描述，例如 Markov 图某些维度声称写入 0.4，其他维度判为
  错位写入 0.8；化学题对分子身份的猜测也不一致。此类模型描述不能作为人工确认事实。

## 证据与复核

提交的小型证据在 [`results/reports/sample10_four_gpu_20261102/`](../results/reports/sample10_four_gpu_20261102/)：

- `completion.json`：执行完成与质量完成分开记录。
- `cases.json`：十题最终 gate、时长、视频哈希。
- `attempts.json`：三十次结果与评分文件哈希，以及失败诊断摘要。
- `per_case.jsonl`：完整最终自评分、准则、证据帧索引和评语。
- `aggregate.json`：保留十题分母的聚合结果。
- `provenance.json`、`prompts.jsonl`：原批次配置、续跑配置与固定题目。

原始视频、日志、反馈图片、进程号以及完整中间诊断留在本地：
`results/qwen38_gpu0_sample10_strict5s_v3_20261102/`、`results/resume_four_gpu_20261102/`。
因此 GitHub 提供可检查的评分证据与哈希，不包含完整视频重放包。

可在保留本地产物的环境复核：

```bash
/root/code2video-env/bin/python scripts/report_sample10_resume.py \
  --source results/qwen38_gpu0_sample10_strict5s_v3_20261102 \
  --run results/resume_four_gpu_20261102 \
  --out results/reports/sample10_four_gpu_20261102
```

复核实际通过：十个唯一 ID、三十次完成尝试、七份视频时长与哈希、全部 gate 重算、
聚合一致性。该复核不调用模型。400 题结构预检和此前 44 项回归是历史修复证据，
本次仅实跑这十题，没有开展 400 题全量视频实验。
