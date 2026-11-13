# 评测协议

General 使用 VLM judge，对实际视频帧、独立音轨与转写逐项评定。计划或生成代码只能辅助定位，不能代替成片证据。运行定义位于 [rubric.py](../localbench/rubric.py)、[detailed_rubric.py](../localbench/detailed_rubric.py)、[strict_anchors.py](../localbench/strict_anchors.py)。

可配置三个独立评委，使用同一份抽帧／转写。54 项视觉与教学准则逐项取整数中位数，6 项音频准则使用明确标注的共享听音单评；缺票、适用性不一致或极差达到 2 分时留空并写复核清单，原有未解决证据冲突继续阻止完整总分。实现见 [judge_panel.py](../localbench/judge_panel.py)，接口见 [README](../README.md#三评委配置与调用)。这改变评委聚合方式，不改变十维权重或各项 1–5 评分锚点。

| 大块 | 子块 | 叶维度 |
| --- | --- | --- |
| 视频质量 | — | 画面与文字呈现、时间一致性、语音与音频质量 |
| 教学质量 | 内容 | 知识与解答正确性、任务完成与内容覆盖 |
| 教学质量 | 组织 | 解释与推理清晰度、教学组织与节奏、受众适配 |
| 教学质量 | 表达 | 图示与教学辅助、音画文字配合 |

共 10 维，每维 6 项，当前严格流程只用整数 1–5。每项按具体缺陷、适用范围和证据评定；1 为严重失效，3 为基本满足，5 须有明确优秀表现证据，中间档按逐项行为锚点区分。详细逐档标准以源码为准。

维度分为 `(适用项均分 − 1) × 25`。视频三个叶维度等权，教学七个叶维度等权，两类各占 50%。教学内内容、组织、表达分别占 2/7、3/7、2/7。证据未知、API 失败及未解决冲突保持缺失，不用任意分数补齐；只有协议允许的可选项才能标记不适用。

排版检查覆盖文字重叠、容器溢出、裁切、对比度、遮挡和图文关系，结合真实帧及局部裁图。裁图放大不等于原尺寸可读，静帧正确不等于播放时长充分。检查器仍有漏检，尚未完成正式人工校准。

Specific 用本题专属问题核对完整视频的知识覆盖，与 General 并列。模拟学生诊断另核对理解和读图；详见[学生协议](student.md)。不得为了压低均分随意改变规则。总分、缺失率、交付率和失败应共同报告。

## 六十项细则

以下从当前运行定义导出；修改协议时同步更新。

### 画面与文字呈现

| 项目 | 判定内容 |
| --- | --- |
| `legibility` | Essential text, formulas and labels are readable at native display size and during the actual hold; enlarged crops help diagnose defects but do not establish native readability. |
| `text_overlap` | Text lines and labels do not collide with each other or become obscured by unrelated arrows, marks or shapes. |
| `containment` | Text fits its intended container with usable padding; no essential text or glyph is clipped by a box, viewport, or frame edge. |
| `composition` | Alignment, grouping, spacing and visual hierarchy clearly separate the title, diagram, labels and caption without crowding or excessive dead space that makes essential content tiny. |
| `contrast` | Text and essential diagram strokes contrast adequately with their actual local backgrounds; color choices do not hide content. |
| `artifact_control` | Glyphs, equations, lines and shapes are rendered cleanly without corruption, missing characters, or intrusive artifacts. |

### 时间一致性

| 项目 | 判定内容 |
| --- | --- |
| `identity` | Objects and diagrams preserve identity through time unless intentionally transformed. |
| `motion` | Initiated motions follow coherent trajectories without unexplained jumps, flicker or reversals. Intentional stillness is acceptable. |
| `state_continuity` | Labels, quantities and visual states remain consistent between steps, or visibly change when intended. |
| `transitions` | Cuts and transitions preserve the context needed to follow the visible events. |
| `event_integrity` | A visibly initiated action progresses without accidental freezes, disappearance or truncation; do not infer an omitted task from task-free frames. |
| `temporal_readability` | Visible changes and holds provide sufficient time to perceive and inspect essential text or events. |

### 语音与音频质量

| 项目 | 判定内容 |
| --- | --- |
| `intelligibility` | Spoken words are intelligible throughout the actual audio. |
| `signal` | Audio is free of disruptive noise, distortion, clipping or dropouts. |
| `delivery` | Speech articulation and rhythm support sustained listening; speech is actually present. |
| `pronunciation` | Audible technical terms, numbers and symbols are pronounced distinctly; assess acoustic clarity, not factual truth. |
| `continuity` | Sentences and word endings are complete without cut-off speech or accidental gaps. |
| `level_stability` | Speech volume remains usable and reasonably stable across segments. |

### 知识与解答正确性

| 项目 | 判定内容 |
| --- | --- |
| `facts` | The central scientific or factual claim is correct. |
| `relationships` | Causal, spatial, or logical relationships are correct. |
| `notation` | Numbers, labels, equations, and units are correct and stable. |
| `reasoning` | Shown operations or intermediate states follow valid rules. |
| `final_state` | The visible result or answer matches the task. |
| `no_contradiction` | No frame contradicts the intended lesson. |

### 任务完成与内容覆盖

| 项目 | 判定内容 |
| --- | --- |
| `givens` | The actual task, quantities, original objects and constraints are preserved. |
| `coverage` | All explicitly required subquestions, concepts and operations are addressed with identifiable evidence. |
| `demonstration` | Every explicitly required visual demonstration is actually visible; narration or a final answer alone does not replace it. |
| `result` | The requested final result is shown or spoken in the modality required by the task and held long enough to inspect. |
| `verification` | Any requested verification actually checks a relationship or answer, rather than simply repeating it or saying it is correct. |
| `constraints` | Explicit prohibitions and source-preservation constraints are obeyed; no unauthorized target changes are visible. |

### 解释与推理清晰度

| 项目 | 判定内容 |
| --- | --- |
| `focus` | The stated audience can identify the one task and learning target without reconstructing omitted context. |
| `attention` | Cues guide the audience to the critical object or step at the right time, without competing highlights. |
| `why` | For each task-essential inference or mechanism, the spoken and/or visual explanation connects the given condition, the applied rule or cause, and the resulting change; naming an operation alone does not explain why it is valid. |
| `readability` | At an essential teaching step, labels and explanatory cues let the viewer locate and connect the givens, operation and result during playback; score instructional search effort, not glyph quality or presumed learning gains. |
| `grounding` | Each essential symbol, quantity and spoken reference has an identifiable referent at first use; givens, operations and results are distinguished without the viewer inventing a mapping. |
| `takeaway` | The final visible state communicates the requested conclusion without needing an off-screen explanation. |

### 教学组织与节奏

| 项目 | 判定内容 |
| --- | --- |
| `setup` | The starting state is identifiable. |
| `target` | The intended change or question is identifiable. |
| `order` | Visible events occur in a comprehensible order. |
| `transition` | At each essential instructional transition, the lesson identifies what changes and connects the preceding state to the next step through the modalities permitted by the task. |
| `closure` | The resulting state is visible long enough to inspect. |
| `chunking` | Operations that depend on one another are introduced in separable teaching units, retaining the prior state needed to interpret the next unit; inspect the densest segment rather than counting slides. |

### 图示与教学辅助

| 项目 | 判定内容 |
| --- | --- |
| `representation` | A concrete representation makes the task-relevant state, relation or before-and-after change visible; decorative movement and answer-only text do not substitute for a requested demonstration. |
| `explanatory_value` | Identify the task-relevant relationship or operation made inspectable by the visual encoding, such as changes to both sides of an equation; topic-related decoration or a conclusion caption alone is insufficient. Correctly localized labels can suffice for a labeling task. |
| `reference_anchor` | Stable objects, scales or correspondences support comparison and reveal the intended relationship without misleading changes. |
| `correspondence` | Visual shapes, positions, arrows, colors and labels map accurately to the knowledge being explained; an analogy, if used, preserves the relevant relationship. |
| `inspectability` | The actual result exposes the essential quantities, endpoints, labels or relationships needed to check it at native display size; pausing may locate evidence but cannot establish adequate playback time. |
| `diagnosability` | Name a concrete task-relevant alternative error and identify which visible quantity or relationship would distinguish it from the shown result; this is inspectability of an error, not proof that a student actually detects one. |

### 受众适配

| 项目 | 判定内容 |
| --- | --- |
| `prerequisites` | The clip fits the stated audience's prior knowledge. |
| `language` | Terminology and symbols suit that audience. |
| `complexity` | The visual load is manageable for that audience. |
| `speed` | Compare the observed time available for the most demanding step with the reading, comparison and reasoning it asks of the stated audience; speech rate or total duration alone cannot establish appropriate pacing. |
| `accessibility` | Essential distinctions remain identifiable through labels, shapes, positions or spoken naming when a color cue alone is insufficient; assess perceptual access separately from font rendering and do not assume unstated user impairments. |
| `depth` | The explanation develops the task-essential rule or mechanism to the stated audience's prerequisite level, without skipping a necessary bridge or adding inaccessible detail; evaluate audience fit, not topic count or measured learning. |

### 音画文字配合

| 项目 | 判定内容 |
| --- | --- |
| `referents` | Spoken references identify the same objects, labels and quantities visible at that time. |
| `synchrony` | The spoken explanation accompanies the relevant visible step at an instructional timescale. |
| `agreement` | Speech and the visible diagram make compatible claims about relationships, direction, quantities and operations. |
| `text_visual_consistency` | On-screen text, arrowheads, labels and geometry agree about the represented relationship; do not excuse a contradiction using an unstated convention. |
| `state_tracking` | Narrated changes correspond to the actual current visual state, without silently describing a prior or future scene. |
| `completion_claims` | Compare each observed substantive conclusion or completed-state claim with the visible outcome at that time. Separate instructions and ongoing actions from claims of completion; a later correct endpoint does not justify an earlier false completed-state claim. |

## dev14：证据完整性与非补偿验收

当前协议为 `localbench-ten-dimensions-dev14-integer-r4`，旧 dev13 成绩保留，不与新协议混排；改协议后使用新输出目录，不能继续复用旧评分缓存。General 的 50/50 权重、十维六十项定义不变，新增明确的证据有效性和独立验收政策。

### 音轨缺失与故障

先以 ffprobe 正向探测音轨。成功探测且无音轨时记录 `audio_stream_missing`，实际必需旁白为已观察到的缺失，音质六项为 1。探测失败、提取/解码失败、听音服务失败仍为未验证，不假装静音。探测器不可用但音频能成功解码时继续正常听音流程。纯音乐、数字静音、无音轨和故障分别保留来源，均不能用虚构转写补齐。

### 全片画面与同步覆盖

General 调用 `extract(..., review_every_frame=True)`，把**每一个实际解码帧**放入 `review_frames`，不只给 24 张概览帧。`timeline_review` 每批最多 16 帧，批次共享边界帧，逐批检查状态变化、字幕残留、遮挡、短暂概念错误及过渡；要求明确回传所有本批帧 ID。每次最多一次 schema 修复。任何批次失败、缺帧或完整帧清单与解码帧数不符，都记 partial 并扣留依赖视觉证据的正式维度分数。概览帧仍用于原有全局 rubric，不再被当作完整覆盖证明。

`alignment` 对所有可用定时语音时窗分批检查（每批最多八个），保留短语音窗口；不再静默截取八个。语音时窗没有邻近画面、任何批次失败或未定时语音片段都会使音画维度未验证。每个项目按所有时窗中最严重的**已观察局部限制**给全片评级，同时保存每批原始项目评级；不把严重局部错位平均掉。未验证窗口不会被当成低分或自动通过。字幕与画面按实际帧引用核对，ASR 定时不被表述为逐字强制对齐。

一般学生/媒体工具默认仍可用 2fps 加突变边界的轻量提取；它不能替代 General 所要求的逐帧审查。逐帧送审会显著增加存储、API 次数和 token；预算照常限制，不够即保留覆盖缺口，不能通过截断提高覆盖率。所有帧已送审只是模型检查覆盖，不等于模型保证检出全部错误，更不是人工视听认证。

### 维度有效性与配对

`score_validity` 将未解决的参考冲突、独立检查缺失/失败/歧义、检查与评分矛盾、布局检查缺口、逐帧检查缺口及转写争议传播到受影响维度。具体 scope 已知时不连带抹掉无关维度；未结构化参考冲突保守阻断教学维度。原始 criterion 评级保留，失效的维度原数字另存 `raw_score_before_validity`，正式 `score` 为 null，分组和总分据此重算。

每个维度返回 `score_validity.status/reasons`。`verified` 仅表示协议所要求的证据可用且无未解冲突，不表示专家判定正确。被扣留的总分不会被后续汇总复活。报告和配对器使用同一有效性函数；旧文件即便仍有数字，也会读取其冲突/缺失信息，排除受影响的维度及总分，保留无争议维度。配对输出 `evidence_exclusions`，失败/缺失任务仍留在分母。

### 独立验收：高均分不能补偿关键缺陷

`acceptance` 与连续 General 分数并列保存，不进行隐含封顶或改写原始评级：

- 每维至少 60；概念正确性、任务完整性、教学清晰度至少 70；视频和教学分组均至少 70。
- 任一有可用证据的项目出现 major/critical 缺陷，或独立检查确认重大/关键缺陷，均验收失败，即便总分很高。
- 已观察的要求失败均使验收失败；未解冲突、必需检查缺失、覆盖缺口或待核查使验收未验证。
- 状态为 `passed / failed / unverified`。确认失败与未知可以共存：总体为 failed，同时仍列出未知原因。只有证据完整且所有规则满足才 passed。

上述阈值是提前声明的开发政策，尚未进行人工效度校准；不是学习成效测量。`scores.json`、CSV、运行报告和配对报告均展示验收状态/原因与全计划题验收率。CLI 退出成功表示生成/评测执行完成，不代表所有视频质量验收通过。旧文件缺少完整检查时不能仅因保留一个高分被标为通过。

三评委入口同样使用 dev14：媒体与听音只准备一次，每名视觉/教学评委独立检查全部帧和语音时窗。任何成员的维度证据失效，不能从其保留的原始项目分数重新投出有效票。汇总保留整数中位数及原始票；即使两票 3、一票 2 的极差只有 1，重大缺陷异议也须裁定，相关维度在配对前保持未验证。三名成员的参考冲突、检查失败及覆盖缺口继续传播到汇总；旧面板文件的空 concerns 包装不被误判为实际冲突。音频仍是独立标注的单份共享检查，不冒充三份独立证据。

## dev15：参考数学、完成判断与截断恢复

当前协议为 `localbench-ten-dimensions-dev15-integer-r5`。dev14 及更早结果保留，不能混排；使用新目录。新增检查不等于专家校准或历史视频已改善。

- `scientific_audit` 在生成前只读公开任务，遇到已知错误的 Snell 速度乘积关系就阻断，不把私有答案送入生成。评测端也检查实际使用的参考，明确排除合同中已被弃用的候选参考；冲突进入 reference_concerns，扣留受影响概念维度及总分。已知错误筛查没有发现问题，仅表示 no_known_conflict，不表示专业内容已认证。
- 场景可以声明 `derivation:{equations:[...],nonzero:[...],substitutions:{...}}`。受限 AST 构造符号表达式，不执行任意模型代码。只对已证明的非零倍数等价变形放行；无法证明、改变解集、未声明分母非零或违反假设则阻断。代数等价不证明第一条物理前提正确。正确的波前参考见 [版本化校正文件](../data/reference_corrections/snell_wavefront_v1.json)，它不是覆盖原成绩或增加正式题目。
- 要求清单增加 fulfillment（complete/partial/absent/incorrect/uncertain）。met 与非 complete 明确冲突会拒绝；对文字中明确承认“部分完成、缺旁白、缺示例或未验证”的 met 同样拒绝并请求恢复，失败则保留未验证。检查是有边界的语义一致性保护，不宣称理解所有自然语言。partial derivative/fractions 等学科词不等于部分完成。勾号、QED 和最终公式不能单独证明核验过程发生。
- 教学维度大响应失败后按失败维度拆分请求，保留成功兄弟维度；单维仍失败才留空。要求清单按最多五项恢复，不重复要求超大完整对象；原始响应、分拆路径及部分成功清单都落盘。传输层不把截断响应当成功缓存，预算仍统一限制。

method 入口的统一声明式后端现在在渲染前启用公开输入的内容复核；未解事实问题阻断，文本修复不能擅改公式/几何字段。真实模型接口和内容检出率仍需恢复实验后验证，离线测试只验证实现路径。

冻结参考合同时，非空未决 concerns 不能仅靠 editorial_reviewed 标签获得通过。对直接传入的合同，未决问题同样进入评分有效性。数学筛查只审查公开任务及合同实际使用的参考条目，明确排除已标为冲突/弃用的候选参考，避免误把已经隔离的参考问题重新扣到视频上。
