# 300 题候选集（multisource_pilot_300）改进指南

**对应数据**: `data/prompts/multisource_pilot_300.jsonl`
**对应脚本**: `scripts/build_multisource_pilot.py`
**对应报告**: `data/curated/multisource_pilot_300_report.json`
**基线提交**: `master` 分支 `256b3ac`（扩展到300题）→ `8188b43`（强化多样性与质量门槛）
**分析时间**: 2026-08-28
**当前状态**: `release_ready: false`，仍是 paper candidate，不是可直接发布的benchmark

本文档记录对当前300题候选集的检查结果，以及后续改进建议。目的是让下一轮迭代有明确的检查项和优先级，而不是仅凑够数量。

---

## 改进进展跟踪

| 改进建议 | 状态 | 说明 |
|---|---|---|
| 1. 修复来源比例校验（问题1、7） | ✅ 已实现，PR待合并 | 见下方"改进进展 1"详情 |
| 2. 补齐 economics/history/sports 的 DisciplineGen 候选 | 🔶 部分完成 | sports已修复；economics/history确认为上游数据源硬性瓶颈，见下方"改进进展 2"详情 |
| 3. 解耦 task_type 与数据源 | ✅ 已实现 | 见下方"改进进展 3"详情 |
| 4. 引入难度分层 | ✅ 已实现 | 见下方"改进进展 4"详情 |
| 5. 扩充 pedagogical_archetype 关键词规则 | ⏳ 未开始 | |
| 6. 将 history 硬编码特例改为通用参数 | ⏳ 未开始 | |
| 7. 明确当前数据状态，决定复核路径 | ⏳ 未开始，需同事决策 | 见"五、需要同事决策的开放问题" |

### 改进进展 1：修复来源比例校验（2026-08-29）

**状态**: 代码已实现并本地验证通过，已提交并推送到PR，等待仓库所有者合并。

**改动内容**（`scripts/build_multisource_pilot.py`）：
- 新增模块级常量 `DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE = 0.65`。
- `validate_rows()` 新增 `max_source_share_per_discipline` 参数：对每个学科分别计算 GRADE / DisciplineGen-1M 的占比，超过阈值即记为issue，独立于原有的 `expected_per_source_discipline` 精确匹配检查，不依赖调用方是否传对了这个粗粒度参数。
- report 新增 `source_balance` 字段，列出 `max_source_share_per_discipline` 阈值和具体违规项。
- `build` 和 `validate` 两个CLI子命令都新增 `--max-source-share-per-discipline` 选项（默认0.65），且 `build()` 内部调用 `validate_rows()` 时已正确传入该参数，构建阶段本身就会报出问题，不需要额外记得手动跑一次带正确参数的 `validate`。

**本地验证结果**：

用现有的300题数据分别跑了 `validate` 和完整的 `build --target-per-discipline 30` 两条路径，均正确识别出问题1中发现的三处失衡：

```
GRADE/economics: 67% (超过65%上限)
GRADE/history:   69% (超过65%上限)
GRADE/sports:    73% (超过65%上限)
```

两条路径结果一致，`valid` 字段变为 `false`，退出码为2，确认修复对"验证形同虚设"（问题7）和"来源比例失衡未被检测"（问题1）都生效。

**提交与推送记录**：
- 本地commit: `ea2daa3 Add per-discipline source-share balance check to validate_rows`
- 由于当前账号对 `Geniusyingmanji/video-teacher` 无写入权限，改用fork流程：推送到 `claptrapp222/video-teacher` 的 `fix/source-share-balance-check` 分支，并创建了指向上游 `master` 分支的Pull Request（尚未合并）。

### 改进进展 2：补齐 economics/history/sports 的 DisciplineGen 候选（2026-08-30）

**状态**: sports已修复并验证；economics/history经排查确认为上游数据源硬性瓶颈，暂不可通过采样参数解决。

**排查方法**：

