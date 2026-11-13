# 评测协议

General 使用 VLM judge，对实际视频帧、独立音轨与转写逐项评定。计划或生成代码只能辅助定位，不能代替成片证据。运行定义位于 [rubric.py](../localbench/rubric.py)、[detailed_rubric.py](../localbench/detailed_rubric.py)、[strict_anchors.py](../localbench/strict_anchors.py)。

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
