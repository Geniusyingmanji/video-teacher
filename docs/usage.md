# 协作者一键运行

当前代码入口为 `teacher.py`。`bench` 使用统一代码场景后端测模型的教学视频生成能力；`method` 在同一后端增加公开题面的状态计算和受约束视觉修复。两者均自动生成完整英文旁白视频，再用相同评测协议评分。

原生入口 `bench --backend video` 支持 Ark／Wan／Wan3 异步协议，尚待服务实测通过。代码场景基线不能充当原生 T2V，`bench --framework code2video` 另行调用官方源码适配器，本方法与其分开。进度见[当前状态](status.md)。

当前实验与付费模型调用暂停；以下命令供恢复运行或协作者使用。

三评委已接入 `bench`、`method` 和 `evaluate`，固定题包的 Specific 可同时启用。完整配置字段、调用示例与输出位置直接维护在 [README：三评委配置与调用](../README.md#三评委配置与调用)。旧单评委配置继续可用；前缀学生提问仍独立于固定题包评分。

## 三条实验路线的接口状态

| 路线 | 当前入口与已实现部分 | 尚需完成 |
| --- | --- | --- |
| 原生视频生成 | `bench --backend video`；Ark／Wan／Wan3 请求构造、异步提交与查询、任务续跑、下载、分镜拼接及共用配音 | 真实服务验收；逐型号时长／图像输入适配。当前没有 Veo、Sora 协议实现 |
| 语言／多模态模型＋统一代码框架 | `bench --backend code`；模型输出 JSON 场景，校验、渲染、配音并自动评 General | 旗舰 B* 的服务和任务兼容性验收；这一路不是官方 Code2Video |
| 语言／多模态模型＋我们的框架 | `method`；在代码后端加入公开任务状态、布局处理、成片反馈与可选关系工具 | 旗舰 B* 验收；论文中 Base→S→S+R→Full 的统一阶段开关仍需拆分 |
| 模型＋Code2Video | `bench --framework code2video`；固定官方源码、公开任务／旁白适配、Manim 容器渲染、共用三评委 | 离线官方调用链已验证；Docker 渲染和真实模型五题验收待执行 |
| 模型＋其他外部框架 | 可用 `evaluate --manifest` 接收外部成片 | SGA、ManimAgent、Remotion 生成适配未实现 |
| 模型＋通用成片反馈基线 | 已有 `visual_agent.py` 反馈组件 | 独立于方法专用编译／修复的 Generic Visual Repair 入口待拆出 |

Code2Video 的安装、配置及完整调用直接见 [README](../README.md#官方-code2video-接入与调用)。

代码依据：[服务配置](../localbench/services.py)、[聊天传输](../localbench/client.py)、[CLI 编排](../localbench/run.py)、[原生视频协议](../localbench/video_api.py)、[原生分镜拼接](../localbench/native_pipeline.py)。

**切换 B* 的边界：** 当前聊天传输固定使用 `/chat/completions` 请求和 `choices[0].message.content` 响应，支持文字／图片及可配置 JSON 输出参数。兼容该格式的网关可以通过配置接入；其他厂商的原生消息、内容生成或 Responses 协议尚无独立适配。仅更换模型名不能证明旗舰模型已经接通，还需核对图像输入、token 参数、JSON 输出和生成／听音／视觉评委各自的服务配置。`doctor` 只检查本地配置与环境，输出 `network_probed: false`，不验证 API 可用性。

**全库输入边界：** 当前自动附件路由覆盖 178 道 GRADE 图片题；另 3 道题的 `source.local_before_path` 已随代码包保留图片，但尚未由 `public_case()` 传给生成器。旧 `wan` 协议明确拒绝图片输入，不能直接承担全部带图题；`wan3` 与 Ark 的带图请求也需逐型号实测。原生片段当前统一输出 720p／24 fps 展示副本，代码默认输出 1024×576／12 fps，论文比较需要记录这一差异。

接口已通过禁用网络连接的离线测试，覆盖聊天调用、三评委与固定题包评分、原生任务收据／续跑、分批 CLI、预检与视觉反馈。原生协议使用模拟服务响应，测试通过不等于已通过真实视频服务或旗舰模型验收。

## 安装

提供 macOS／Linux 后端，要求 Python 3.11+，建议 Python 3.12。系统默认 `python3` 若仍为 3.10，请显式使用 3.12。macOS 和 Linux 均已实际运行两条入口；Linux 在新 Python 3.12 环境完成讲解/解题各一题的双入口试跑，现有环境与结果限制见[当前状态](status.md)。无需 CUDA。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Linux 可安装 `espeak-ng` 与 DejaVu 字体提供离线英语旁白；macOS 默认使用 `say` 的 Samantha。若配置 Edge TTS，需要用 `pip install -r requirements-tts.txt` 安装可选包 且能访问其网络服务。程序会测量实际语音长度后排时；不会用静音代替配音。首次完整评测还需下载 Whisper `base.en`，后续使用本地缓存。

```bash
# Debian / Ubuntu 的可选系统依赖
sudo apt-get install espeak-ng fonts-dejavu-core

# Alibaba Linux / RHEL 系列（包名以系统仓库为准）
sudo yum install espeak dejavu-sans-fonts
```

服务器不能访问 Hugging Face 时，可用配套离线 ASR 包 `video-teacher-asr-base-en-3d3d5dee.tar.gz`。它包含公开的 `Systran/faster-whisper-base.en` 固定快照，单独提供，不含服务凭据。解压到项目缓存后启用离线模式：

```bash
mkdir -p .local-cache
tar -xzf /path/to/video-teacher-asr-base-en-3d3d5dee.tar.gz -C .local-cache
export HF_HUB_OFFLINE=1
```

该包 SHA-256 为 `ed6e5ac8f7cf491653fb93f4f5a0bef933fc6330cc05b16750b63c46a7b0da40`；文件清单与逐文件哈希在解压后的 `.local-cache/ASR-MANIFEST.json`。离线模式只用于模型权重缓存，生成与 VLM/听音评分仍需访问所配置的 API。

若系统盘空间较少，在数据盘目录创建项目和虚拟环境，并将安装临时目录、包缓存放到同一数据盘；无需占用 GPU。

## 三项服务配置

用环境变量提供模型、URL、API key。URL 可以是根地址、`/v1`、`/compatible-mode/v1` 或完整 `/chat/completions` 地址。示例中的占位值需替换。

```bash
export VIDEO_TEACHER_MODEL='qwen3.8-flash'
export VIDEO_TEACHER_BASE_URL='https://YOUR-SERVICE/compatible-mode/v1'
export VIDEO_TEACHER_API_KEY='YOUR-API-KEY'

# 本地配置、输入、旁白环境检查，不调用模型
.venv/bin/python teacher.py doctor

# 默认三题，自动生成并评测
.venv/bin/python teacher.py bench --out results/my_bench

# 同三题，运行本项目方法并评测
.venv/bin/python teacher.py method --out results/my_method
```

生成模型需要支持文本／图片输入，输出符合提示的 JSON 场景程序。旧单评委模式中，未配置 judge 时与生成模型共用服务；三评委模式要求显式配置三家模型，且不与 `judge` 混用。单评委 Qwen 默认通过相同 URL／key 调用 `qwen3.5-omni-flash` 做实际听音；全模态 Omni 则复用自身。三评委模式必须明确配置 `audio_judge`，或设为 `false` 保留音频缺失。只有视觉能力的模型不能完成听音评分。

不同服务分别配置时，复制 [collaborator.example.json](../configs/collaborator.example.json) 到仓库外，修改模型和 URL。每个服务可指定不同的 `api_key_env`；只有地址相同才允许继承未提供的凭据。API key 不写进运行配置及报告。

```bash
.venv/bin/python teacher.py bench --config /path/to/private/services.json --out results/my_bench
.venv/bin/python teacher.py method --config /path/to/private/services.json --out results/my_method
```

`json_format: false` 适用于不接收 `response_format` 的服务，仍会解析和校验返回 JSON。`extra_body` 可补充供应商支持的请求参数，但不能覆盖 model、messages、stream、max_tokens。

## 选择题目、并发及续跑

推荐先让协作者试跑五题，确认依赖、服务、旁白、成片和评分报告，再运行全库。先配置好上文的环境变量或在命令中加 `--config /path/to/private/services.json`。

```bash
.venv/bin/python teacher.py doctor --num 5
.venv/bin/python teacher.py bench --num 5 --out results/bench5
.venv/bin/python teacher.py method --num 5 --out results/method5
# 分批示例：第 6–10 题
.venv/bin/python teacher.py method --offset 5 --num 5 --out results/method_next5
# 只重评输入清单的前两题
.venv/bin/python teacher.py evaluate --manifest results/method5/manifest.json --num 2 --out results/review2
```

`--num` 默认从完整题库按固定顺序取题，不受默认三题样例限制；`--offset` 从 0 开始，必须与 `--num` 一起用。指定 `--ids` 时先按所给题号及顺序选题，再截取；生成命令显式指定 `--suite smoke` 时只在三题样例中截取。`evaluate` 和 `student` 默认在输入清单中截取。超出范围报错。固定顺序的小批不是分层抽样；需跨学科覆盖时用 `--ids` 指定样例。

每批报告只统计本批，不自动合并。确认后全量运行使用新目录，小批任务会在全量中重新运行；`--resume` 不能改变已冻结的题集。可用下面命令调度全库，预算以小批实耗调整。

```bash
# 400 题候选池全部进入生成与汇总
.venv/bin/python teacher.py bench --suite all --out results/bench400 --max-calls 32000 --max-tokens 240000000

# 同一 400 题、13 学科，运行本项目方法
.venv/bin/python teacher.py method --suite all --out results/method400 --max-calls 32000 --max-tokens 240000000

# 任意指定题号，同样自动评测
.venv/bin/python teacher.py method --ids econ_prob_01 phys_exp_02 geo_exp_03 --out results/method3

# 复用已完成视频及已有评分（包括明确留空的评分）
.venv/bin/python teacher.py bench --out results/my_bench --resume

# 独立评测已有本入口清单；不再生成
.venv/bin/python teacher.py evaluate --manifest results/my_bench/manifest.json --out results/rejudge
```

续跑需要相同的题集、模型、配置、预算和代码；代码／协议改变后用新目录。重试失败生成保留历史文件。`--resume --retry-incomplete` 可重试未形成完整综合分的评测，旧证据留在 previous_attempts。内容核查与评分冲突仍可能保持空分。全量命令保留失败题；原图任务支持标签替换、专用计算后端及通用原图标注，但通用标注不保证完成所要求的几何或图像变换。400 题是候选池，未全部获得专家内容批准。

CLI 默认 API 并发 8、渲染并发 2、评测并发 4；本项目恢复运行时按当前约定显式设置 `--api-workers 4`，可使用 `--api-workers`、`--render-workers`、`--eval-workers` 调整。`--max-calls`、`--max-tokens` 限制整个运行的模型调用和 token 预算预留，生成、视觉和听音共用一个台账。token 预算不是已核验的人民币账单上限。详细协议的单题调用数通常超过 30；全量示例显式提高预算，默认 8000 次／8000 万 token 不保证覆盖全部 400 题。建议先跑默认三题，依据服务实际用量和单价设置全量预算。当前 resume 冻结预算，预算变更需要新目录。

内网 Matrix 网关若被系统代理错误转发，可在运行前设置 `NO_PROXY=matrixllm.alipay.com`（保留其他需要直连的域名）。其他服务按其实际网络要求配置。

## 输出

保留与回传的完整清单见 [README：需要保留和回传的文件](../README.md#需要保留和回传的文件)。本地保留整个运行输出目录；默认回传逐题评分、失败记录、配置和用量，不传视频、音频或整套抽帧。若重评引用外部原视频，在本地保留原生成目录。

| 文件 | 用途 |
| --- | --- |
| `REPORT.md` | 可点击视频与逐题大维度分数 |
| `summary.json` / `scores.csv` | 全部所选题的状态、十个叶维度、交付率、评分覆盖率 |
| `manifest.json` | 当前成片、媒体哈希与全部计划题状态 |
| `generation/` | 计划、旁白、视频、生成失败和修复记录 |
| `evaluation/` | 最终视频抽帧、实际音轨、评分引用及错误 |
| `api/usage.jsonl` / `api_usage.json` | API 请求、服务端用量及预算预留 |
| `run_config.json` | 无 API key 的运行与代码快照信息 |

报告分视频质量、教学质量；教学进一步分内容、组织、表达。视频三叶维度等权，教学七叶维度等权，两类各占 50%。内容／组织／表达在教学内分别占 2/7、3/7、2/7。

可选第三块为 [模拟学生诊断](student.md)。在配置中加入 `student_evaluation` 可随原命令运行；`teacher.py student` 可单独评已有视频。第三块报告理解、疑问、证据核验与覆盖率，不参与原综合分。若启用此块，退出码 0 还要求所有学生会话完成；单独 `student` 命令的退出码仅检查该块完成情况。

退出码 0 表示所选题全部交付且 General 可计算，并且已启用的 Specific／学生阶段完成；退出码 2 表示配置错误或有失败／缺失评分。有效综合分仍不等于教学质量合格，VLM judge 需要人工校准。不要只展示成功视频的均分而忽略交付率和评分覆盖率。

## 原生视频 API

复制 [collaborator.video.example.json](../configs/collaborator.video.example.json) 到仓库外，分别配置聊天规划／评测服务和视频服务。视频服务 key 放在 `VIDEO_TEACHER_VIDEO_API_KEY`。示例使用 Ark 正式路径；现有 Matrix key 不等于 Ark key。

```bash
.venv/bin/python teacher.py bench --backend video --config /path/to/video-services.json --ids chem_exp_01 --out results/native_smoke --max-video-seconds 80
```

`--max-video-seconds` 默认 120，限制累计提交的输出秒数，含分镜向上取整，不能覆盖默认三题的全部目标时长。超限后保留已有任务，报告未交付。单段时长必须符合实际模型；旧版固定 5 秒模型需把 `max_shot_seconds` 设置为 5（当前通用切片请求整数秒，应先用支持可变时长的模型）。

请求在服务端创建后以 task ID 续跑，不重新付费提交。若网络中断导致提交结果未知，`task.json` 标记 `submission_unknown`；需先从服务端找回任务，不能删掉收据盲目重跑。原生片段按实际配音时长裁剪并拼接，过短片段报错，不循环或拉慢补时。

独立评测默认选择清单全部题目；存在多个成片版本时用 `--mode code` 或对应模式显式选择，避免静默漏评。`method` 当前使用代码后端。


严格评分与限制见[评测协议](evaluation.md)。本地打包与离线校验：

```bash
.venv/bin/python scripts/build_collaborator_bundle.py --out /tmp/video-teacher-current.tar.gz
.venv/bin/python scripts/validate_collaborator_bundle.py --bundle /tmp/video-teacher-current.tar.gz --out /tmp/video-teacher-validation.json
```

构建包包含当前代码、测试、文档、配置示例、400 题、来源元数据与 181 张题目输入图（另有 1 张测试图）。不包含重复图、答案图、视频、音频、凭据、实验结果或模型权重；不要直接打包整个工作目录。

### dev14 评测资源与依赖

General 默认逐帧分批检查全部解码帧，另对全部定时语音窗口分批核对同步；模型调用量和本地证据空间显著高于旧抽帧协议。既有预算限制仍有效，预算耗尽记覆盖不完整和未验证，不静默跳过批次。恢复实验时先小批量测真实用量，再预先设置预算。

安装系统 `ffprobe`（通常随 `ffmpeg` 软件包提供），用于区分真正无音轨和音频解码/探测故障。只装 imageio 的 ffmpeg 不一定包含 ffprobe；探测工具不可用时不会推断“没有音轨”。代码和协议变化后使用新输出目录；本次修复不自动重评历史结果。报告新增“质量验收”与验收率，执行成功及高 General 均分均不自动表示验收通过。

### 对已有声明式成片做局部修复

```bash
.venv/bin/python teacher.py repair --data data/tasks.jsonl \
  --manifest results/source/manifest.json --ids TASK_ID \
  --patch /path/outside/repo/patch.json --out results/local_patch
```

patch.json 示例（哈希必须来自实际源片和计划，不能使用占位值）：

```json
{"case_id":"TASK_ID","video_sha256":"ACTUAL_MEDIA_SHA256","plan_sha256":"CANONICAL_PLAN_DIGEST","replacements":[{"scene":1,"field":"caption","old_text":"Entire current caption","new_text":"Entire corrected caption"}]}
```

`plan_sha256` 使用 `localbench.common.digest(json.loads(plan_file.read_text()))`，视频哈希使用 `localbench.provenance.file_hash(video)`。源 manifest 必须带匹配的 public_input_hash，并明确只有一条完整 code 成片。字幕修复不请求模型；旁白修复通过可选 `--config` 的 tts 设置合成，因此其后端可能需要联网。此命令不是恢复实验的授权；本次验证使用离线测试音频和假模型回答。

生成的语音调度另保存 timing_attempts.json，记录每次实际语音时长、语速、目标时长和文本哈希。重写必须满足实测字数上限且实际减少字数；仅“换个说法但更长”不再作为有效收敛。文件时长覆盖和 ASR 活跃语音覆盖仍分别解释，不能把这些记录当成完整费用账单。
