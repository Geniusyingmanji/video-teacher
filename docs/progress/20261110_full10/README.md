# 四卡十题运行进度（2026-11-10）

最新 completion.json 与十份 final 案例记录确认本轮十题全部结束：生成带旁白视频 3/10，质量验收通过 0/10。旧 progress.json 仍显示 9/10，已落后于最终记录。本报告以完成记录为准，不把执行结束当作质量通过。

配置：本地 Qwen3.8-27B，GPU 0–3，每卡两个案例 worker；冻结十题，strict 模式，quality-v12，启用质量修复及 visual critic，最多三次尝试。生成与评审使用同一本地模型，分数仍需外部人工校准。

| 案例 | 视频生成 | 质量验收 | 失败原因 |
|---|---|---|---|
| cs_prob_02 | 失败 | 未通过 | ValueError: chapter chapter_1 speech too_long: 18.89s for 18.733333333333334s |
| grade_ComputerScience_task_17 | 失败 | 未通过 | ValueError: chapter chapter_1 speech too_long: 21.94s for 20.0s |
| lang_high_01 | 失败 | 未通过 | ValueError: chapter chapter_3 speech too_long: 21.38s for 19.0s |
| math_exp_02 | 失败 | 未通过 | ValueError: Storyboard validation exhausted: timeline omits current task requirements: expected_visual_elements:3 |
| math_high_02 | 失败 | 未通过 | ValueError: chapter chapter_3 speech too_long: 20.04s for 17.53333333333333s |
| math_prob_01 | 成功 | 未通过 | 生成成功，但质量未通过 |
| math_prob_02 | 失败 | 未通过 | Rejected render: layout |
| med_exp_01 | 失败 | 未通过 | Video generation returned no complete video; inspect preserved section render logs. Last render diagnostic: ValueError: lesson authored duration 69.267s differs from 75s; refusing to stretch or truncate |
| phys_exp_02 | 成功 | 未通过 | 生成成功，但质量未通过 |
| phys_exp_03 | 成功 | 未通过 | 生成成功，但质量未通过 |

已完成的阻塞修复提交：`6ced48b`（旁白重试、分镜审核历史错误、反馈上下文预算与长请求超时），`0f027e8`（不支持的 Text font_weight 预检）。此前验证记录为 43 项回归测试及 4 项代码生成测试通过；本次仅归档进度，没有重新运行测试。

修复后的补跑尚未启动，原始轮次及失败产物保留。完整本地产物位于 `results/qwen38_four_gpu_full10_20261110T082127Z/`；本目录 snapshot.json 保存完成状态及逐题结果，不包含大体积视频。

本次同步检查发现 GitHub 域名解析失败（Could not resolve host: github.com）；远端推送是否成功以实际 git push 结果为准，本地提交不代表远端已更新。
