# 2026-08-30 工作总结

**仓库**: https://github.com/Geniusyingmanji/video-teacher
**本地路径**: `D:\ai_teacher\video-teacher-prompts`
**任务背景**: 同事把 `video-teacher` 项目的教学视频prompt数据集扩展到了300题（在GitHub `master` 分支上，尚未合并到 `main`），请求帮忙检查质量并改进。

---

## 一、整体时间线

1. 下载/同步仓库最新内容到 `D:\ai_teacher`
2. 检查300题数据集，撰写问题诊断和改进建议文档
3. 撰写脚本术语说明文档，解释数据结构和关键函数含义
4. 实际修复"问题1/7：来源比例校验缺失"
5. 实际修复"问题2（sports部分）：DisciplineGen候选不足"
6. 排查确认economics/history的候选不足是数据源本身的硬性瓶颈
7. 实际修复"问题3：task_type与数据源强绑定"
8. 实际修复"问题4：difficulty无难度分层"
9. 实际修复"问题5：pedagogical_archetype兜底分类占比过高"
10. 实际修复"问题6：history硬编码特例改为通用参数"
11. 通过fork+PR的方式将全部六项代码修复提交到GitHub

改进文档里的7项建议中，6项属于代码改进，已全部完成并验证；第7项是需要人工决策的流程事项，不属于代码问题。

---

## 二、仓库同步与环境问题排查

### 1. 分支现状确认

`Geniusyingmanji/video-teacher` 仓库有 `main` 和 `master` 两个分支，同事新增的300题相关改动（两个提交：扩展到300题、强化多样性与质量门槛）只存在于 `master` 分支，还没合并到 `main`。为了能实际读取、测试这批数据和对应的构建脚本，把本地 `main` 分支快进合并（fast-forward，无冲突、可撤销）到了 `origin/master`，这样本地工作区就同时具备了完整的300题数据和脚本。

### 2. Git代理故障修复

任务过程中一度出现 `git fetch` 无法连接GitHub的问题，排查发现是本地git全局配置里指向 `http://127.0.0.1:7890` 的代理已经失效（代理服务没在运行）。移除了这条全局代理配置后，git网络操作恢复正常。

**影响提醒**：这是全局git配置改动，如果这台机器上其他需要该代理的git操作或工具依赖这个设置，可能需要重新评估是否要恢复。

### 3. 权限问题与fork流程

尝试直接推送修复到 `origin`（即 `Geniusyingmanji/video-teacher`）时被拒绝（403 Permission denied），当前登录账号 `claptrapp222` 对该仓库没有写入权限。改为标准的开源协作流程：

- 在GitHub上fork了该仓库到 `claptrapp222/video-teacher`
- 本地新增一个名为 `myfork` 的git remote指向这个fork
- 后续所有代码修复都推送到 `myfork` 的 `fix/source-share-balance-check` 分支
- 创建了一个指向上游 `Geniusyingmanji/video-teacher` 的 `master` 分支的Pull Request，目前处于等待仓库所有者审核合并的状态

---

## 三、生成的两份分析文档

### 1. `docs/MULTISOURCE_PILOT_300_IMPROVEMENT_PLAN.md`（改进指南）

对300题数据集（`data/prompts/multisource_pilot_300.jsonl`）做了系统性检查，发现并记录了7个问题：

| 编号 | 问题 | 优先级 |
|---|---|---|
| 1 | 学科内GRADE/DisciplineGen两个来源的比例严重不均衡（economics、history、sports三门学科GRADE占比超过65-73%），且没有被任何校验发现 | 高 |
| 2 | task_type（讲解型/问题求解型）完全由数据源决定，不是独立设计的教学维度 | 高 |
| 3 | difficulty字段300条全部是"undergrad"，没有难度梯度 | 中 |
| 4 | pedagogical_archetype（教学操作类型）分布集中，两个类别占了58%，其中一个是"没识别出规律"的兜底分类 | 中 |
| 5 | 数据整体仍是草稿状态，168条GRADE数据待学科专家复核，128条DisciplineGen数据待视觉复核，许可状态未确认 | 高（流程风险） |
| 6 | history学科有一段只对该学科生效的硬编码限流逻辑，缺乏通用性 | 低（技术债） |
| 7 | 现有的校验函数`validate_rows()`在实际构建场景下没有正确接收比对参数，导致问题1的失衡从未被自动检测出来 | 高（验证逻辑缺口） |

