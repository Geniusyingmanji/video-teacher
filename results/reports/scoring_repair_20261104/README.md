# 2026-11-04 评分链路修复与固定十题复评

当前状态以 `validation_latest.json` 为准。基础修复代码提交：`64ae386`；终止 token 防护及完整回归记录：`c48536b`、`f695577`。完整测试 224 项通过，日志见 [full_tests_20261105.log](full_tests_20261105.log)。

2026-11-05 状态：基础十题评分及离线结构审计完成，严重缺陷复核仍在运行。五条成片、五条生成失败记录均保留。复核完成前，部分逐题结果不作为最终汇总或教学质量验收。

## 结果位置

- [最终基础评分](compact_final/aggregate.json)与[逐题证据](compact_final/per_case.jsonl)。
- [逐题复核检查点](compact_verified_v3/per_case.jsonl)；完成后将生成 `compact_verified_v3/aggregate.json`。
- [基础评分离线证据审计](compact_final/evidence_audit.json)通过；仅验证来源、引用和计算，不证明模型观察必然正确。
- [五条可播放英文旁白视频](../../../delivery/README.md)。
- [修复细节](../../../docs/SCORING_REPAIR_20261104.md)。

`final/`、`verified/`、`compact_verified/`、`compact_verified_v2/` 和根目录旧评分、旧进度文件是修复前及中断过程的历史记录，不作为最终验收结论。`compact_context_probe.json` 和 `compact_completion_probe.json` 仅验证最长案例的请求容量与引用 schema，不作为视频总分。

## 可复现输入

[prompts.jsonl](prompts.jsonl) 保留原十题；[delivery_manifest.jsonl](delivery_manifest.jsonl) 使用仓库内视频相对路径，原始 manifest 另存 [generation_manifest.jsonl](generation_manifest.jsonl)。五条失败生成记录不替换，不制造零分。

在仓库根目录配置兼容的视觉评委与 ASR 后运行：

```bash
python -m eval.run_benchmark_v2 \
  --prompts results/reports/scoring_repair_20261104/prompts.jsonl \
  --manifest results/reports/scoring_repair_20261104/delivery_manifest.jsonl \
  --out results/local_reproduction --workers 4 \
  --judge-base-url http://127.0.0.1:8000/v1 \
  --judge-base-url http://127.0.0.1:8001/v1
```

基础评分结束后，执行严重缺陷复核和离线审计：

```bash
python scripts/verify_benchmark_scores.py \
  --base-dir results/local_reproduction \
  --prompts results/reports/scoring_repair_20261104/prompts.jsonl \
  --out results/local_verified --workers 2 \
  --judge-base-url http://127.0.0.1:8000/v1 \
  --judge-base-url http://127.0.0.1:8001/v1
python scripts/audit_score_evidence.py \
  --results results/local_verified/per_case.jsonl \
  --prompts results/reports/scoring_repair_20261104/prompts.jsonl \
  --out results/local_verified/evidence_audit.json
```

本轮为 Qwen3.8-27B 同模型生成和复核。结构校验、ASR 和采样帧复核不能替代直接听音、独立专家标注或跨模型校准。区分执行完成、生成成功、有效评分与教学质量验收。

本地 Qwen/xgrammar 若复现终止 token 被拒绝的 HTTP 500，可在上述复核命令增加 `--structured-stop-token-id 248046 --structured-stop-token-id 248044`。这些 ID 仅适用于已确认的当前 tokenizer；其他评委默认不启用。详见[终止 token 防护说明](../../../docs/SCORING_REPAIR_20261104.md)。
