# 工作暂停交接：2026-11-02

用户明确要求停止工作，记录进度和未完成目标。当前生成与重评任务已停止；
暂停时检查 `/proc`，未发现 `run_qwen_sample10.py`、`run_model_case.py` 或
`reevaluate_qwen_sample10.py` 正在运行。不要在用户要求继续前自动启动。

## 用户最终授权的目标

1. 做适用于整个 400 题库的通用修复，不能只针对第三题写特例。
2. 不降低验收要求，不把“能渲染”“JSON 合法”当成高质量完成。
3. 全部修改验证后，提交并推送 GitHub **main**。
4. 然后在 **GPU 0 / Qwen3.8-27B** 重跑原来固定抽取的 **10 题**。
   最新指令是重跑 10 题，不是启动 400 题全量生成。
5. 严格五秒：75 个解码帧，15 fps；保留原题要求、原图非授权区域。
6. 使用已批准的 v4 评分：强化易懂性、形象化解释；教学吸引力单独报告，
   不计入八维总分、不抵消知识错误。

## 仓库与环境

- 主仓库 `/root/video-teacher`，分支 `main`。
- `/root/videoteacher` 是 `/root/video-teacher/research/code2video` 的符号链接。
- origin: `https://github.com/Geniusyingmanji/video-teacher.git`。
- 最近已推送：`b4ebe3389b0fa5c3e63c3c9ed738c88bafba8e99`。
  之前的五秒修复提交为 `2cbd568`、`15e3e30`。
- 当前 main 与 origin/main 在上述提交同步，下面的新通用修复**尚未提交**。
- Code2Video vendor checkout 在 `research/code2video/Code2Video/`，被主仓库忽略；
  vendor 本地修改需要用补丁文件或仓库原生模块保存，不能只改被忽略的文件。
- 渲染环境 `/root/code2video-env/bin/python`，Python 3.11，Manim CE。
- 推理环境 `/root/qwen38-env/bin/python`，Python 3.14，vLLM 0.31.0。
- 模型 `/root/models/Qwen3.8-27B`，API 模型名 `qwen3.8-27b`，端口 8000。
- 原图 `/root/video-teacher/data/sources/grade/selected_assets/before/`。
- shell 环境内默认可能找不到 ffmpeg；将 `/root/code2video-env/bin` 放到 PATH。
- GPU/本地 API 访问在沙箱内曾被拒绝，实际模型运行需要正常申请沙箱外执行。
- Git 仓库未设身份；前几次提交沿用历史身份：
  `git -c user.name=AI_Explorer -c user.email=explorer@ai.com commit ...`。
- 早前用户原有未提交修改保存在 Git stash：
  `before-update-20261102-qwen-start`；不要删除或擅自混入本次修改。

## 已实现、已推送的功能

- `generation/strict_video_contract.py`：完整当前题目贯穿规划、分镜、代码、修复；
  区分当前任务字段与历史 original_prompt_text / source.original_instruction。
- `generation/strict_manim.py`：测量完整事件时间线，再分配 75 帧重新渲染，
  不是截掉视频；结尾留一秒，原图任务开头留一秒；检查时长和原图保护。
- `scripts/run_qwen_sample10.py`：固定随机种子 `20261102`，抽 400 题中的同 10 题。
- v4 评分及文档 `docs/TEACHING_DESIGN_V4.md`。
- `scripts/reevaluate_qwen_sample10.py`：随清单更新重评成片，缺失题保留在十题分母。
- 之前相关 22 项评分测试、4 项严格渲染测试曾通过；这不等于新修改全部通过。

## 最近一次运行的真实状态

目录：`results/qwen38_gpu0_sample10_strict5s_20261102/`。