文档针对每个问题给出了对应的改进建议，并设置了"改进进展跟踪"表格，记录每项建议的完成状态。

### 2. `docs/MULTISOURCE_PILOT_300_GLOSSARY.md`（术语说明）

针对构建脚本 `scripts/build_multisource_pilot.py` 里的关键概念写了详细解释，包括：两个上游数据源（GRADE、DisciplineGen-1M）的结构、生成的prompt记录里每个字段的含义、`task_type`的判定逻辑、`grade_to_prompt`/`dg_to_prompt`两个核心转换函数、`pedagogical_archetype`教学操作类型的分类规则、以及验证报告JSON里各字段的含义。这份文档是为了让同事和后续维护者能看懂脚本在做什么，不涉及问题诊断。

---

## 四、实际完成的代码修复

### 修复1：来源比例校验缺失（对应改进建议1、7）

**问题**：`validate_rows()`函数原本只检查一个粗粒度参数`expected_per_source_discipline`，而这个参数在实际构建命令（`build --target-per-discipline 30`）中根本没有被正确传入，导致300题里economics/history/sports三门学科的来源比例严重失衡（GRADE占比67-73%）从未被自动检测到。

**修复内容**（`scripts/build_multisource_pilot.py`）：
- 新增常量`DEFAULT_MAX_SOURCE_SHARE_PER_DISCIPLINE = 0.65`
- `validate_rows()`新增独立的比例检查：对每个学科分别计算两个来源各自占比，超过65%就报为issue，这个检查不依赖任何外部参数是否传对
- 验证报告新增`source_balance`字段，列出阈值和具体违规项
- `build`和`validate`两个命令行子命令都新增`--max-source-share-per-discipline`选项

**验证结果**：用实际数据跑了`validate`和完整`build`两条路径，都正确识别出了三处失衡（economics 67%、history 69%、sports 73%），确认修复生效。

### 修复2：sports学科候选不足（对应改进建议2的一部分）

**排查过程**：没有直接调大采样参数，而是先定位根因——用pyarrow直接读取DisciplineGen-1M数据集在HuggingFace上的parquet文件，对比脚本里实际使用的采样文件列表和上游仓库的完整文件清单，发现脚本遗漏了9个sports相关的文件，原来只采样了两个高度模板化的"阵型图"文件（只是换阵型编号的文案，去重后只剩7-8条不重复候选）。

**修复内容**：把遗漏的9个文件（象棋开局、围棋、中国象棋、运动营养分类等）加入采样列表，重新采样后合并进候选数据文件，候选总量从1995行增加到2355行。

**验证结果**：重新构建300题后，sports学科的DisciplineGen候选从7-8条提升到15条，GRADE/DisciplineGen比例恢复到50/50平衡，此前73%超阈值的违规已消失。

### 排查结论：economics和history的候选不足是数据源本身的硬性瓶颈


同样用直接读取上游数据的方式排查了这两门学科：
- **economics**：整个DisciplineGen-1M数据集里，唯一含economics内容的文件总共42万多行里只有13行被标记为该学科，且没有专门的economics相关文件存在。当前已经把这13行全部用上，无法通过任何采样参数获得更多。
- **history**：一个专门文件有1万行，但抽样后发现只有约20种不同的任务模板（本质是同一类"填补时间线缺失年份"的任务换不同历史事件）。脚本里已经有意把这个文件的候选数限制在5条以内以避免模板化内容占满名额，这是此前已知的设计取舍，不是本次要修的bug。

