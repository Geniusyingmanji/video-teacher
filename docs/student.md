# Specific 与模拟学生

这两块独立于 General 报告，不合成学生总分。

| 入口 | 输入与输出 | 接入状态 |
| --- | --- | --- |
| `teacher.py student` / `student_run.py` | 小模型看截至当前检查点的视频帧、独立音轨转写、受众画像与自身先前状态，输出理解和疑问；reviewer 核对知识与媒体依据 | 默认 CLI 的分段诊断 |
| `specific_eval.py` + 配置 `specific_questions` | 三评委读取同一完整视频证据及预先冻结的题目问题／参考，独立评分后汇总 Specific | 已接入 `bench`／`method`／`evaluate`；不是运行时学生提问 |
| `student_questions/pipeline.py` | 学生看 1/4、1/2 或协议指定前缀提出本题问题；judge 看完整媒体与有效问题逐问评分，输出 Specific | 独立研究入口 |
| `student_questions/trajectory.py` | 学生继续观看后回答原问题，记录回答与疑问变化 | 研究协议 |
| `student_knowledge.py` | 用预先冻结的知识点问题检查学生回答及图示对应 | 小规模试验 |

学生观察不含私有答案、judge 反馈和未来视频。提问与评分分离：不把学生自行判断“懂了”作为质量真值。问题要核对题意、前缀可见范围和是否能由完整视频回答；无效问题、失败响应和证据缺失分别记录。最终问题集应在比较不同模型前固定，避免每个模型得到不同难度的考卷。

当前实测学生为 `doubao-seed-2-0-mini-260428`，reviewer 为 `qwen3.8-flash`；学生仍会读错图示关系。更小的本地 VLM 可通过[服务模板](../configs/collaborator.student.local-vlm.example.json)接入，尚不能当作已验证方案。现有[画像](../configs/student_profiles.pilot.json)只覆盖小批题目，不能直接开启 400 题完整学生评估。

配置示例见 [collaborator.student.example.json](../configs/collaborator.student.example.json)。复制到仓库外时同步放置或正确指定画像路径。运行：

```bash
.venv/bin/python teacher.py student --manifest results/my_method/manifest.json --config /path/to/student-services.json --out results/student_review
```

固定题包格式与三评委调用见 [README](../README.md#三评委配置与调用)。示例只有一题的一问，400 题正式题包尚待裁定；自动前缀提问协议仍为研究入口。下一步是冻结逐题题包，用人工标注和受控缺陷校准 judge／学生检错能力。
