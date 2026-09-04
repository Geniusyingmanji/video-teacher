# 300 题候选集术语与代码结构说明

**对应脚本**: `scripts/build_multisource_pilot.py`
**用途**: 解释 `multisource_pilot_300.jsonl` 数据结构中出现的字段名、函数名和设计概念，供后续维护和复核参考。

本文档只做名词解释，不涉及问题诊断或改进建议；改进相关内容见
`docs/MULTISOURCE_PILOT_300_IMPROVEMENT_PLAN.md`。

---

## 一、两个上游数据源

### GRADE

一个"给定原图 + 编辑指令 + 目标图"的图表编辑数据集。每条记录包含：
- 学科领域（`domain`，如 `math`、`physics`）
- 编辑指令文本（`text`）
- 原图路径（`image_path`）和目标图路径（`gt`）
- 可选的检查问题列表（`questions`）

脚本里用 `GRADE_DOMAIN_MAP` 把GRADE原始的领域标签（如 `"his"`、`"eco"`）映射到仓库统一使用的学科名（`history`、`economics`）。

### DisciplineGen-1M

一个跨学科的文本到图像/编辑标注数据集，以Parquet文件存储，按学科和任务类型拆分成多个文件（如 `t2i_chemistry.parquet` 是"生成"类标注，`edit_math_math_textedit.parquet` 是"编辑"类标注）。因为单个Parquet文件的图像列体积巨大，脚本只读取文字标注列，不下载图像。

---

## 二、生成的prompt记录里的字段含义

以下字段是脚本最终写入 `multisource_pilot_300.jsonl` 每一行的键，`REQUIRED_FIELDS` 里列出的是必须存在的字段。

| 字段 | 含义 |
|---|---|
| `id` | 记录的唯一标识，格式为 `grade_<task_id>` 或 `disciplinegen_<discipline>_<source_key>`，全部转小写。 |
| `discipline` | 学科分类，取自 `DISCIPLINES` 列表中的10个固定值（mathematics、physics、chemistry、biology、geography、computer_science、economics、history、music、sports）。 |
| `subdomain` | 学科下的细分方向，比如GRADE的 `sub_task`，或DisciplineGen的文件名主体（如 `science_t2i`）。 |
| `task_type` | 教学任务的类型，只能是 `"explanation"`（讲解型）或 `"problem_solving"`（问题求解型）。详见下一节。 |
| `difficulty` | 难度分层，当前实现里全部写死为 `"undergrad"`（本科水平）。 |
| `prompt_text` | 真正会喂给视频生成模型的完整指令文本，由脚本拼接学科、任务类型、教学操作（archetype）和原始标注内容生成。 |
| `expected_concepts` | 期望视频体现的知识点列表，用于后续人工/自动评分对照。 |
| `expected_visual_elements` | 期望视频画面中应该出现的视觉元素清单（如"高亮的编辑区域"、"带方向箭头的时间线"）。 |
| `expected_narrative_order` | 期望的叙事节拍（beat）顺序，是一个字符串列表，描述视频应该按什么顺序展开。 |
| `pedagogical_target_audience` | 目标受众描述，固定格式为"某学科的入门学生"（`introductory <discipline> student`）。 |
| `discipline_specific_rubric` | 针对该学科/任务定制的评分要点列表，用于人工评审时打分参考。 |
| `audio_narration_required` | 是否要求视频包含语音讲解，当前全部为 `False`。 |
| `target_duration_s` | 期望视频时长（秒），当前全部为 `5`。 |
| `narrative_beats` | 把 `expected_narrative_order` 转换成带有具体帧区间（`expected_frame_range`）的结构化列表，由 `timed_beats()` 函数生成。 |
| `source` | 记录该条数据的原始出处信息（数据集名称、原始ID、许可状态等），详见后文第七节。 |
| `curation` | 记录该条数据的复核/加工状态，详见后文第八节。 |

---

## 三、`task_type`：讲解型 vs 问题求解型

`task_type` 描述这条prompt要求视频完成什么性质的教学动作，只有两个取值：

- **`explanation`（讲解型）**：要求视频呈现一个概念、结构或关系，不涉及"编辑/修改"一个已有的视觉状态。多数来自DisciplineGen里非`edit_`前缀的文件（如 `t2i_chemistry.parquet`）。
- **`problem_solving`（问题求解型）**：要求视频呈现"从一个初始状态，按指令完成某种操作/编辑/推导，得到最终状态"的过程。GRADE的所有记录都被固定标记为此类型（因为GRADE本身就是"原图→编辑指令→目标图"结构）；DisciplineGen里文件名以`edit_`开头，或记录中含`instruction`/`edit_instruction`字段的行，也归为此类。