这两项结论也记录进了改进文档，标注为"上游数据源硬性瓶颈"，和sports的"可修复"情况区分开，避免后续被误认为是可以简单调参数解决的问题。

### 修复3：task_type 与数据源解耦（对应改进建议3）

**问题**：`task_type`（讲解型/问题求解型）本该是独立的教学维度，但原实现完全由数据来源决定——所有GRADE记录被硬编码成 `problem_solving`，所有非 `edit_` 前缀的DisciplineGen记录自动变成 `explanation`。这导致按task_type做任何分析，实质上都只是在按数据源分组。

**修复内容**：改为读源标注文本判断，核心区分点是"在已有素材上操作"还是"从零画一张讲解图"。新增三组正则：操作/推导类动词（complete、calculate、mark、rotate、missing 等）、创建类动词（generate、draw、illustrate 等）、指向已有素材的短语（"in the diagram"、"provided"、"starting from"）。若操作类动词与已有素材同时出现，判为问题求解。

**中途一次失败尝试**：第一版把 diagram、schematic 这类名词也算作讲解信号，结果45条判定打平，且"complete the chemical reaction equation in the diagram"这种明显的操作型任务被误判成讲解型。修正方式是只看动词表达的**意图**，不看动作作用的**载体**。

**验证结果**：

| 数据源 | 修复前 | 修复后 |
|---|---|---|
| GRADE | 161条全是problem_solving（100%绑定） | 82条problem_solving / 79条explanation |
| DisciplineGen-1M | 114条explanation / 25条problem_solving | 104条explanation / 35条problem_solving |

两个数据源内部都有了两种任务类型，每个学科内部也都同时包含两类。报告新增 `task_type_balance` 字段，便于后续发现该字段是否又退化成数据源代名词。

### 修复4：引入难度分层（对应改进建议4）

**问题**：300条数据的 `difficulty` 全部硬编码为 `undergrad`，难度维度形同虚设。

**先做信号探查（这步决定了方案）**：把所有可能的难度信号统计了一遍——源文本长度26到800字符、四分位清晰（可用）；高阶术语命中中位数0（偏稀疏，只能作辅助）；而 `expected_narrative_order` 节拍数**全部是4**、`expected_concepts` 概念数**全部是3**（完全无区分度，因为它们由固定模板生成、不随源内容变化）。这个发现避免了走弯路。

**修复内容**：`infer_difficulty()` 打分制——长度≥400字符+2分、≥180字符+1分；高阶术语（derive/theorem/meiosis/allele/elasticity 等）命中≥2个+2分、1个+1分；纯标注类动词且无高阶术语-1分。≥3分归 `professional`，≥1分归 `undergrad`，否则 `k12`。规则确定性，可复现。

**验证结果**：

| 难度 | 条数 | GRADE | DisciplineGen |
|---|---|---|---|
| k12 | 124 | 98 | 26 |
| undergrad | 136 | 43 | 93 |
| professional | 40 | 20 | 20 |

三档都有实质数量，两个数据源都覆盖全部三档。报告新增 `difficulty_balance` 字段。

**如实记录的局限**：存在边界误判，例如"bird egg structure, showing and labeling the following parts"被判成 `professional`（长文本加"labeled"重复触发加分），实际更接近记忆层级。没有加硬编码特例去纠正个别样本，因为那会破坏规则一致性和可复现性。

### 修复5：扩充 pedagogical_archetype 关键词规则（对应改进建议5）

**问题**：`visual_transformation` 占87条（29%），但它不是真正识别出的类型，而是"所有规则都没命中"的兜底桶；同时 `evidence_inference` 只1条、`comparison` 只7条。

**排查方式**：没有凭直觉加词，而是把87条兜底样本按学科拆开逐条读源文本。发现它们高度集中在四类有明确特征的任务上：music 25条全是"按指定调号/拍号生成乐谱"、sports 15条是棋类走法与阵型、chemistry 13条是分子结构式、computer_science 11条是堆/链表/逻辑门构建。