对三个学科分别追踪"为什么DisciplineGen候选不够15条"的根因，而不是直接调大`--per-file`采样量：
1. 用`pyarrow`直接读取DisciplineGen-1M在HuggingFace上的parquet文件元数据，统计每个学科的真实可用行数。
2. 对比脚本`DG_FILES`默认采样文件列表与上游仓库的完整文件清单（通过HuggingFace API获取），检查是否有学科相关文件被遗漏。
3. 对已采样但候选不足的学科，检查`diverse_take()`去重后的实际可用数量，区分"总量不足"和"去重后不足"两种情况。

**sports（已修复）**：

根因是脚本`DG_FILES`列表遗漏了上游仓库里9个sports相关的parquet文件，原来只采样了`edit_sports_data_soccer_formation_dots.parquet`和`..._jerseys.parquet`两个文件，且这两个文件内容高度模板化（只是换阵型编号的"用蓝点/白球衣画出4-3-3阵型"这类文案），去重后仅剩7-8条候选。

修复方式：把以下9个文件加入`scripts/build_multisource_pilot.py`的`DG_FILES`列表：
```
edit_sports_data_chess_opening_2k.parquet
edit_sports_data_go_crucial_move_strong_2k.parquet
edit_sports_data_xiangqi_opening.parquet
edit_sports_data_xiangqi_bestmove_6k.parquet
edit_sports_data_sports_nutrition_classify_grouping_6k.parquet
edit_sports_data_sports_nutrition_high_gi_6k.parquet
edit_sports_data_sports_nutrition_high_protein_6k.parquet
edit_sports_data_sports_nutrition_pie_chart_6k.parquet
edit_sports_data_sports_nutrition_pyramid_6k.parquet
```
并对每个新文件采样40行，合并进`data/sources/disciplinegen/metadata/sampled_rows_expanded.jsonl`（总采样量从1995行增至2355行）。

验证结果：重新跑`build --target-per-discipline 30`后，`DisciplineGen-1M/sports`从8条升至15条，`GRADE/sports`相应回落到15条，达到50/50平衡，此前`source_balance.violations`中的`GRADE/sports 73%超上限`已消失。

**economics（确认为硬性瓶颈，非采样参数问题）**：

用pyarrow直接读取`science_t2i.parquet`的`metadata`列统计学科分布，发现这是DisciplineGen-1M里唯一含economics内容的文件，全库422,442行中标记为"Economy"学科的只有**13行**。查了上游仓库完整文件列表（通过GitHub仓库页面和HuggingFace API），**没有任何专门的economics/finance相关parquet文件**。当前脚本已经把这13行全部采样并选中，无法通过调整采样参数获得更多——这是DisciplineGen-1M数据集本身在economics学科上的覆盖上限。

**history（确认为硬性瓶颈，部分可归因于design tradeoff）**：

`science_t2i.parquet`里标记为"History"的只有8行。另一个专门的`edit_histrory_timeline_pairs.parquet`总共10000行，但抽样500行后模板归类，发现只有约20种不同的任务模板（都是"填补历史事件时间线上缺失的年份/事件名"这一类文案，只是替换具体的历史事件）。`diverse_take()`按Jaccard相似度去重后最多能从中选出15条不完全重复的记录，但脚本里专门有一段逻辑把这个文件的候选数限制在5条以内（`stratified_dg()`中`if discipline == "history": buckets[timeline_name] = buckets.get(timeline_name, [])[:5]`），这是为了避免这个高度模板化的文件占满history学科的名额，属于问题6（history硬编码特例）里已经记录的设计取舍，不是本次要修的bug。即使不做这个限制，把timeline文件的候选数放宽到15条，也只是把"内容多样性不足"的问题从"数量不足"转移成"看起来数量够了但风格高度重复"，不能真正解决多样性问题。

**改动的文件**：
- `scripts/build_multisource_pilot.py`：`DG_FILES`列表新增9个sports文件（含注释说明原因）。
- `data/sources/disciplinegen/metadata/sampled_rows_expanded.jsonl`：合并了新采样的360行sports候选，总量从1995行增至2355行。
- `data/prompts/multisource_pilot_300.jsonl`、`data/curated/multisource_pilot_300_report.json`：用扩充后的候选池重新跑了`build --target-per-discipline 30`并覆盖生成。