判定逻辑基于**源标注文本的内容**，而不是记录来自哪个数据源（这是2026-08-30改进后的行为，此前该字段完全由数据源决定）：

```python
# grade_to_prompt() 和 dg_to_prompt() 都调用同一个函数
task_type = infer_task_type(source_text)
```

`infer_task_type()` 的判定规则：
1. 统计文本中"操作/推导类动词"（complete、fill、calculate、mark、rotate、missing 等）和"创建类动词"（generate、draw、create、illustrate 等）各出现多少次。
2. 如果出现了操作类动词，**且**文本里有指向已提供素材的短语（"in the diagram"、"shown in"、"provided"、"starting from" 等），直接判为 `problem_solving`——因为这说明任务是在既有素材上做修改，而不是从零创建。
3. 否则比较两类动词的出现次数，多者胜出。

注意：判定只看**动词**，不看 diagram、figure 这类**名词**。因为两种任务类型都会频繁提到这些名词，把它们计入会导致误判（例如"complete the equation in the diagram"会因为"diagram"被误判成讲解型）。

---

## 四、`grade_to_prompt` 与 `dg_to_prompt`：两个转换函数

这两个函数是脚本的核心，分别负责把两个上游数据源的一行原始记录，转换成前面列出的统一prompt schema。

### `grade_to_prompt(row)`

输入：GRADE数据集的一行原始记录（包含`domain`、`sub_task`、`text`、`task_id`、`image_path`、`gt`、`questions`等字段）。

主要步骤：
1. 用 `GRADE_DOMAIN_MAP` 把 `domain` 转换成仓库统一的 `discipline`。
2. 从 `questions` 字段提取评分要点（`rubrics`），不足3条时用几条通用的兜底描述补齐。
3. 调用 `pedagogical_archetype()` 分析指令文本，判断这是哪一种"教学操作类型"（archetype，见下节）。
4. 调用 `archetype_spec()` 根据archetype生成对应的视觉元素、叙事节拍、评分要点模板。
5. 拼装出完整的prompt记录，`task_type` 固定为 `problem_solving`，`curation.status` 固定为 `draft_needs_subject_review`（表示这条数据还需要学科专家复核事实正确性）。

### `dg_to_prompt(row)`

输入：DisciplineGen的一行原始记录（在此之前，`row` 已经被 `stratified_dg()` 打上了`_inferred_discipline`、`_source_file`等辅助字段）。

主要步骤：
1. 读取 `_inferred_discipline` 作为该记录的学科。
2. 从记录里提取原始标注文本（`row_text_fields()`，见下节）。
3. 判断文件名是否是`edit_`前缀来决定 `task_type`。
4. 同样调用 `pedagogical_archetype()` 和 `archetype_spec()` 生成教学结构。
5. 拼装出完整的prompt记录，`curation.status` 固定为 `draft_needs_visual_review`（表示图像未下载，视觉呈现是否合理还没人工核实）。

## 五、`pedagogical_archetype`：教学操作类型

这是脚本用来给每条记录打上"这段视频该教什么样的动作"标签的函数。输入是原始标注文本（和可选的subdomain），输出是一个固定的分类标签（archetype）。

判定方式是关键词正则匹配，按顺序检查文本里是否出现某一类关键词，命中第一个匹配的规则就返回对应标签：

| archetype | 触发关键词示例 | 含义 |
|---|---|---|
| `quantitative_reasoning` | calculate, equation, formula, graph, axis, vector, angle, probability | 需要计算、作图或符号推导的任务 |
| `comparison` | compare, contrast, difference, versus, distinguish | 对比两个对象或状态的任务 |
| `temporal_sequence` | timeline, sequence, cycle, stages, steps, process, flow | 按时间/步骤顺序展开的任务 |
| `causal_mechanism` | mechanism, cause, effect, interaction, transmission, reaction, force | 解释因果关系或机制的任务 |
| `classification` | classify, category, group, sort, taxonomy, hierarchy | 分类归组的任务 |
| `spatial_reasoning` | map, location, region, formation, geometry, direction, anatomy | 涉及空间位置、地理、几何关系的任务 |
| `evidence_inference` | infer, evidence, determine, diagnose, deduce, interpret | 根据线索推断结论的任务 |
| `labeling` | label, annotate, name, mark the, point to | 给视觉元素打标签/命名的任务 |
| `visual_transformation` | （无匹配规则时的兜底类别） | 上述规则都未命中时的默认归类，多为"对输入图像做某种变换"的任务 |

