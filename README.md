# RISE-Teacher

完整教学视频的 benchmark 与代码介入生成方法。400 道候选题、13 个学科，覆盖讲解和解题，目标约 50–105 秒英文旁白视频。先完成 benchmark，再验证方法收益。

当前为开发阶段：全库实验与人工校准尚未完成；方法迭代和付费调用暂停。**禁止从本地执行 git push。**

## Benchmark 与方法

- **General**：视频质量，以及教学质量下的内容、组织、表达；10 维 × 6 项整数 1–5。视频与教学各占 50%。
- **Specific**：逐题知识问题评分，与 General 并列。
- **模拟学生**：分段理解、疑问与图示对应诊断，独立报告。
- **方法**：公开任务 → 课程规划 → 声明式场景／可执行状态 → 校验、配音、渲染 → 成片反馈修复 → 可选关系约束 → 独立评测。

已有局部关系修复结果，尚无稳定跨题教学收益或 RSI 证据。[当前状态与结果](docs/status.md)。

论文主表模型、框架对照、组件消融、图表与执行规模见[论文实验规划](PAPER_PLAN.md)。MVP 计划使用最强可用模型＋我们的框架，并与同一模型＋其他框架及原生视频系统比较；具体模型待开发预检后冻结。这是待执行方案，不代表已获得正式成绩。

## 数据分布

| 学科 | 讲解 | 解题 | 合计 |
| --- | ---: | ---: | ---: |
| 数学 | 7 | 32 | 39 |
| 物理 | 18 | 19 | 37 |
| 化学 | 18 | 19 | 37 |
| 生物 | 18 | 19 | 37 |
| 医学 | 11 | 8 | 19 |
| 计算机科学 | 18 | 19 | 37 |
| 历史 | 11 | 25 | 36 |
| 地理 | 19 | 18 | 37 |
| 经济与金融 | 14 | 23 | 37 |
| 社会与公民教育 | 5 | 7 | 12 |
| 语言与文学 | 5 | 8 | 13 |
| 艺术与音乐 | 11 | 23 | 34 |
| 体育与棋类 | 0 | 25 | 25 |
| **合计** | **155** | **245** | **400** |

体育与棋类为普通学科，`--suite all` 与 `--suite core` 均选择全部 400 题。开发成员 124 题、预留候选 276 题；预留候选尚未认证为正式未见测试集。

## 文件结构

```text
video-teacher/
├── README.md                 # 项目说明与完整目录导航
├── PAPER_PLAN.md             # 论文模型清单、实验矩阵与图表规划
├── AGENTS.md                 # 当前操作约束
├── teacher.py                # bench / method / evaluate / student / doctor
├── requirements.txt          # 当前运行依赖
├── requirements-tts.txt      # 可选网络配音
├── localbench/               # 当前唯一实现
│   ├── run.py, pipeline.py   # CLI、规划与生成
│   ├── code2video.py         # 官方 Code2Video 生成与完整教学任务适配
│   ├── code2video_source.py  # 固定上游源码验证与加载
│   ├── code2video_runtime.py # Docker 渲染与运行配置
│   ├── scene.py, state.py    # 渲染与领域状态
│   ├── rubric.py, judge.py   # General 评分与汇总
│   ├── judge_panel.py        # 三评委独立评分、逐项汇总与分歧记录
│   ├── specific_eval.py      # 冻结题包的三评委 Specific 评分
│   ├── student*.py           # 分段学生和知识诊断
│   └── student_questions/    # 逐题问题、评分与回答轨迹
├── configs/                  # 服务示例、学生画像、题目编辑规则
├── data/
│   ├── source_tasks.jsonl    # 带来源的构建输入
│   ├── tasks.jsonl           # 当前统一 400 题
│   ├── tasks.summary.json    # 题库状态
│   ├── development_membership.json  # 已知开发成员
│   └── sources/              # 来源元数据与素材
├── docs/
│   ├── benchmark.md          # 数据、范围、输入边界
│   ├── evaluation.md         # 维度、权重、六十项细则
│   ├── method.md             # 代码介入生成与修复
│   ├── student.md            # Specific 与模拟学生
│   ├── usage.md              # 安装、配置、命令与输出
│   ├── research.md           # 相关工作与方法启发
│   └── status.md             # 当前进度与近期结果
├── scripts/                  # 打包、包验证、排版验证、Code2Video 安装与离线联调
├── tests/                    # 当前实现的离线回归与排版样例
├── results/                  # 本地实验媒体、评分与失败，不随代码交付
└── dist/                     # 本地分发产物与可选 ASR 权重包，不随代码交付
```