**修复内容**：新增三个archetype —— `symbolic_notation`（记谱）、`structure_construction`（结构构建）、`strategy_decision`（策略决策），放在规则表**最前面**（因为判定是"首个命中即返回"，特征明确的规则必须先于宽泛规则）。同时补齐三者在 `archetype_spec()` 里的模板，否则构建会直接 KeyError。

**中途抓到的严重误判**：第一版规则过宽，抽样立刻暴露问题——`symbolic_notation` 命中38条但只24条是music，因为 `major`/`minor`/`staff` 是常见英文词，"showing the **major** countries"（政治地图）、"the **major** distribution regions"（林地分布）都被误吞；`strategy_decision` 命中29条但只21条是sports，`formation`/`play` 太泛，把"the **formation** process of Chinook winds"（地理）、"**force** analysis diagram"（物理）都算进来。

修正方式不是删词，而是加上下文约束：`major`/`minor` 改成**前瞻断言**，只在后面30字符内出现 key/scale/chord/time 时才算命中（"C major, 4/4 time"算，"major countries"不算）；阵型收紧为 `\d-\d-\d formation` 必须是数字格式。修正后三类的学科归属完全干净。

**验证结果**：

| 指标 | 改进前 | 改进后 |
|---|---|---|
| 兜底类别占比 | 87条（29.0%） | **31条（10.3%）** |
| 活跃archetype数 | 9个 | **12个** |
| 最大类别占比 | 30.0% | 28.3% |

**遗留问题**：`evidence_inference`(1条) 和 `comparison`(4条) 仍稀缺——这轮解决的是"兜底桶太大"，没解决这两类绝对数量不足，因为上游数据本来就少有这类任务。剩余31条兜底仍有细分空间，但边际收益下降且每加规则都有新误判风险，停在10.3%这个合理水平，没有为刷数字硬加规则。

### 修复6：将 history 硬编码特例改为通用参数（对应改进建议6）

**问题**：`stratified_dg()` 里有段只对 history 生效的硬编码限流（把那个1万行但只有约20种模板的时间线文件砍到5条）。逻辑合理但写成了"学科名+文件名"双写死的特例，以后别的学科遇到同类问题就得再加if分支。

**动手前先探查，这步否决了最初方案**：统计各学科实际使用的上游文件数，发现 sports 有11个、mathematics/chemistry/computer_science/history 各2个，但 **physics/biology/geography/economics/music 各只有1个**。如果无条件对所有学科限流，这5个单文件学科的候选会被白砍一刀，纯自伤。所以通用规则必须附带前提：**只在学科有多个来源文件时才限流**。

**踩了一个真实回退（重要记录）**：第一版直接把原来的固定值5提为通用默认值。构建后对比文件哈希发现输出变了，进一步核对确认是真实回退，不是无害差异——

| 学科 | 改动前 | 第一版实现 |
|---|---|---|
| chemistry | 15 | **10** |
| computer_science | 15 | **7** |
| history | 9 | **7** |

根因是**5这个数字原本为history单个文件量身定制**，当成通用默认值后，多文件学科的配额被切成"文件数×5"，反而凑不满15条。

修正方式：把上限从"固定条数"改为"占该学科配额的比例"（`--max-source-file-share`，默认0.5）。限流的本意是"不让单个文件垄断配额"，不是"砍到某个固定数字"，所以上限应随配额缩放。

**验证结果**：chemistry、computer_science、sports 全部恢复15条无回退，单文件学科未被误伤，history 从9升到10（按比例算出的上限15比原来的5宽松，多取到一条非模板化记录）。参数可控性也验证过：`--max-source-file-share 0` 关闭限流后 history 升到15，正是模板文件占满名额的情况，说明机制真在起作用。代码里已无 `discipline == "history"` 特例分支。