判定顺序即代码里 `rules` 列表的顺序，也就是从上到下依次尝试匹配，一旦某条规则命中就立即返回，不会再检查后续规则。这意味着如果一段文本同时包含"calculate"和"compare"两个关键词，会被归为 `quantitative_reasoning`（因为它排在规则列表最前面），而不是`comparison`。

`visual_transformation` 不是一个真正被关键词识别出来的类别，而是"没有命中任何规则"的默认归类，所以它的占比高，通常反映的是关键词覆盖不足，而不是这类任务本身特别常见。

---

## 六、`archetype_spec`：按archetype生成的教学脚本模板

这个函数接收 `pedagogical_archetype()` 的输出结果和原始标注文本，返回三个列表，分别对应prompt记录里的三个字段：

1. **视觉元素列表**（→ `expected_visual_elements`）：这类archetype的视频画面里应该出现哪些视觉组件。例如`labeling`类型要求"未标注的原始画面"、"末端对准目标的引导线"、"完整的标签集合"。
2. **叙事节拍列表**（→ `expected_narrative_order`，再经`timed_beats()`转换为`narrative_beats`）：视频应该按什么顺序展开，通常是4个节拍：呈现任务→聚焦关键信息→执行核心操作→验证结果。
3. **评分要点列表**（→ 汇入`discipline_specific_rubric`）：用于人工评审时检查这类任务是否做对，例如"结论没有超出证据支持范围"（针对`evidence_inference`）。

## 七、`source` 字段：溯源信息

记录这条prompt改编自哪个原始数据源、哪一条记录，方便追溯和许可审查。两个数据源的字段略有不同：

**GRADE来源的记录**：
| 子字段 | 含义 |
|---|---|
| `dataset` | 固定为 `"GRADE"` |
| `source_id` | 原始的 `task_id` |
| `source_url` | GRADE数据集主页链接 |
| `source_image_path` / `target_image_path` | 原图/目标图在上游数据集里的路径 |
| `original_instruction` | 原始编辑指令文本 |
| `license_status` | 许可确认状态，当前为 `"unverified"`（未确认可否重新分发） |

**DisciplineGen来源的记录**：
| 子字段 | 含义 |
|---|---|
| `dataset` | 固定为 `"DisciplineGen-1M"` |
| `source_id` | 内部生成的稳定标识（`_source_key`或`stable_key()`生成的哈希） |
| `source_url` | 指向具体Parquet文件的HuggingFace链接 |
| `source_file` | 具体的上游Parquet文件名（如`t2i_chemistry.parquet`） |
| `row_group` / `row_index` | 该记录在Parquet文件里的物理位置，用于精确复现取样 |
| `original_annotation` | 原始标注文本 |
| `license_status` | 固定为 `"verified_redistributable"`（DisciplineGen-1M的GitHub仓库声明了CC BY 4.0许可） |
| `license` / `license_source` | 许可名称及其声明来源链接 |

### `stable_key()`

DisciplineGen的原始记录本身没有唯一ID，脚本用这个函数基于记录内容算出一个确定性的哈希值作为 `source_id`，保证同一条原始数据无论何时重新构建，生成的ID始终相同（可复现性）。

---

## 八、`curation` 字段：数据复核状态

记录这条数据在"能否直接使用/发布"这条流水线上处于哪个阶段。

| 子字段 | 含义 |
|---|---|
| `status` | 复核状态，取值包括：`draft_needs_subject_review`（GRADE专用，需要学科专家核实事实正确性）、`draft_needs_visual_review`（DisciplineGen专用，需要核实图像未下载情况下的视觉合理性）、`reviewed_release_ready`（已完成复核，可用于发布） |
| `conversion` | 转换方法版本标记，当前为 `"source_grounded_archetype_v2"`，表示使用了"基于原始标注内容归类archetype"的第二版转换逻辑（相对早期版本`deterministic_v1`） |
| `pedagogical_archetype` | 与前面`pedagogical_archetype()`函数输出一致，记录这条数据被归入的教学操作类型 |
| `automatic_quality_checks` | 一组布尔标记，说明这条数据经过了哪些自动化检查（是否源自原文、是否有可视化验证的结果、是否禁止编造未支持的事实等），但这些标记只是"声明"，不是实际的自动化验证结果 |
| `visual_pair_screening` | 仅GRADE记录才有，记录图像对（原图/目标图）是否经过人工的"contact sheet"（缩略图集合）快速筛查 |