## 使用与源码入口

安装、服务配置和 Linux 命令见[使用说明](docs/usage.md)。凭据放仓库外。源码按职责查阅 [localbench/README.md](localbench/README.md)。

服务配置完成后，先小批量验证；以下生成与评测命令需要模型 API：

```bash
# 本地预检，不调用模型
.venv/bin/python teacher.py doctor --num 5
# 同五题：基线生成 + General 评测
.venv/bin/python teacher.py bench --num 5 --out results/bench5
# 同五题：我们的方法 + General 评测
.venv/bin/python teacher.py method --num 5 --out results/method5
# 已有成片单独重评五题
.venv/bin/python teacher.py evaluate --manifest results/method5/manifest.json --num 5 --out results/review5
# 确认后调度全部 400 题；bench 可使用相同参数
.venv/bin/python teacher.py method --suite all --out results/method400 --api-workers 4 --max-calls 32000 --max-tokens 240000000
```

`--num N` 按题库固定顺序取 N 题；`--offset K --num N` 跳过 K 题再取 N 题。同一题库与参数下，基线和方法选择相同题目。`--ids` 可显式选跨学科样例。不传选题参数时，生成默认三题；已有视频的 `evaluate`／`student` 默认取输入清单全部题目。`--suite all` 或 `--num 400` 选择全库；超出可选数量会报错，不静默少跑。

每批使用独立输出目录；`--resume` 只续跑相同题集、配置和源码，不能把五题目录直接扩成 400 题。完整 400 题尚未全量验收，预算需要按小批实耗调整。默认入口评 General；配置三评委及固定题包后也可同时评 Specific。学生诊断需显式配置和对应画像，自动前缀提问仍是独立研究入口。

## 三评委配置与调用

使用 [collaborator.three-judges.example.json](configs/collaborator.three-judges.example.json)，复制到仓库外并填写实际服务。当前支持 **Chat Completions 兼容接口**；URL 可填 `/v1`、`/compatible-mode/v1` 或完整 `/chat/completions` 地址。

| 配置项 | 用途 |
| --- | --- |
| `generator` | 最强生成模型 B*；生成与方法修复使用它 |
| `judges` | 恰好 3 个评委，逐个填写 `id`、真实 `family`、`model`、`url`、`api_key_env` |
| `audio_judge` | 实际听音与转写核对；单独配置，不作为三份独立投票 |
| `specific_questions`（可选） | 冻结题包 JSON 路径，相对路径按服务配置文件所在目录解析 |

示例用 `VIDEO_TEACHER_GENERATOR_KEY`、`VIDEO_TEACHER_JUDGE_A_KEY`／`B_KEY`／`C_KEY` 和 `VIDEO_TEACHER_AUDIO_KEY` 从环境读取密钥。可以使用同一兼容网关，三个评委的模型与家族必须不同。家族标签由配置者填写，程序检查重复但不能核实网关别名对应的真实模型。每个评委独立配置 `json_format` 和 `extra_body`；`judge` 单评委配置与 `judges` 三评委配置不能同时出现。

三评委模式不继承生成模型。旧的 [单评委配置](configs/collaborator.example.json)仍可使用；正式比较需为所有被测系统保持相同评委配置。没有可听音模型时可显式写 `audio_judge: false`，音频分数保留缺失。

```bash
# 只检查配置、选题和本地环境，不调用模型
.venv/bin/python teacher.py doctor --config /path/to/three-judges.json --num 5

# 统一代码基线：生成五题，再由三评委评分
.venv/bin/python teacher.py bench --config /path/to/three-judges.json --num 5 --api-workers 4 --out results/bench5_panel

# 我们的方法：同五题、同三评委
.venv/bin/python teacher.py method --config /path/to/three-judges.json --num 5 --api-workers 4 --out results/method5_panel

# 只重评已有成片，不再生成
.venv/bin/python teacher.py evaluate --config /path/to/three-judges.json --manifest results/method5/manifest.json --num 5 --api-workers 4 --out results/review5_panel

# 同一配置续跑；也可以显式重试不完整评测
.venv/bin/python teacher.py evaluate --config /path/to/three-judges.json --manifest results/method5/manifest.json --num 5 --api-workers 4 --out results/review5_panel --resume --retry-incomplete
```