**重新构建后的来源占比变化**：

| 学科 | 修复前 GRADE/DG | 修复后 GRADE/DG | 是否仍超65%上限 |
|---|---|---|---|
| economics | 20/10 (67%) | 20/10 (67%) | 是（硬性瓶颈） |
| history | 20/9 (69%) | 20/9 (69%) | 是（硬性瓶颈） |
| sports | 22/8 (73%) | 15/15 (50%) | 否（已修复） |

**遗留事项**：
- economics和history仍需要人工介入才能真正补齐：可参考现有`disciplinegen_math_replacements.jsonl`、`disciplinegen_sports_replacements.jsonl`的做法，用DisciplineGen-1M官方渲染器脚本手动生成新的economics/history样本，或者接受这两门学科在DisciplineGen来源上的天然稀缺，改为在report里显式标注为"已知数据源限制"而非"未处理的失衡"。
- 需要决定：如果经过人工确认这两个学科的DisciplineGen补充候选确实无法在合理成本内获得，是否要把`--max-source-share-per-discipline`的65%阈值对这两个学科单独放宽，还是保留报错让每次构建都能看到这个已知限制的提醒。
- 本次未提交到git，仍是本地工作区改动，需要与改进1的PR合并流程一并考虑。

### 改进进展 3：解耦 task_type 与数据源（2026-08-30）

**状态**: 已实现并本地验证通过。

**问题回顾**：

`task_type`（`explanation` 讲解型 / `problem_solving` 问题求解型）本应是一个独立的教学维度，但原实现里它完全由数据来源决定：
- `grade_to_prompt()` 中硬编码 `"task_type": "problem_solving"`，即所有GRADE记录必然是问题求解；
- `dg_to_prompt()` 中按文件名是否以 `edit_` 开头判断，而DisciplineGen绝大多数文件不是该前缀，因此几乎全部落入 `explanation`。

结果是这个字段实质上成了"数据来源"的代名词，无法支撑"不同任务类型下模型表现如何差异"这类分析——因为任何按task_type的切分，本质上都在切分数据源。

**解决思路**：

改为基于源标注文本的内容来判断，而不是看记录来自哪个文件。核心区分逻辑是：**这个任务是在已有素材上做操作/推导，还是从零创建一个讲解用的图示**。

新增三组正则模式（`scripts/build_multisource_pilot.py`）：
- `SOLVE_VERB_PATTERN`：作用于既有素材或需要推导出答案的动词，如 complete、fill、connect、calculate、mark、highlight、rotate、missing 等。这类动词都预设了一个"给定的初始状态"需要被改变或解决。
- `EXPLAIN_VERB_PATTERN`：从零创建讲解性素材的动词，如 generate、draw、create、illustrate、depict。这里刻意**只保留动词、排除 diagram/figure 这类名词**——因为两种任务类型都会频繁提到这些名词，把它们计入会稀释信号（这是第一版规则失败的原因，详见下方）。
- `EXISTING_ARTIFACT_PATTERN`：显式指向已提供素材的短语，如 "in the diagram"、"shown in"、"provided"、"starting from"。

判定优先级：若同时出现操作类动词**且**指向已有素材，直接判为 `problem_solving`（例如 "draw the missing curve in the diagram" 虽然有 draw，但实质是在补全已有图表，属于问题求解）；否则比较两类动词的出现次数，多者胜出。

**一次失败的尝试（记录下来供参考）**：

第一版规则把 diagram、schematic、labeled 这类名词也算作"讲解信号"，结果300条里有45条GRADE记录判定打平无法归类，且像 "Please complete the chemical reaction equation in the diagram"、"Please color the organ green in the diagram" 这类明显的操作型任务被误判为讲解型——因为句中的 "diagram" 把天平拉向了讲解一侧。修正方式就是把名词从判定信号里剔除，只看动词表达的**意图**，不看动作作用的**载体**。

**验证结果**：

重新构建300题后，两个数据源内部都出现了两种任务类型的合理分布：

