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

场景程序是受约束的 JSON；当前不直接执行任意模型 Python。状态和关系工具保证声明关系的执行，模型对题意、对象和关系的选择仍可能错误。最终评测重新读取实际媒体；当前生成和视觉 judge 使用同类模型，不能称为跨模型家族独立验证。

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