---

## 九、辅助函数速查

| 函数 | 作用 |
|---|---|
| `row_text_fields(row)` | 从原始记录里按固定字段顺序（prompt、text、caption、instruction、edit_instruction、conversations、description、metadata）提取所有可用的文本内容，拼成候选文本列表。 |
| `has_usable_text(row)` | 判断一条DisciplineGen记录的文本长度是否落在35-1200字符之间，用于过滤"太短没有教学目标"或"太长无法在5秒视频里呈现"的记录。 |
| `infer_dg_discipline(row)` | 从DisciplineGen记录的文件名、`subject`/`discipline`/`domain`等字段、或标注文本内容里，推断这条记录属于10个学科中的哪一个。 |
| `source_tokens(row)` | 把记录的文本内容切分成小写单词集合，用于后续的重复度检测。 |
| `diverse_take(candidates, count)` | 从候选列表里挑出`count`条记录，优先选择彼此文本重复度（Jaccard相似度）较低的记录，避免选出内容雷同的样本。 |
| `stratified_grade(rows, per_discipline, seed)` | 对GRADE全量数据按学科分组，剔除已知问题ID，再调用`diverse_take()`为每个学科选出固定数量的记录。 |
| `stratified_dg(rows, per_discipline, seed)` | 对DisciplineGen全量数据做同样的分层选取，额外增加了"按上游文件轮流取样"的桶排序逻辑，避免单一模板化文件占满某个学科的名额。 |
| `timed_beats(beats)` | 把一组叙事节拍文字，均匀映射到1-8的帧编号区间上，生成`narrative_beats`里每个节拍对应的`expected_frame_range`。 |
| `clean_text(value, limit)` | 把任意类型的字段值转成去除多余空白、限制长度的字符串，用于生成ID、截取展示文本等场景。 |

---

## 十、验证报告（report JSON）里的术语

对应 `data/curated/multisource_pilot_300_report.json`，由 `validate_rows()` 函数生成。

| 字段 | 含义 |
|---|---|
| `valid` | 基础schema检查（必填字段、合法的discipline/task_type取值、ID唯一性等）是否全部通过。 |
| `release_ready` | 在`valid`基础上，是否也没有`release_issues`（许可、复核状态等发布前置条件）。 |
| `by_source` / `by_discipline` / `by_source_discipline` | 按数据源、学科、"数据源+学科"组合统计的记录数量分布。 |
| `curation_status` | 按`curation.status`取值统计的记录数量分布。 |
| `diversity.pedagogical_archetypes` | 按`curation.pedagogical_archetype`统计的记录数量分布。 |
| `diversity.unique_narrative_plans` | 有多少种不同的`expected_narrative_order`组合（叙事节拍的具体文字序列），用于判断模板是否过度重复。 |
| `diversity.largest_exact_narrative_plan_count` | 出现次数最多的那个叙事节拍组合重复了多少次。 |
| `diversity.largest_pedagogical_archetype_share` | 占比最高的archetype类别在全部记录中的比例。 |
| `diversity.source_text_near_duplicate_pairs_at_0_72` | 使用Jaccard相似度阈值0.72判定为"近似重复"的原始标注文本配对数量。 |
| `paper_candidate_gate` | 一组自动化门槛检查的汇总结果（archetype数量≥8、单一archetype占比≤35%、单一叙事模板重复次数≤5、近似重复对数=0），`automated_pass`为`true`表示全部通过。但这仅代表自动化检查通过，`manual_subject_review_required`等字段说明人工复核仍是必须的。 |

---

## 十一、常见疑问速答

**Q: `task_type` 和 `pedagogical_archetype` 是同一个东西吗？**
不是。`task_type` 只有两种粗粒度取值（讲解/问题求解），反映"整体教学模式"；`pedagogical_archetype`有9种细粒度取值，反映"具体的认知操作类型"（比如分类、对比、时序）。一条`explanation`类型的记录也可以是`quantitative_reasoning`archetype。

**Q: 为什么两条不同数据源的记录，`expected_visual_elements`措辞很像？**
因为两者都是通过同一个`archetype_spec()`函数生成的，只要archetype相同，视觉元素模板就相同，脚本只替换了模板里嵌入原文的那一小段文字。

**Q: `draft_needs_subject_review`和`draft_needs_visual_review`能互换吗？**
不能。前者只出现在GRADE记录里（关注内容对错），后者只出现在DisciplineGen记录里（关注视觉呈现是否合理，因为图像还没下载核实）。这是两个数据源各自欠缺的复核类型不同导致的。