| 数据源 | 修复前 | 修复后 |
|---|---|---|
| GRADE | 161条全部 problem_solving（100%绑定） | 82条 problem_solving / 79条 explanation |
| DisciplineGen-1M | 114条 explanation / 25条 problem_solving | 104条 explanation / 35条 problem_solving |
| 总计 | 186 / 114 | 117 problem_solving / 183 explanation |

抽样检查判定结果符合直觉：
- 判为 `problem_solving`：「complete the chemical reaction equation in the diagram by filling in its products」「connect the illustrations of each stage in the correct order」
- 判为 `explanation`：「Generate a labeled diagram of an animal cell, including cell membrane, cytoplasm, nucleus...」「Generate a food web diagram illustrating the relationships among a producer, a primary consumer...」

同时 `scripts/validate_prompt_jsonl.py` 校验300条全部通过（退出码0），且每个学科内部都同时含有两种任务类型，不再出现某个学科被单一任务类型垄断的情况。

**附带改动**：

验证报告新增 `task_type_balance` 字段，记录任务类型的总体分布和按数据源的交叉分布。这样以后每次构建都能直接从报告里看出来task_type是否又退化成了数据源的代名词（如果某个数据源只输出一种任务类型，就说明解耦失效了）。

**遗留事项**：
- 当前规则是基于关键词的启发式判断，覆盖了本批300条数据的主要模式，但没有人工逐条核对过每一条的判定是否准确。改进文档"五、需要同事决策的开放问题"里第1条提到的"是否需要人工抽样检查边界样本"仍然有效，建议在正式用于论文前抽样20-30条人工确认。
- 总体分布现在是 183 explanation / 117 problem_solving，仍不是严格的1:1。这是内容本身决定的（DisciplineGen确实以生成类标注为主），没有强行调平，因为人为凑比例会破坏"判定基于内容"这个前提。

### 改进进展 4：引入难度分层（2026-08-30）

**状态**: 已实现并本地验证通过。

**问题回顾**：

300条数据的 `difficulty` 字段全部硬编码为 `"undergrad"`，没有任何区分度。对照仓库里早期的数据集（`pilot_v0_2` 是 low/medium/high 三档，`high_difficulty_addon` 是 professional 单档），这批300题实质上丢掉了难度维度，无法支撑"模型在不同难度题目上表现如何变化"这类分析。

**信号探查过程**：

先统计了数据里有哪些可用作难度判断的信号，结果决定了最终方案：

| 候选信号 | 实测结果 | 是否可用 |
|---|---|---|
| 源文本长度 | 26 - 800 字符，四分位为 113 / 209 / 391 | ✅ 主信号，区分度好 |
| 学科高阶术语命中数 | 中位数 0，最多 4 | ⚠️ 偏稀疏，作辅助调整 |
| 基础动词（label/name/color）命中数 | 中位数 0，最多 4 | ⚠️ 作降级信号 |
| `expected_narrative_order` 节拍数 | **全部是 4** | ❌ 无区分度 |
| `expected_concepts` 概念数 | **全部是 3** | ❌ 无区分度 |

后两项之所以没区分度，是因为它们由 `archetype_spec()` 的固定模板生成，不随源内容变化，所以不能用来判断难度。

**实现方案**（`scripts/build_multisource_pilot.py`）：

新增 `infer_difficulty()`，采用打分制：
- **长度**（主信号）：≥400字符 +2分，≥180字符 +1分。依据是源规格越长，意味着要在5秒视频里满足的约束越多。
- **高阶术语**（`ADVANCED_TERM_PATTERN`）：命中≥2个 +2分，命中1个 +1分。词表覆盖 derive/theorem/equilibrium/mechanism/meiosis/allele/enzyme/asymptotic/elasticity 等预设需要先修课程的概念。
- **基础动词**（`BASIC_TERM_PATTERN`）：命中≥2个且无高阶术语时 -1分。纯粹的"标注/命名/涂色"属于记忆层级任务。
- 分档：≥3分 → `professional`，≥1分 → `undergrad`，否则 → `k12`。

规则是纯确定性的，重新构建可复现。

**验证结果**：