- 第 1 题 `grade_his_task_16`、第 2 题 `cand_med_cs_gap_05` 曾通过生成结构/五秒验收。
- 第 3 题 Markov chain、第 4 题几何、第 5 题正态分布直方图失败。
- 暂停前第 6 题正在生成，已停止；不能说 10 题完成。
- “生成 complete=true”此前只表示结构和时长通过，**不表示教学质量通过**。
- v4 首题曾有八维有效评分 50 分，被文字稳定性和静止门槛封顶；教学吸引力评分
  格式无效，后续重评又出现 applicable 非布尔错误。因此没有十题有效高质量结果。
- 原图失败实证：Markov 视频五秒正确，但授权框之外约 6.1% 像素变化，被拒绝。
- 日志：`qwen-sample10-strict5s-20261102.log`、
  `qwen-sample10-v4-reevaluation.log`。
- v4 结果在该 run 目录的 `video-teacher-2x8-v4/`。
- Qwen 服务日志 `research/code2video/qwen38-vision-gpu0-20261102.log` 最后显示
  03:31:14 EngineCore 被 SIGTERM 后退出，API 关闭。暂停时本地端口测试为连接拒绝。
  没有证据将其归因为 OOM；下次按实际日志排查并重新启动。

## 400 题通用审计已发现的事实

`data/prompts/candidate_400.jsonl` 恰好 400 个条目；来源：
GRADE 178、DisciplineGen-1M 116、自编/无 source.dataset 106。
没有空 prompt；386 题显式 target_duration_s=5，14 题未填；400 题均不要求音频。
178 题有 GRADE source_image_path。按精确大小写拼接有 15 题误报缺图，
按文件名 casefold 解析后这 178 张原图均能找到。

主要根因：

1. 源图经过缩放留边，模型却在归一化画布坐标、原图坐标和 Manim 坐标之间手算，
   同一题的授权框和实际标注位置不一致。
2. 原始 JSON mode 不能保证评分 criteria 有六项、applicable 是布尔等。
3. 附加评分失败会让整题重新调用八维，浪费且导致已有效评分随机变坏。
4. 原图保护只看压缩视频的全图平均容差，可能漏掉小面积越界修改；需要更严格的
   编码前逐帧保护，再将压缩后检查作为补充，不能只放宽阈值。
5. 渲染成功未与高质量验收、具体任务覆盖挂钩；旧修复经常只读笼统异常。
6. 某些题的历史元数据和当前 prompt 不一致，必须遵守既定字段优先级；不能根据
   original_instruction 偷换当前任务。题意自身不充分时不能编造答案来通过。

## 当前未提交修改（进行中，不能直接宣布完成）

已修改文件：

- `eval/benchmark_video_rubric.py`
- `eval/judges/gpt55.py`
- `eval/rubric_6x6.py`
- `eval/teaching_engagement.py`
- `generation/strict_manim.py`
- `generation/strict_video_contract.py`
- `research/code2video/experiments/run_model_case.py`

新增文件：

- `eval/judges/structured_rubric.py`：严格 JSON Schema、六个 criterion ID、布尔/数字类型、
  有界验证重试；不默默修补无效评分。三个评分入口开始接入；gpt55 拒绝 length 截断。
- `generation/source_geometry.py`：通用原图需求判定、大小写无歧义素材解析、
  原图像素到留边画布的统一转换、OpenCV 检测原图矩形候选框。
- `generation/source_primitives.py`：SourcePrimitives.text/curve/highlight，
  用原图像素定位、检查冻结框、最小 16 渲染像素文字；替换文字时保留框边缘。

进行中的接入：

- contract VERSION 已从 v2 改为 `strict-five-seconds-v3`。
- source 编辑框改为**原图像素单位**；contract 保存尺寸、原图哈希、矩形候选框。
- 提示 coder 使用 runtime 的 `self.source_text/curve/highlight`，不要手写坐标映射。
- renderer 开始挂载这些 helper，将原图框转换到画布再执行保护检查。
- 时间分配开始设置每个 play 至少 6 帧、wait 至少 3 帧，避免强行压成闪烁。
- 原图检查开始记录越界变化连通域框，修复 API 开始携带实际 diagnostics。
- run_model_case 新增 `--attempt`、`--quality-feedback`，素材解析改用通用 resolver；
  输出 CASES 目录开始带 attempt 后缀。批次 runner 还没有完整接入这些新参数。

