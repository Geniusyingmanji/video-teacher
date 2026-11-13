# Benchmark

400 道候选题、13 个学科，讲解 155 题、解题 245 题，目标为约 50–105 秒完整英文旁白教学视频。体育与棋类 25 题使用相同选题与评分规则。学科数量见[项目首页](../README.md)。

- [source_tasks.jsonl](../data/source_tasks.jsonl)：带来源的原始题目，供规范化构建。
- [tasks.jsonl](../data/tasks.jsonl)：当前统一候选池；[摘要](../data/tasks.summary.json)记录结构与审核状态。
- [data_fixes.json](../configs/data_fixes.json)：显式编辑规则；`python -m localbench.prepare` 重建候选池。
- [sources/](../data/sources/)：来源元数据、许可信息与题目素材。
- [development_membership.json](../data/development_membership.json)：已知 124 道开发成员，包含关联题；清理旧结果后继续排除在预留候选之外。

剩余 276 道是预留候选，不能称作认证未见测试集。专家批准记录为 0；296 题仍需独立难度标注。来源审核、人工裁定和全库实验尚待完成。

生成器仅接收公开题目、受众、时长和允许原图；私有答案与评分参考只进入评测。[common.py](../localbench/common.py)维护公开输入白名单。[split.py](../localbench/split.py)结合当前结果、保留成员及同源／相似题分组生成开发与预留清单。

评估包含 General 通用评分、Specific 逐题问题评分、模拟学生诊断。细则见[评测说明](evaluation.md)和[学生说明](student.md)。失败任务计入实验分母，同时报告交付率、评分覆盖率与有效分数。