| 难度 | 条数 | GRADE | DisciplineGen-1M |
|---|---|---|---|
| k12 | 124 | 98 | 26 |
| undergrad | 136 | 43 | 93 |
| professional | 40 | 20 | 20 |

三档都有实质数量，且两个数据源内部都覆盖了全部三档——这点很重要，说明难度不像修复前的 `task_type` 那样退化成数据源的代名词。

抽样检查判定合理性：
- `k12`：「illustrate the food chain relationships among the five organisms」「connect the illustrations of each stage of a butterfly's life cycle」
- `undergrad`：「Generate a food web diagram for an ecosystem with five species labeled A-E」
- `professional`：「Generate a diagram of a cell in meiosis II showing two chromosomes, one with alleles A and a」

`scripts/validate_prompt_jsonl.py` 校验300条全部通过（退出码0），且每个学科内部都同时含有多个难度档位。

**附带改动**：

验证报告新增 `difficulty_balance` 字段，记录难度的总体分布和按数据源的交叉分布，便于以后每次构建都能确认难度维度没有退化成单一档位。

**已知局限（如实记录）**：

启发式判定存在边界误判。例如「Generate a labeled diagram of a bird egg structure, showing and labeling the following parts...」被判为 `professional`，主要是因为文本较长加上"labeled"重复出现触发了长度加分，但这道题实际上更接近 `k12`/`undergrad` 的记忆层级。这类误差是基于关键词的方案固有的局限，没有通过硬编码特例去纠正个别样本，因为那会破坏规则的可复现性和一致性。

**遗留事项**：
- 建议人工抽样20-30条核对难度判定，尤其是 `professional` 这一档（只有40条，误判影响相对更大）。这与"五、需要同事决策的开放问题"第2条（难度分层用自动启发式还是人工标注校准）直接相关。
- 当前分档阈值（400/180字符、术语命中数）是基于本批300条数据的分布拟合的，如果后续数据规模或来源变化，阈值可能需要重新校准。

---



## 一、现状快照

依据 `git show 8188b43:data/curated/multisource_pilot_300_report.json` 的实际内容：

| 维度 | 数值 |
|---|---|
| 总条数 | 300 |
| 来源分布 | GRADE 168 / DisciplineGen-1M 132 |
| 学科数 | 10（每学科29-31条，基本均衡） |
| difficulty 分布 | 100% `undergrad` |
| task_type 分布 | `problem_solving` 186 / `explanation` 114 |
| curation 状态 | `draft_needs_subject_review` 168、`draft_needs_visual_review` 128、`reviewed_release_ready` 4 |
| license | GRADE 168条 `unverified`；DisciplineGen 132条 `verified_redistributable`（CC BY 4.0） |
| 最大 archetype 占比 | 30.33%（`quantitative_reasoning`） |
| 自动化 paper_candidate_gate | `automated_pass: true` |

自动化门槛（archetype≥8个、单一archetype≤35%、单一叙事模板≤5次重复、近似重复对=0）目前全部通过，但这只是"没有踩到红线"，不代表数据结构本身是均衡、可比的。

---

## 二、发现的问题

### 问题 1：学科内部的来源比例不均衡，且未被校验（优先级：高）

构建命令只约束了"每学科合计约30条"，没有约束"每学科内 GRADE / DisciplineGen 各占多少"。实际按学科拆分后：

| 学科 | GRADE | DisciplineGen-1M |
|---|---|---|
| economics | 20 | 10 |
| history | 20 | 9 |
| sports | 22 | 8 |
| 其余 7 个学科 | 15 | 15 |

`economics`、`history`、`sports` 三门学科明显偏向 GRADE 的"图表编辑"任务风格，其他学科则均衡。这会导致学科之间的任务性质不可比，影响后续用这批数据做跨学科评测的结论。

`validate_rows()` 函数当前只检查 `expected_per_source_discipline` 这一个粗粒度参数（`build --target-per-discipline 30` 模式下实际没有正确传入约束），完全没有检测这个来源比例失衡，属于验证逻辑的缺口。

### 问题 2：task_type 与数据源强耦合，不是独立设计的维度（优先级：高）

