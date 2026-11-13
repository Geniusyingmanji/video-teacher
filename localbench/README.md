# 当前源码导航

当前代码按职责索引如下。

先看 [teacher.py](../teacher.py) → [run.py](run.py)。Benchmark 概念见[评测导航](../docs/benchmark.md)，生成方法见[方法导航](../docs/method.md)，当前成熟度见[状态快照](../docs/status.md)。

`pipeline.py`、`run.py` 等仍承担多个职责；下面按主要用途归类。可选关系工具和研究原型并非全部由默认 CLI 使用。源码中的 rubric 是唯一运行定义，详细准则同时列于评测文档。

## 入口、编排与运行记录

[run.py](run.py), [common.py](common.py), [preflight.py](preflight.py), [provenance.py](provenance.py), [api_usage.py](api_usage.py), [services.py](services.py), [client.py](client.py)。

## 题库、公开输入与人工审核

[prepare.py](prepare.py), [split.py](split.py), [audit.py](audit.py), [audit_coverage.py](audit_coverage.py), [reference_contract.py](reference_contract.py), [reference_report.py](reference_report.py), [source_audit.py](source_audit.py)。

## General：评分协议与汇总

[rubric.py](rubric.py), [detailed_rubric.py](detailed_rubric.py), [strict_anchors.py](strict_anchors.py), [applicability.py](applicability.py), [judge.py](judge.py), [verification.py](verification.py), [requirements.py](requirements.py)。

## 成片证据与音频

[evidence.py](evidence.py), [asr.py](asr.py), [alignment.py](alignment.py), [transcript_guard.py](transcript_guard.py), [transcript_validity.py](transcript_validity.py), [pixel_regions.py](pixel_regions.py), [region_review.py](region_review.py), [program_consistency.py](program_consistency.py), [relation_audit.py](relation_audit.py), [source_changes.py](source_changes.py), [source_observation.py](source_observation.py), [source_region.py](source_region.py), [claim_scope.py](claim_scope.py), [literal_visual_probe.py](literal_visual_probe.py)。

## Specific 与学生

[student.py](student.py), [student_run.py](student_run.py), [student_protocol.py](student_protocol.py), [student_keyed.py](student_keyed.py), [student_retention.py](student_retention.py), [student_knowledge.py](student_knowledge.py), [student_perception.py](student_perception.py)。

## 生成规划与重渲染

[pipeline.py](pipeline.py), [native_pipeline.py](native_pipeline.py), [scene.py](scene.py), [rerender.py](rerender.py), [assets.py](assets.py), [timing.py](timing.py)。

## 配音与教学语言

[tts.py](tts.py), [speech.py](speech.py), [math_speech.py](math_speech.py), [spoken_units.py](spoken_units.py), [semantic_speech.py](semantic_speech.py), [fixed_scene_speech.py](fixed_scene_speech.py), [teaching_cues.py](teaching_cues.py), [content_review.py](content_review.py)。

## 领域状态与视觉组件

[state.py](state.py), [geometry.py](geometry.py), [chart.py](chart.py), [flow.py](flow.py), [triangle.py](triangle.py), [triangle_examples.py](triangle_examples.py), [keyboard.py](keyboard.py), [keyboard_bridge.py](keyboard_bridge.py), [contact_pair.py](contact_pair.py), [nephron.py](nephron.py), [bond.py](bond.py), [voice.py](voice.py), [source_scene.py](source_scene.py), [source_graph.py](source_graph.py)。

## 反馈与版式约束

[visual_agent.py](visual_agent.py), [refine.py](refine.py), [layout_repair.py](layout_repair.py), [label_repair.py](label_repair.py), [layer_order.py](layer_order.py), [arrow_direction_guard.py](arrow_direction_guard.py), [layout_audit.py](layout_audit.py), [layout_geometry.py](layout_geometry.py), [stroke_style.py](stroke_style.py), [stroke_preflight.py](stroke_preflight.py), [stroke_visibility.py](stroke_visibility.py)。

## 关系编译与开发原型

[object_connections.py](object_connections.py), [connection_instances.py](connection_instances.py), [apparent_size.py](apparent_size.py), [public_spans.py](public_spans.py), [artifact_plan.py](artifact_plan.py), [anchored_routes.py](anchored_routes.py), [mechanism_chain.py](mechanism_chain.py), [mechanism_binding.py](mechanism_binding.py), [causal_chain.py](causal_chain.py), [lesson_revision.py](lesson_revision.py), [transfer_bridge.py](transfer_bridge.py), [atmospheric_bridge.py](atmospheric_bridge.py), [relation_support.py](relation_support.py), [relation_witness.py](relation_witness.py), [compass_diagram.py](compass_diagram.py)。

## 空间表示与约束

[spatial_graph.py](spatial_graph.py), [spatial_solver.py](spatial_solver.py), [spatial_contract.py](spatial_contract.py), [spatial_plan.py](spatial_plan.py), [spatial_revision.py](spatial_revision.py), [spatial_correspondence.py](spatial_correspondence.py), [spatial_inversion.py](spatial_inversion.py), [spatial_view_narration.py](spatial_view_narration.py)。

## 评测控制与报告

[controls.py](controls.py), [region_controls.py](region_controls.py), [spoken_controls.py](spoken_controls.py), [control_report.py](control_report.py), [delivery.py](delivery.py), [compare.py](compare.py), [human.py](human.py), [human_agreement.py](human_agreement.py), [import_run.py](import_run.py)。

## 原生视频接口（服务实测暂缓）

[video_api.py](video_api.py)。

## 问题协议子包

- [student_questions/protocol.py](student_questions/protocol.py)：前缀提问、适用性与逐问评分协议。
- [student_questions/pipeline.py](student_questions/pipeline.py)：证据、问题包及评分编排。
- [student_questions/trajectory.py](student_questions/trajectory.py)：学生对原问题的连续回答。
- [student_questions/pool_recovery.py](student_questions/pool_recovery.py)：题包条目失败与恢复处理。

这些研究协议尚未全部替换默认学生 CLI；近期固定四问知识点试验也不能称为自动前缀问题池。