## 测试进度与风险：下次必须先做

- 新 structured helper 的真实 API 测试**尚未成功**：第一次被沙箱拒绝；按规定升级
  后发现服务已退出、端口连接拒绝。不能声称 Qwen 的 JSON Schema 实测通过。
- 最近运行 `test_teaching_engagement.py` 5 项、`test_strict_video_contract.py` 4 项通过，
  但 source 渲染测试仍使用旧归一化框，必须改成像素框、加强小面积越界反例；
  当前测试通过不足以证明新坐标实现正确。
- 新模块未完成全面审查；不要直接推送这些半成品或启动重跑。
- structured retry 会重新验证每项，不降低证据标准；需补 schema、错误类型、
  截断、重复 ID、空证据和重试耗尽测试。
- 当前 structured helper 已把 chat ValueError 放进验证重试 try 内，但网络错误仍会
  向外传播；下次需要明确基础设施故障 vs 内容/格式故障，避免无效循环。
- SourcePrimitives 的 curve 仍要求盒内，原 25% 面积上限仍保留。对直方图等较大
  目标，应该设计任务对象级冻结掩膜/验证流程，不能简单扩大框来使旧结果通过。

## 下一步按顺序完成

1. 复查全部工作区 diff；不重做已推送的 v4 功能。
2. 完成通用素材/坐标/冻结目标规范及编码前逐帧原图保护；诊断输出应让修复能看到
   真正错位位置。检查目标框是否真的对应原题对象，防止模型扩大框掩盖错位。
3. 完成结构化评分的真实模型验证；补齐失败维度独立重试/复用有效维度的缓存逻辑。
   缓存仍必须匹配视频哈希、case 哈希、评分版本、模型及实现哈希。
4. 新增明确的高质量 gate：严格时长、源图保护、任务覆盖、正确性、可读性等
   分开记录；不能以生成 complete 或 JSON 合法作为高质量结果。
5. 批次 runner 接入有界质量反馈修复、独立 attempt 目录和证据保存。修复任务要求
   不变，不能无限重试、不默默跳过失败题；400 题都使用同一实现。
6. 建立 400 题全量预检报告和按任务类型的回归测试：所有素材解析、大小写、
   不同纵横比/留边坐标、题意/目标缺失、严格五秒/最小可读时间、原图小面积
   越界、评分 schema、缓存和质量 gate；包括失败反例，不能测试只贴实现。
7. 重新启动 GPU 0 的 Qwen vision 服务，做真实 schema、真实源图标注及真实渲染验证。
   可先用既有启动脚本：`CUDA_VISIBLE_DEVICES=0 QWEN_VISION=1 QWEN_MAX_SEQS=2 bash
   research/code2video/experiments/start_qwen38.sh`，日志用新名字保存。
8. 必要的测试通过、实际证据检查后，按用户授权提交并推送 GitHub main。
9. **推送后**在新的 run 目录，以修复版本重跑同一批 10 题（seed 20261102）。
   不复用旧版几何/质量 contract 的结果冒充新通过；保留旧产物。
10. 报告实际完成数和质量缺口。不能保证未经运行的 400 题全部高质量；要区分
    400 题结构预检覆盖、分类型回归、10 题实跑和真正 400 题全量实跑。

固定十题 ID：
`grade_his_task_16`, `cand_med_cs_gap_05`, `grade_ComputerScience_task_17`,
`grade_math_math_90`, `grade_math_static_9`, `disciplinegen_chemistry_32e43cbfb37a3402`,
`cs_prob_02`, `grade_board_games_task_13`, `cand_hs_civ_05`, `med_exp_01`。

用户偏好：直接执行已授权工作，不反复询问确认；清楚区分已验证结果与计划。
本次用户明确暂停，因此当前只记录交接，不继续实现、提交、推送或启动任何任务。
