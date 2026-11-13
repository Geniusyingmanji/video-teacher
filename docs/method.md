# 方法：可执行教学场景与反馈修复

当前研究问题：如何让教学画面中的对象、数量、关系和变化过程与讲解保持一致。

```text
公开题目、受众、时长、公开原图
  → 任务路由与课程规划
  → 声明式场景程序 / 专用状态或原图后端
  → 结构与布局检查、真实英语配音、排时与渲染
  → 普通图形分支的 VLM 成片反馈与局部修复
  → 可选表观尺寸顺序约束
  → 可选对象连接约束
  → 独立 General / Specific / 学生诊断
```

场景程序是受约束的 JSON；当前不直接执行任意模型 Python。状态和关系工具保证声明关系的执行，模型对题意、对象和关系的选择仍可能错误。最终评测重新读取实际媒体；既有方法实验使用同类模型作视觉 judge；新接口可显式配置三个不同家族评委，但真实服务与校准仍待验收。

## 从哪里看实现

| 职责 | 代码 | 说明 |
| --- | --- | --- |
| 完整入口、分支及可选阶段 | [run.py](../localbench/run.py) | `teacher.py method` 实际入口 |
| 课程规划与生成 | [pipeline.py](../localbench/pipeline.py) | 与 [scene.py](../localbench/scene.py) 渲染配合 |
| 领域状态 | [state.py](../localbench/state.py)、[源码导航](../localbench/README.md) | 数学、电子、算法等有限适配 |
| 视觉反馈与局部修改 | [visual_agent.py](../localbench/visual_agent.py)、[rerender.py](../localbench/rerender.py) | 普通修复通常保持旁白和时间；专用分支受保护 |
| 表观尺寸顺序 | [apparent_size.py](../localbench/apparent_size.py)、[public_spans.py](../localbench/public_spans.py) | 可选、默认关闭；最近实测失败并保留原片 |
| 对象连接 | [object_connections.py](../localbench/object_connections.py)、[connection_instances.py](../localbench/connection_instances.py) | 可选、默认关闭；覆盖跨场景重复实例 |


可选关系工具尚未证明稳定跨题收益；尺寸修复仍不稳定。当前不具备 self-evolving 或 RSI 的实验证据。详见[当前状态](status.md)。

## 与官方 Code2Video 的源码对比

