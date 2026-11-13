# RISE-Teacher

完整教学视频的 benchmark 与代码介入生成方法。400 道候选题、13 个学科，覆盖讲解和解题，目标约 50–105 秒英文旁白视频。先完成 benchmark，再验证方法收益。

当前为开发阶段：全库实验与人工校准尚未完成；方法迭代和付费调用暂停。**禁止从本地执行 git push。**

## Benchmark 与方法

- **General**：视频质量，以及教学质量下的内容、组织、表达；10 维 × 6 项整数 1–5。视频与教学各占 50%。
- **Specific**：逐题知识问题评分，与 General 并列。
- **模拟学生**：分段理解、疑问与图示对应诊断，独立报告。
- **方法**：公开任务 → 课程规划 → 声明式场景／可执行状态 → 校验、配音、渲染 → 成片反馈修复 → 可选关系约束 → 独立评测。

已有局部关系修复结果，尚无稳定跨题教学收益或 RSI 证据。[当前状态与结果](docs/status.md)。

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
├── AGENTS.md                 # 当前操作约束
├── teacher.py                # bench / method / evaluate / student / doctor
├── requirements.txt          # 当前运行依赖
├── requirements-tts.txt      # 可选网络配音
├── localbench/               # 当前唯一实现
│   ├── run.py, pipeline.py   # CLI、规划与生成
│   ├── scene.py, state.py    # 渲染与领域状态
│   ├── rubric.py, judge.py   # General 评分与汇总
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
├── scripts/                  # 打包、包验证、排版验证三个工具
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

每批使用独立输出目录；`--resume` 只续跑相同题集、配置和源码，不能把五题目录直接扩成 400 题。完整 400 题尚未全量验收，预算需要按小批实耗调整。默认一键入口评 General；学生诊断需显式配置和对应画像，Specific 问题协议仍为独立研究入口。

## 需要保留和回传的文件

### 运行项目

协作者使用 `scripts/build_collaborator_bundle.py` 生成的源码包，不要直接压缩整个工作目录。打包器自动收集：

- `teacher.py`、`localbench/`：当前入口与全部实现。
- `requirements.txt`、可选 `requirements-tts.txt`：依赖。
- `configs/`、400 题及来源元数据：无密钥配置示例、题库和开发成员清单。
- **181 张题目输入图**：178 张当前 GRADE 输入图，以及 3 张题目声明的生成来源图；另含 1 张排版测试图。不带重复图、答案图或无关题目的图片。
- `README.md`、`AGENTS.md`、`docs/`、`scripts/`、`tests/`：运行说明、约束、打包工具与离线验证。

**视频不用传。源码包排除全部实验视频、音频、`results/`、`dist/`、Git 历史、虚拟环境、缓存和模型权重。** 本地素材目录可保留原始参考数据，它的大小不等于源码包大小。模型服务密钥放仓库外；ASR 权重按服务器联网条件另行准备。

### 一次实验的结果

**本地保留完整输出目录，默认回传评分与运行记录，不传视频、音频或整套抽帧。** 需要回传：

- `REPORT.md`、`summary.json`、`scores.csv`、`manifest.json`、`run_config.json`。
- `generation_inputs.jsonl`、`evaluation_tasks.jsonl`，以及各题 `scores.json`、失败／错误记录。
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