原生视频使用相同三评委配置，再加入 [video 示例](configs/collaborator.video.example.json)的 `video` 配置块，调用 `bench --backend video`；真实视频服务仍待验收。`--api-workers` 是生成、三评委和听音模型共享的请求并发上限；调用预算也共用，三评委需要重新估算 API 用量。

**汇总规则：** 抽帧和独立转写只准备一份，三位评委互不查看对方评分。General 的 54 项视觉／教学准则逐项取整数中位数，再按原权重聚合；6 项音频准则由共享听音模型评分。任一评委缺评、适用性不一致或三人极差达到 2 分，该项正式分留空，候选中位数与原始证据进入复核清单。已有转写争议和核查冲突继续保留，不能被投票消除；三人一致也不等于专家真值。

**启用 Specific：** 在三评委配置中添加 `"specific_questions": "/absolute/path/to/questions.json"`。格式见 [specific_questions.example.json](configs/specific_questions.example.json)：包含题目完整记录的 `case_hash`、专属问题、目标准则与引用依据。该示例仅覆盖 `math_exp_02` 的一个演示问题，试跑需用 `--ids math_exp_02`；不代表 400 题已完成题包。所有选中题目都必须有匹配题包，缺题或题目哈希变化会在模型调用前报错。

Specific 使用同三评委、同完整视频证据、同一冻结题包；逐问中位数按 `(均值 − 1) × 25` 转为 0–100，缺评、明显分歧或目标“满足／错误或缺失”冲突时留空。结果不混入 General。更换评委、题包、预算或源码需用新输出目录；默认续跑保留未完成结果，`--retry-incomplete` 会保留上一轮证据并重试，重复请求可命中缓存。复核清单供人工检查，程序不自动将待复核项改成有效分。

每题输出位置：

| 文件 | 内容 |
| --- | --- |
| `evaluation/<id>/scores.json` | 三评委汇总、General、可选 Specific 与缺失状态 |
| `evaluation/<id>/judges/<judge_id>/scores.json` | 每位评委的原始准则分、理由与证据；各自辅助检查同目录保存 |
| `evaluation/<id>/review_queue.json` | 分歧、缺评、未解决核查冲突 |
| `evaluation/<id>/actual_audio.json`、`evidence/` | 三评委共享的真实媒体与独立听音证据 |
| `evaluation/<id>/specific/` | 冻结题包、各评委逐问判断、Specific 汇总与复核清单 |

`REPORT.md`、`summary.json`、`scores.csv` 同时列出评委覆盖和 Specific 状态。退出码 0 要求所有选中题目交付、General 有效，且所有已启用的 Specific／学生阶段完成；否则退出码为 2。接口与汇总已做离线验证，三个实际评委的服务连通性与人工校准仍待执行。

## 官方 Code2Video 接入与调用