核对对象是 [Show Lab Code2Video 固定提交](https://github.com/showlab/Code2Video/tree/1142d8e14cdc2806df85aedb0fbb5dca474caa0f)，不是同名的 SenseNova 模型。以下是源码中的机制差异；目前没有同 backbone、同题、同预算的成片对照结果，不能据此宣称我们优于它。

| 环节 | 官方 Code2Video | 我们当前框架 | 可以检验的增量与限制 |
| --- | --- | --- | --- |
| 规划 | 教学大纲 → 分镜 → `lecture_lines` 与对应动画；已有受众、先修知识、递进要求 | 公开任务 → 带旁白与时长的 JSON 场景；按题面路由状态／原图分支 | 完整教学规划本身不新；需验证明确的任务关系是否被保留 |
| 表示与渲染 | 生成自由 Python／Manim，使用 `TeachingScene` 和 6×6 网格 | 白名单 JSON 图元、确定性渲染器，加有限领域状态编译器 | 更容易检查和绑定数量、连接与状态；代价是表达范围受限，Manim 对新动画的自由度更高 |
| 运行错误修复 | ScopeRefine 从报错定位行／函数／动画块，局部修改后做语法与 dry-run 检查，失败时回退整段修复 | schema 校验、布局检查与受限图元修改；不需要为任意模型 Python 做运行修复 | 两边都已有“检查→局部修复”；我们的可检验增量应落在教学约束，不能只强调 agent 循环 |
| 视觉反馈 | `stage4.py` 明确写 **ONLY for layout and spatial positioning issues**；检查遮挡、越界、网格利用，最多 3 项；`GridCodeModifier` 应用位置／尺寸修改 | `visual_agent.py` 检查内容、组织、表达、视频四组，最多 8 项，并校验 scene 与实际证据 ID | 反馈对象从版式扩展到知识关系和步骤；VLM 仍可能误判，问题条目多不等于效果好 |
| 可执行知识 | 所选实现主要通过模型生成的 Manim 程序表达；没有看到与我们相同的跨题统一状态验证层 | `state.py` 有方程、二分搜索、遗传组合、电子转移等有限适配；另有琴键、力对、肾单位、债券等专用分支 | 可以直接计算部分答案过程与状态变化；主要靠规则和专用适配，尚非覆盖 400 题的通用能力 |
| 对象关系 | 网格位置、区域和缩放可定位；语义关系主要依靠规划／代码内容 | 对象连接、跨场景实例、箭头方向、表观尺寸等可选约束与绑定工具 | 可比较端点、数量、方向、跨场景身份；部分工具默认关闭，表观尺寸试验仍有失败和无改动 |
| 修复保留 | 原代码备份和重试已存在；官方并发／路径假设需适配 | 普通视觉修改限制编辑范围，校验音轨保持一致；专用分支有保护与失败保留 | 有利于定位修复的副作用；“保留原片”不等于修复成功，需同时统计新错误和未修复问题 |
| 跨题经验 | 本次固定源码中未见独立的跨任务经验更新模块 | 有建议记忆研究组件，但默认 `method` 不形成已验证的自演化流程 | 目前不能主张 self-evolving／RSI；若继续做，需另与 ManimAgent 比较 |
| 最终评分 | 原项目有自己的评测流程 | 独立 General／Specific／学生诊断，可配置三评委 | 这是 benchmark 的公共基础设施；对两种框架同样使用，不计作生成方法优势 |

源码依据：官方 [agent.py](https://github.com/showlab/Code2Video/blob/1142d8e14cdc2806df85aedb0fbb5dca474caa0f/src/agent.py)、[scope_refine.py](https://github.com/showlab/Code2Video/blob/1142d8e14cdc2806df85aedb0fbb5dca474caa0f/src/scope_refine.py)、[stage4.py](https://github.com/showlab/Code2Video/blob/1142d8e14cdc2806df85aedb0fbb5dca474caa0f/prompts/stage4.py)；本项目 [state.py](../localbench/state.py)、[run.py](../localbench/run.py)、[visual_agent.py](../localbench/visual_agent.py)、[object_connections.py](../localbench/object_connections.py)、[rerender.py](../localbench/rerender.py)。

### 本次接入如何处理公平性

适配器调用固定源码中的大纲、分镜、代码生成、ScopeRefine、网格反馈与修改逻辑；生成定义通过 AST 选择加载，绕开上游 CLI、厂商 SDK 和依赖其目录的初始化。上游文件本身不修改，逐个校验哈希；没有将自写 Planner–Coder–Critic 标成官方复现。

为了运行我们的完整教学题，明确增加如下适配，均写入 `adapter.json`／冻结配置：

- **输入：** 使用完整公开题面、受众、时长及允许的原图；不导入上游题库参考图或外部图标搜索结果。给规划、代码和纠错请求实际附图，不只传图片路径。
- **时长与旁白：** 将官方默认约 5 分钟改成题目时长，分镜增加 `narration` 和 `duration_s`；用与其他路线相同的 TTS 后端实测排时，再要求代码匹配。时长不符进入运行纠错，最终不强行拉伸或裁剪。这是基线的任务适配，不算本方法独占贡献。
- **模型与观察：** Planner、Coder、ScopeRefine、内部 Critic 全部使用同一 `generator` B*；官方默认的 Gemini 整段视频＋网格输入改成均匀抽帧＋官方网格图，保留官方布局提示。观察方式的变化可能影响结果，需要在论文说明；正式 judge 独立且对所有框架相同。
- **执行：** 保留官方 Manim 0.19.0 和低质量预设 480p／15 fps；生成代码与 dry-run 在隔离容器执行。外层限制并行题数、段落按原顺序处理，以便共享 API 预算且避免上游新进程丢失状态。
- **失败：** 缺段、无有效 Critic 或时长不符保留为失败；修复失败时保留匹配的旧代码和旧媒体；全部题目仍在统计分母。成功的视频仍可能质量很低，由统一评测判断。

这一行应写作 **B* + Code2Video (adapted)**。与我们的 JSON 后端存在表示与渲染差异，系统对照能回答“哪条完整路线效果更好”，不能单独证明某个模块导致提升。后续统一分辨率／帧率时需要重新冻结设置，不能靠视频放大获得相同原生画质。

### 最值得验证的三个方法假设

1. **可执行知识状态：** 对要求数量变化、算法轨迹、状态转移的题，显式计算与渲染绑定能否减少画面知识错误？同时报告适配器覆盖率、未覆盖题表现和引入的新错误。
2. **教学关系反馈：** 相比官方布局反馈，检查“对象—关系—步骤”是否提高 Specific 与教学内容／表达维度？在同一表示和预算下比较普通视觉反馈与关系约束，避免把渲染器差异当作约束效果。
3. **受约束局部修复：** 固定正确旁白、时间和已验证关系后，局部修改能否降低回归率和修改成本？同时报告修复成功、未改动、失败保留与误改，不能仅挑成功案例。

这些增量可以概括为“把教学关系变成可检查、可执行、可局部修复的约束”。代码生成、三角色协作、视觉反思、语法纠错和网格布局本身已有直接先例。当前最明显的短板仍是专用规则覆盖、跨题泛化以及稳定提升的证据。

## 数值同源图示与绑定的局部修复

二维点积、线性映射、矩阵复合、换基新增 `linear_algebra` 计算型图元，独占图示面板。箭头、当前网格、矩阵和读数从同一状态计算；不能传入独立的 dot/result/readout 字段。复合计算 `B(A v)` 与 `(BA)v`，换基计算 `B^-1 v` 并重建原世界向量。中间帧读数与当前变换同步，目标值明确区分；各数值与假设由公开任务决定，不从隐藏答案导入。收据为 `linear_algebra_computation.json`。目前只覆盖有限二维操作，不是任意模型画出的几何已经正确，也不是改写官方 Code2Video 渲染器。

已交付的声明式片子可用 `teacher.py repair` 精确修改字幕、旁白或可见文本。补丁绑定 case_id、视频 SHA256 和规范 JSON 计划 digest，逐项提供场景、字段、完整旧文和新文；旧文、哈希、公开任务任一不一致均拒绝。保留原片，写新目录。固定章节边界；不重规划整片，不移动后面的语音。

字幕修复复制原音轨并比对完整解码样本；旁白修复仅合成目标章节并固定槽位拼接，超长就失败，不截断或推移其他章节。拼接前 24kHz PCM 的非目标样本保持一致；最终 AAC 重编码不承诺逐样本完全相同。非目标场景保持原计划并核对多个渲染进度的原始像素；目标章节仍有阻塞布局问题则拒绝。失败候选记录原因并回退为原片，不伪装成修复完成。

编译字幕/分段语音不能改一个实际不生效的普通文本字段；要修改对应编译器，工具会明确拒绝。该入口不支持直接修改缺少绑定声明式计划的旧 Manim／原生模型视频。产物状态为 rendered_requires_independent_evaluation，必须另做评测，不能直接继承原分数。

局部修复还要求源 artifact 在原始生成时记录 `plan_sha256`、`scene_version` 和 `renderer_sha256`（代码、Pillow 与实际字体指纹）。不能通过事后修改 plan.json 再更新补丁哈希来重新绑定原片；没有原始收据或渲染环境已变的旧产物会拒绝自动修复。成功的新片清除继承的总分、维度、验收及 quality_passed，标记 not_evaluated_after_repair；失败仍保留原片对应记录。