- `grade_to_prompt()` 中 `task_type` 被硬编码为 `"problem_solving"`（对应GRADE的"图表编辑"任务）。
- `dg_to_prompt()` 中 `task_type` 由文件名是否以 `edit_` 开头决定，DisciplineGen 里绝大多数文件不是 `edit_` 前缀，因此几乎全部落在 `"explanation"`。

结果是 186:114 的 task_type 分布本质上是数据源属性的副产品，不是刻意设计的任务类型均衡。如果后续要分析"讲解类"和"问题求解类"任务上模型表现的差异，这个耦合会让结果被数据源本身的特性主导。

### 问题 3：difficulty 字段没有区分度（优先级：中）

300条全部是 `"undergrad"`。对照仓库里早期的 `pilot_v0_1` / `pilot_v0_2` / `high_difficulty_addon`，那些数据集明确设计了 k12/undergrad/professional/graduate 四层难度。这300条实质上退化成单一难度，削弱了本该有的难度梯度价值，也无法支撑"不同难度下模型表现如何变化"这类分析。

### 问题 4：pedagogical_archetype 分布依然集中，兜底分类占比高（优先级：中）

report 中的分布：

```
quantitative_reasoning   91   (30.3%)
visual_transformation    84   (28.0%)
temporal_sequence        40
spatial_reasoning        30
labeling                 23
classification           12
causal_mechanism         11
comparison                4
legacy_reviewed           4
evidence_inference        1
```

两个最大类别合计占58.3%，`comparison` 和 `evidence_inference` 几乎是摆设。`visual_transformation` 是 `pedagogical_archetype()` 函数里"没有匹配任何正则规则就归入"的兜底类别（见 `scripts/build_multisource_pilot.py` 中 `pedagogical_archetype()` 的实现），高占比说明关键词规则覆盖率不足，很多样本本质上没有被正确归类。自动化门槛设的"单一archetype ≤35%"只是刚好没踩线，不代表分布真正均衡。

### 问题 5：数据整体仍是草稿，未完成复核（优先级：高，属于流程风险而非代码bug）

- 168条GRADE数据标记为 `draft_needs_subject_review`：需要学科专家核实图表编辑任务的事实正确性。
- 128条DisciplineGen数据标记为 `draft_needs_visual_review`：因为其嵌入图像未下载，仅凭文字annotation无法确认视觉呈现是否合理。
- 仅4条标记为 `reviewed_release_ready`。
- GRADE的许可状态仍是 `unverified`（HuggingFace页面无明确的redistribution条款），这168条如果要发布或对外分发，许可风险尚未解除。

这一状态是数据管线设计时就已知的阶段性结果，写在这里是为了确保后续使用者（尤其做正式评测或投稿）不会误以为"扩到300条+加了多样性门槛"就等于"数据已经可用"。

### 问题 6：history 学科的时间线数量上限是硬编码特例，缺乏通用性（优先级：低，技术债）

`stratified_dg()` 里有这样一段专门逻辑：只对 `history` 学科生效，把某个模板化程度过高的上游文件（历史时间线编辑任务）截断到固定的5条。这是为了压低该文件在history学科候选池里的占比。如果之后在其他学科也发现类似"某个上游文件模板化程度过高、需要限流"的情况，还需要再加一个专门的if分支，脚本会越改越难维护，且这类特例容易被后人误删或遗漏。

### 问题 7：`expected_per_source_discipline` 校验形同虚设（优先级：高，验证逻辑缺口）

`validate_rows(rows, expected_per_source_discipline=...)` 在 `build --target-per-discipline 30` 场景下，实际传入的仍是默认的 `per_source_discipline=5`，与真实目标（每源每学科15条左右）不匹配，导致这项校验既没有报错，也没有真正起到约束作用。问题1中的来源比例失衡之所以没被自动发现，根源就在这里。

---

## 三、改进建议（建议优先级顺序）

### 1. 修复来源比例校验（对应问题1、7）