`bench --framework code2video` 已接入 [Show Lab 官方实现](https://github.com/showlab/Code2Video)，使用固定提交 `1142d8e14cdc2806df85aedb0fbb5dca474caa0f`。沿用官方 Planner、Coder、ScopeRefine 和网格 Critic；生成及内部 Critic 共用 `generator` 模型，最终评分使用另配的评委。运行标识为 `official_code2video_adapted`，适配差异与我们的方法对比见[方法文档](docs/method.md#与官方-code2video-的源码对比)。

先按[安装说明](docs/usage.md#安装)装好本项目，在 Linux 服务器准备可运行的 Docker，然后执行：

```bash
# 只下载固定哈希的生成源码、许可证与网格参考图，约 10 个文件；保存到仓库外缓存
.venv/bin/python scripts/setup_code2video.py
# 准备独立 Manim 0.19.0 环境，不修改本项目 Python 依赖
# 需要 Docker 已安装并启动
docker pull manimcommunity/manim:v0.19.0
```

复制 [collaborator.code2video.example.json](configs/collaborator.code2video.example.json)到仓库外，填写 `generator`、三个 `judges` 和 `audio_judge` 的实际服务，设置模板指定的密钥环境变量。模板已含三评委和 Code2Video 设置；不能只改模型名称就认为接口已验证。模型需要支持图片输入及 Chat Completions 格式。

```bash
# 检查配置、固定源码哈希和本地 Docker 镜像；不调用模型，也不启动生成
.venv/bin/python teacher.py doctor --framework code2video --config /path/to/code2video.json --num 5

# 生成 5 题，自动用同一套 General / 可选 Specific / 三评委评测
.venv/bin/python teacher.py bench --framework code2video --config /path/to/code2video.json --num 5 --api-workers 4 --render-workers 2 --out results/code2video5

# 同配置续跑；需要重试未完成评测时另加 --retry-incomplete
.venv/bin/python teacher.py bench --framework code2video --config /path/to/code2video.json --num 5 --api-workers 4 --render-workers 2 --out results/code2video5 --resume

# 小批确认后，使用新目录尝试全部 400 题；预算应先按小批实耗调整
.venv/bin/python teacher.py bench --framework code2video --config /path/to/code2video.json --suite all --api-workers 4 --render-workers 2 --max-calls 32000 --max-tokens 240000000 --out results/code2video400

# 成片重评沿用通用入口，不需要 Docker 或重新运行 Code2Video
.venv/bin/python teacher.py evaluate --config /path/to/code2video.json --manifest results/code2video5/manifest.json --num 5 --api-workers 4 --out results/code2video5_review
```

`--num`、`--offset`、`--ids` 与原入口一致。`method` 是我们的框架，不能叠加 `--framework code2video`；这次未接入 SGA、ManimAgent 或 Remotion。

`code2video` 配置字段：

| 字段 | 默认值与含义 |
| --- | --- |
| `source_dir`（可选） | 默认为 `~/.cache/video-teacher/code2video/<固定提交>`；相对路径按服务配置文件目录解析 |
| `docker_image` | `manimcommunity/manim:v0.19.0`；运行冻结实际 image ID，镜像改变后需新目录 |
| `feedback_rounds` | 2 轮官方布局 Critic；范围 1–5 |
| `critic_frames` | 每段抽取 8 帧，另提供官方网格参考图；范围 4–32 |
| `max_code_tokens` | 每次代码／规划请求最多输出 10000 token；总预算仍由 CLI 控制 |
| `max_fix_attempts`、`max_regenerate_attempts` | 各 3；控制渲染纠错与重新生成的外层次数，ScopeRefine 内部也可能多次请求 |
| `max_feedback_attempts` | 3；每轮反馈修改尝试上限 |
| `render_timeout_s` | 180 秒；每次 Manim 渲染的超时上限 |

**完整视频适配：** 官方默认约 5 分钟的规划改为题目指定的 50–105 秒；增加每段旁白与时长字段，使用共用 TTS 实测排时，再让 Manim 代码匹配时间槽。按分镜原顺序配音、拼接，缺段或时长不符记失败，不拉伸动画、循环片段或裁掉旁白。公开原图传给规划、代码生成和修复，外部素材搜索关闭。内部 Critic 保留官方布局提示，但使用抽帧图片兼容配置的模型；这与官方 Gemini 整段视频输入有差异。

运行只从固定上游文件加载所需生成定义；不加载上游服务配置或评测入口。模型生成的 Python 在无网络 Docker 容器执行，仅挂载该题公开工作目录，不传 API 密钥。默认 Manim 输出 480p／15 fps；与我们当前 JSON 后端 1024×576／12 fps 的差异需在论文记录。

每题 `generation/<id>/` 包含 `adapter.json`、`public_input.json`、`outline.json`、`storyboard.json`、`narration_plan.json`、`section_*.py`、`requests/`、`critic/`、`feedback/`、`render_logs/`、`framework_status.json`、`upstream.log` 与成功时的 `code2video.mp4`。`manifest.json`、评分路径、报告及用量账本沿用统一入口。失败保留在分母，Critic 故障不会当作无缺陷；只完成部分段落不登记为完整交付。

源码安装器与 SHA-256 锁清单位于 [setup_code2video.py](scripts/setup_code2video.py)和 [code2video.upstream.json](configs/code2video.upstream.json)。首次安装后可用以下命令验证官方调用链：

```bash
.venv/bin/python scripts/validate_code2video_adapter.py --out /tmp/code2video_adapter_check
```

该验证禁用网络，使用测试模型回答、测试片段和静音音轨，真实加载官方规划／修复／Critic 并用 FFmpeg 拼接；不执行模型生成的 Python，不证明生成质量。当前已通过这类联调和离线回归；本机无 Docker，实际容器渲染、真实模型服务和五题生成验收仍待执行。

## 需要保留和回传的文件

### 运行项目

协作者使用 `scripts/build_collaborator_bundle.py` 生成的源码包，不要直接压缩整个工作目录。打包器自动收集：

- `teacher.py`、`localbench/`：当前入口与全部实现。
- `requirements.txt`、可选 `requirements-tts.txt`：依赖。
- `configs/`、400 题及来源元数据：无密钥配置示例、题库和开发成员清单。
- **181 张题目输入图**：178 张当前 GRADE 输入图，以及 3 张题目声明的生成来源图；另含 1 张排版测试图。不带重复图、答案图或无关题目的图片。
- `README.md`、`PAPER_PLAN.md`、`AGENTS.md`、`docs/`、`scripts/`、`tests/`：运行说明、论文规划、约束、打包工具与离线验证。

**视频不用传。源码包排除全部实验视频、音频、`results/`、`dist/`、Git 历史、虚拟环境、缓存和模型权重。** 本地素材目录可保留原始参考数据，它的大小不等于源码包大小。模型服务密钥放仓库外；ASR 权重按服务器联网条件另行准备。

### 一次实验的结果

**本地保留完整输出目录，默认回传评分与运行记录，不传视频、音频或整套抽帧。** 需要回传：

- `REPORT.md`、`summary.json`、`scores.csv`、`manifest.json`、`run_config.json`。
- `generation_inputs.jsonl`、`evaluation_tasks.jsonl`，以及各题 `scores.json`、失败／错误记录。
- 三评委启用时，附各评委的评分 JSON、`review_queue.json` 和 Specific 评分／冻结题包，保持子目录结构。
- `api_usage.json`、`api/usage.jsonl`；学生启用时附逐题诊断 JSON 与汇总。

不要只回传均分，失败和缺失也要保留。报告中的视频与图片链接用于本地复核，接收评分文件不代表已接收媒体。下表说明需要在实验机器本地保留的内容：

| 文件／目录 | 保留用途 |
| --- | --- |
| `REPORT.md`、`summary.json`、`scores.csv` | 可读报告、逐题状态、各维度分数与覆盖率 |
| `manifest.json`、`generation_inputs.jsonl`、`evaluation_tasks.jsonl` | 本次实际选题、公开生成输入、评测任务与媒体对应关系 |
| `generation/`、方法修复产物目录 | 最终 MP4、场景计划、旁白、生成与修复收据、失败原因；至少保留清单引用的全部媒体 |
| `evaluation/` | 每题逐项分数、真实抽帧／音轨证据、原始模型响应、核查与错误 |
| `student/`、`students.json`（启用时） | 学生原始回答、疑问、复核、缺失与失败；单独问题协议的题包和评分也一起保留 |
| `api/`、`api_usage.json` | 调用记录、服务端用量、预算与缓存；用于核对费用和续跑 |
| `run_config.json`、`source_snapshot/` | 本次无密钥配置与对应的一份源码快照，用于核对运行所用实现 |

单独 `evaluate`／`student` 输出可能引用原生成目录的视频；原视频与来源清单需要在本地一起保留，回传评分记录时不要求附视频。失败任务、空分和本次重试证据与成功任务共同保留。评测任务和参考答案可供评测者核查，不能作为生成输入。

不用回传视频、音频、完整抽帧目录、`.venv/`、`.local-cache/`、旧安装包、历史源码副本或私有服务配置。当前实验凭据不得放进结果包。详细命令与输出说明见[使用说明](docs/usage.md)。
