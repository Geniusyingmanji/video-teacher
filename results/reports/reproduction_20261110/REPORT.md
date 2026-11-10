# 无需凭据的作者方法复现（2026-11-10）

已按用户要求跳过受限权重，Code2Video 的 API 模型换成本地 Qwen。以下是实际推理与编译结果，不是训练复现或论文全量基准复现。

| 方法 | 实际执行 | 编译与图像 | 内容核查 |
|---|---|---|---|
| [TikZilla-8B-RL](https://huggingface.co/nllg/TikZilla-8B-RL) | 作者公开完整权重，原模型卡提示与采样配置，同一组六道教学题 | 原始响应带空 think 标签；精确提取 LaTeX 正文后 6/6 编译成功并生成 PNG | 六张均已检查，各有未满足的题目要求；编译成功不代表教学图正确 |
| [DeTikZify v2.5 8B](https://github.com/potamides/DeTikZify) | 作者公开权重及作者代码，四张参考图转 TikZ | 4/4 编译成功并生成 PNG | 发现标签、结构与几何失真，不能作为合格重建 |
| [Code2Video](https://github.com/showlab/Code2Video) | 作者 Planner/Coder/Critic 流程，API 模型替换为 Qwen3.8-27B | 已完成 5/5 章节与最终合片；73.07 秒，完整解码通过 | 无音轨；抽帧发现小字与低对比度，未通过完整教学质量验收 |

## TikZilla 的可复查结果

- [六题实际输出总览](tikzilla/overview.png)
- [逐图内容核查](tikzilla/content_review.json)
- [原始推理报告](tikzilla/report.json)
- [仅去除响应包装后的编译报告](tikzilla/document_only_report.json)
- 每题目录保留原始响应、完整提示、未经内容修复的 TikZ 源码和实际 PNG。

明显问题包括：三角形版面被大段照抄的提示占据且裁切；透镜与折射位置没有对齐且缺少焦距标记；冒泡排序缺少所要求的单独数字框和相邻交换标记；对流路径不闭合；Cantor 图缺少中间三分之一的间隙，剩余长度错误；肾单位缺少 U 形管道及独立血管。

模型版本固定为 35b3f5b15a4db9307d8434cd7f8a17fdf3f0038c，无需 Hugging Face 登录。模型卡采样为 temperature=1.0、top_p=0.9、max_new_tokens=2048；种子 42–47。实际依赖版本与模型卡推荐依赖的差异均在报告中记录。仅作推理试跑，不声称复现论文指标。

## DeTikZify 的可复查结果

- [参考图与输出对照](detikzify/comparison.png)
- [逐图内容核查](detikzify/content_review.json)
- [推理报告](detikzify/report.json)

权重版本为 f17cd7872bb23879ccf76fda90e56e21b8ee4e51，作者代码版本为 13ac429925f0125ce5117676450134f400499d0d。图像输入来自之前 Qwen SVG 试跑，明确作为重建目标而非正确答案。运行单次采样，未运行 MCTS 搜索或完整公开基准。此模型是图像转 TikZ，不替代文字生成图的任务。

## Code2Video 的复现边界

本轮直接调用作者 GENERATE_VIDEO，保留其大纲、分镜、Coder、渲染与 Critic 流程；不接入本项目额外的 lesson contract、配音或评分逻辑。Qwen 替换作者 API 模型，Critic 使用八张有序视频抽帧替代原服务的原生视频输入；可选图标服务关闭，重试上限另行记录。上游运行补丁及源码差异会保留。不声称这是原 API 模型成绩，也不把无配音的作者流程成片当作本项目英文讲解视频验收通过。

脚本：scripts/reproduce_tikzilla.py、scripts/compile_tikzilla_outputs.py、scripts/reproduce_detikzify.py、scripts/reproduce_code2video_native.py。完整本地运行目录位于 results/tikzilla_author_20261110、results/detikzify_author_20261110、results/code2video_native_20261110；日志位于 logs/reproduction_20261110。旧轮次未改写。

## 续接与视频汇总（2026-11-10）

续接核查未发现最终 report.json 或完整合片。日志最后记录在 03:33 UTC，不能继续标为正在运行。
当前环境拒绝本地模型端口连接（Operation not permitted），因此尚未恢复模型生成，也未完成全片验收。

全部已有视频已复制到 `delivery/all_generated_videos_20261110/`：1688 个文件，含 129 个非缓存视频及 1559 个渲染缓存片段。
同目录 manifest.json 保存来源与 SHA-256；原件未修改。非缓存视频包括章节与测试，不能视为全部完整成片。
运行 `python3 scripts/collect_generated_videos.py --out delivery/all_generated_videos_20261110` 可重新汇总；已有同名但内容改变的文件会报错，避免覆盖。

GitHub 推送尝试失败：无法解析 github.com。未完成远端同步。

### 访问恢复与续跑

环境访问权限更新后，github.com DNS、GitHub 远端访问、GPU 及本地 Qwen 端口均恢复。
提交 c4c798f 已成功推送，远端 main 已核对。此前网络阻塞记录为历史状态。
已启动恢复运行，保存恢复前完整快照，复用第 1、2、5 段优化视频；由作者修复及 Critic 流程处理第 3、4 段。
续跑日志：logs/reproduction_20261110/code2video_resume.log。仅在全部章节有输出时合片；完成与质量以最终报告及实际视频检查为准。

### 最终生成状态（2026-11-10 04:20 UTC）

续跑完成，5/5 章节生成并合片，续跑耗时 2449.17 秒；复用第 1、2、5 段。
最终视频为 73.066667 秒，H.264、854×480、15 fps，无音轨。ffmpeg 全程解码通过，无错误。
[生成报告](code2video_report.json)、[媒体审计](code2video_media_audit.json)、[抽帧概览](code2video_overview.jpg) 已保留。
抽帧可见说明文字较小、部分对象对比度低；未做完整时序教学质量验收，不能宣称质量通过。
作者 token_usage 不覆盖所有直接修复与 Critic 调用，不能视为本轮总消耗。
视频已补入统一交付目录，便于查找的文件名为 Code2Video_Linear_transformations_and_matrices_FINAL.mp4；manifest.json 保存全部来源和哈希。