---

### 六项改进完成后的整体质量核对

每项改进完成后都跑了完整构建加校验，最终状态：

- `paper_candidate_gate.automated_pass`: true
- 源文本近似重复对（Jaccard 0.72）: 0
- `unique_narrative_plans`: 300（无叙事模板重复）
- 最大 archetype 占比: 28%
- `scripts/validate_prompt_jsonl.py`: 300条全部通过（退出码0）
- 仍在报的两项 `source_balance` 违规（GRADE/economics 67%、GRADE/history 69%）是已确认的上游数据源硬性瓶颈，不是未处理的缺陷

---

## 五、Git提交记录

本地`main`分支上新增了六个提交，均已推送到fork仓库的`fix/source-share-balance-check`分支：

1. `ea2daa3` — Add per-discipline source-share balance check to validate_rows（修复1）
2. `10fc0bc` — Widen sports DisciplineGen sampling; add improvement docs（修复2 + 两份文档）
3. `d54b9fb` — Infer task_type from source text instead of dataset origin（修复3）
4. `9c7a73d` — Derive difficulty tiers from source-text complexity（修复4）
5. `2fd5f37` — Add notation, structure, and strategy archetypes to cut fallback rate（修复5）
6. `8259cdf` — Generalize per-source-file cap; drop history special case（修复6）

对应的Pull Request指向上游`Geniusyingmanji/video-teacher`仓库的`master`分支，目前处于待审核合并状态。

---

## 六、尚未开始的工作（供明天参考）

改进文档里记录的7项改进建议中，**6项代码改进已全部完成**。剩余工作都不是代码问题，而是需要人工判断或决策的事项：

**需要同事拍板的流程决策（改进建议7）**：
- 168条GRADE数据的学科专家复核（`draft_needs_subject_review`）
- 128条DisciplineGen数据的视觉复核（`draft_needs_visual_review`，需先下载嵌入图像）
- GRADE数据的redistribution许可确认，否则这168条不能对外分发

**需要人工抽样核对的质量保证工作**：
- 修复3的 `task_type` 判定、修复4的 `difficulty` 分档、修复5的 `archetype` 归类都是关键词启发式规则，建议各抽样20-30条人工确认准确性，尤其是 `professional` 难度档（只有40条，误判影响相对更大）
- 这些判定涉及学科内容的正确性，需要懂相应学科的人来核，无法靠自动化替代

**数据源本身的限制（已确认，非缺陷）**：
- economics（上游全库仅13条可用）和 history（另一来源高度模板化）的DisciplineGen候选不足是硬性瓶颈，需要决策：是用官方渲染器脚本手动生成新样本，还是接受现状并在报告里显式标注为"已知数据源限制"

**可选的后续优化**：
- `evidence_inference`（1条）和 `comparison`（4条）两类archetype数量仍然稀缺，要补充需针对性地去上游筛选或生成
- 剩余31条兜底archetype样本仍有细分空间，但建议配合人工标注校准，而不是继续纯靠关键词硬加规则

---

## 七、涉及的文件清单

**新建的文档**（本次工作产出）：
- `video-teacher-prompts/docs/MULTISOURCE_PILOT_300_IMPROVEMENT_PLAN.md`
- `video-teacher-prompts/docs/MULTISOURCE_PILOT_300_GLOSSARY.md`

**修改的代码/数据文件**：
- `video-teacher-prompts/scripts/build_multisource_pilot.py`
- `video-teacher-prompts/data/curated/multisource_pilot_300_report.json`
- `video-teacher-prompts/data/prompts/multisource_pilot_300.jsonl`
- `video-teacher-prompts/data/sources/disciplinegen/metadata/sampled_rows_expanded.jsonl`

**Pull Request**：`claptrapp222/video-teacher` 的 `fix/source-share-balance-check` 分支 → 上游 `Geniusyingmanji/video-teacher` 的 `master` 分支