在 `validate_rows()` 中新增一项检查：对每个 `(discipline, source.dataset)` 组合计算占比，设定一个合理的上下限（例如每学科内单一来源占比不超过65%，或直接检查是否偏离目标配比超过一定阈值），并让 `build` 命令按`--target-per-discipline`的实际值传入正确的期望值，而不是沿用默认的 `per_source_discipline`。

### 2. 补齐 economics / history / sports 的 DisciplineGen 候选（对应问题1）

检查 `data/sources/disciplinegen/metadata/sampled_rows_expanded.jsonl` 中这三门学科的可用样本量是否足够15条。若不足，需要扩大 `sample-disciplinegen --per-file` 的采样规模，或在 `data/curated/` 下补充新的 replacement 文件（参考现有的 `disciplinegen_math_replacements.jsonl`、`disciplinegen_sports_replacements.jsonl` 的做法）。

### 3. 解耦 task_type 与数据源（对应问题2）

不要让 `task_type` 完全由函数（GRADE固定问题求解、DisciplineGen固定讲解）决定。可以引入基于annotation内容的判断规则（比如annotation中包含"计算/推导/编辑/修改"等信号时归为 `problem_solving`，否则归为 `explanation`），让两种任务类型在两个数据源内都有一定比例，减少数据源对任务类型分布的主导性。

### 4. 引入难度分层（对应问题3）

参考 `pilot_v0_1`/`pilot_v0_2` 已有的difficulty设计思路，为300条数据设计一套可复现的分层规则（例如基于source_text长度、涉及概念数量、是否需要多步推理等信号），把当前全量的`undergrad`拆分为至少k12/undergrad/professional三档，避免难度维度失去区分度。

### 5. 扩充 pedagogical_archetype 的关键词规则（对应问题4）

审查 `pedagogical_archetype()` 里各archetype对应的正则规则，针对当前落入`visual_transformation`兜底类别的84条样本抽样检查，看是否能识别出新的规律并补充规则；同时专门为`comparison`、`evidence_inference`这类稀缺archetype在两个数据源里查找更多候选，提升其占比。

### 6. 将 history 的硬编码特例改为通用参数（对应问题6）

把"限制单个上游文件在某学科候选池中的最大数量/占比"做成 `stratified_dg()` 的通用参数（例如 `--max-share-per-source-file`），而不是针对history单独写死判断，方便未来其他学科出现同类问题时复用。

### 7. 明确当前数据状态，决定复核路径（对应问题5）

在推进任何正式评测或论文引用之前，需要决定：
- 是否接受当前draft状态直接用于内部实验（不对外发布）；
- 还是先安排学科专家对168条GRADE数据做`draft_needs_subject_review`复核；
- DisciplineGen的128条`draft_needs_visual_review`是否需要下载对应图像做视觉核实；
- GRADE数据的redistribution许可条款是否需要联系上游确认，否则不能对外分发这168条及其图像资产。

---

## 四、验证方式

每完成一项改进后，建议执行以下命令确认修复效果：

```bash
python scripts/build_multisource_pilot.py build --target-per-discipline 30 \
  --out data/prompts/multisource_pilot_300.jsonl \
  --report data/curated/multisource_pilot_300_report.json

python scripts/build_multisource_pilot.py validate \
  --input data/prompts/multisource_pilot_300.jsonl \
  --per-source-discipline 15

python scripts/validate_prompt_jsonl.py data/prompts/multisource_pilot_300.jsonl
```

检查生成的 report JSON，确认：
- `by_source_discipline` 中每个学科的两个来源占比接近预期（问题1、2）；
- `diversity.pedagogical_archetypes` 中兜底类别占比下降、稀缺类别占比上升（问题4）；
- `paper_candidate_gate.automated_pass` 仍为 `true`，且新增的来源比例检查也通过。

---

## 五、需要同事决策的开放问题

1. task_type 的判定规则改为基于内容后，是否需要重新人工抽样检查一批边界样本？
2. 难度分层规则希望用自动化启发式（如文本长度）还是需要人工标注一部分样本作为校准基准？
3. GRADE 168条的许可确认预计能否在近期完成？如果不能，这批数据是否应该先排除在"paper candidate"范围之外，只保留132条DisciplineGen数据对外展示？



