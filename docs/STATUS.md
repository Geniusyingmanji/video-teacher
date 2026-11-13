# 当前状态快照

日期：2026-11-12，R106 结束后。方法迭代和模型调用暂停。未来恢复执行时，应先更新本页日期和运行指针。

## Benchmark

- 候选池 400 题，统一覆盖 13 个学科；体育与棋类 25 题按普通学科参与。讲解 155、解题 245。
- 最近本地清单：开发 124、预留候选 276；专家批准记录 0，未认证为正式留出集。[原始清单](../results/localbench/continuous_method_20261112/round102_repeated_connections/reserve_inventory_after_trials/summary.json)
- General 已实现十维、六十项整数 rubric；视频和教学各 50%。Specific 与学生诊断单列。
- 前缀提问、回答轨迹及固定知识点学生试验已实现，但与默认 CLI 并非一个完全统一的协议。
- 400 题正式实验、人工校准、可靠的 judge／学生检错能力尚未完成。

## 方法与最近结果

| 运行 | 结果 | 证据 |
| --- | --- | --- |
| R100 四题开发对比 | 已完成；没有稳定整体教学收益证据 | [冻结协议](../results/localbench/continuous_method_20261112/round100_four_case_transfer/PROTOCOL.md) |
| R102 生物对象连接 | 50 秒视频，7/7 处跨场景连接修复并核验；Specific 87.5→100，候选学生 1/2 完成，仍有读图漏检 | [完整报告](../results/localbench/continuous_method_20261112/round102_repeated_connections/REPORT.md) |
| R103 透视题完整 CLI | 85 秒视频已生成；尺寸阶段未成功应用，普通修复删去一条道路边线；正式 General 总分 null，专项四问 100 | [CLI 报告](../results/localbench/continuous_method_20261112/round103_perspective_full_cli/method/REPORT.md) |
| R104 尺寸原型 | 树木只修好一侧；另一条同题横截线视频无改动 | [运行目录](../results/localbench/continuous_method_20261112/round104_size_projection/) |
| R105 尺寸原型 | 树木候选失败，保留原片；横截线无改动 | [失败记录](../results/localbench/continuous_method_20261112/round105_grounded_size_order/cases/trees/size/result.json) |
| R106 尺寸原型 | 树木绑定被判为同一不可区分深度，保留原片；横截线无改动 | [失败记录](../results/localbench/continuous_method_20261112/round106_depth_layer_sizes/cases/trees/size/result.json) |

R103 的记录中视频质量约 97.92、教学质量约 65.48，因转写证据争议未解决而没有正式总分。专项满分不等于完整视频满分。R104–R106 使用同一已知透视开发题的既有成片，不是多个未见任务的迁移验证。


## 后续待办（尚未执行）

1. Benchmark：补题目裁定、冻结问题包与人工／缺陷控制校准。
2. 方法：收敛到教学关系约束和成片反馈，完成有明确对照的小规模配对实验。
3. 工程：统一研究协议与 CLI，补全小模型学生画像和问题包覆盖。

本页是当前进度入口；各轮结果不作为最新累计统计。所有 API 用量以运行账本为准，本页没有重新汇总费用。

仓库保留最近 R100–R106 开发批次的原始成功、失败和评分；更早试跑、重复实现及旧文档已清理。部分旧运行引用的上游文件已删除，这些记录用于结果核查，不保证旧运行可完整重放。当前 124 道开发成员另存于 [development_membership.json](../data/development_membership.json)。
