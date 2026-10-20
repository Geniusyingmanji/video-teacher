# 从知识状态到生成约束

这是短片段生成的通用接口；按**状态变化**描述任务，不按学科或样例 ID 写分支。当前实现覆盖生成前检查和提示编译，尚未证明模型遵守提示，也尚未自动判断最终视频的知识正确性。

## 一条教学步骤如何变成约束

1. 学科专家或经核对的题源给出学习目标、一个 `beat`、前态 `pre_state`、后态 `post_state`。状态键必须持久，`changes` 必须准确列出变化的键。未变化的事实可放进 `invariants`。
2. 将可计算关系写成 `checks`。支持路径或常量作为操作数，当前有 `equals`、`less_than`、`greater_than`、`all_equal`、`sum_equal`。例如 `post.focus.y == post.axis_y`，或转移前后电子总数相同。这些检查只证明**契约内部**自洽；错误的题目真值仍需专家发现。
3. `visible_evidence` 说明观众必须在最终画面看见什么。`layout` 以相对坐标预留文字和图示区域，检查安全边距、最小文字大小、文字是否装得下、同一阶段区域是否重叠。相对坐标可跨输出分辨率复用。
4. `prepare_cases` 先检查目标时长与帧数/FPS是否匹配，并试渲染状态绑定的图元，全部通过后才编译成单步骤 `video_prompt`。原始长课提示不会混入短片提示。两个 Wan 入口均可用 `--contracts` 启用，且在加载模型前失败退出。manifest 保存完整生成提示、目标时长和契约 SHA-256。
5. 后续成片验证应以 `visible_evidence` 和 `checks` 为检测目标，输出证据时间戳及 `wrong / missing / unobservable`。目前的通用代码尚未对像素视频执行这一步；提示通过预检不能算成片通过。

## 多轮修订

`refine_contract` 提供有上限的“草案 → 诊断 → 修订 → 再验证”循环。编辑器或 Agent 以回调形式接收诊断，最多运行 `max_rounds` 次；每轮记录契约哈希、通过/拒绝状态和错误原因。循环冻结学习目标、知识断言与前后知识状态，只允许修正约束表达、检查项或布局。专家若发现真值本身有错，须另行修订题源并重新审核，不能在自动修复中悄悄改答案。

这是**生成前**的循环。生成后的循环还需从成片提取证据，定位失败镜头，按固定预算修改提示、首帧或片段，并重新核对最终画面；该部分尚未实现。

## 跨学科例子

[`examples.jsonl`](../data/teaching_contracts/examples.jsonl)包含数学求导、凸透镜、NaCl 电子转移三个**示范契约**。求导案例检查唯一变化的项及公式的排版框；透镜案例检查焦点与光轴的纵坐标相等、焦点在透镜右侧、入射光线斜率一致；化学案例检查电子总数守恒和离子电荷。它们共享一套状态、断言、布局和时长校验代码。

只检查契约并输出编译后的 JSONL，不生成视频：

```bash
python -m scripts.check_generation_contracts \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --contracts data/teaching_contracts/examples.jsonl \
  --out results/compiled_contract_examples.jsonl
```

这三个示例仅覆盖 pilot 的 3/60 题。用于正式运行时，先完成并审核整批契约，再加 `--require-all`；Wan 入口在给定 `--contracts` 时本身要求每个待生成题目有契约。当前已有可验证首帧的代码原型，但 Wan TI2V 只接收首帧和提示；要测试“可执行状态进入像素成片”的方法假设，仍需最终成片事实保持检查，以及与普通首帧/纯文本的配对对照。

通用图元首帧渲染器已在 [`contract_frame.py`](../generation/contract_frame.py) 实现；三题与现有普通首帧的实际检查见[试运行记录](CONTRACT_FIRST_FRAME_TRIAL.md)。这个试运行只覆盖首帧，不构成成片方法效果证据。
