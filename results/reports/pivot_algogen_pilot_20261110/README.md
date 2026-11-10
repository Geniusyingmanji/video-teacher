# PIVOT 与 ALGOGEN 实际试跑

当前阶段：环境准备通过，等待 results/code2video_eight_full_eval_20261110/eval/aggregate.json 后自动启动两种作者流程。状态见 results/pivot_algogen_pilot_20261110/state.json。

- PIVOT：作者 CLI，英文 The determinant，保留教学脚本、事实检查、测验、Manim、英文 TTS 与合片。独立环境 /root/pivot-env，作者提交 ffc28ae3d05e2f2f2c3e58dc38e9aca7f1ac1d0b。
- ALGOGEN：作者 run_pipeline.py，原始 sorting_leetcode_179_seed_02 示例，保留 tracker → trace → RSL → Manim → AES。独立环境 /root/algogen-env，作者提交 1bb093c76499135ecf54fc8030219a4e7ee4424c。

全部作者聊天模型显式替换为四卡本地 Qwen3.8-27B，关闭 thinking，原先未指定的输出预算设为 8192，其余作者输出预算保留。适配器只在设定 REPRO_CHAT_LOG 与 REPRO_LOCAL_PORTS 时启用，逐调用保存原模型名、完整提示、实际模型配置、响应或流及异常。不是原 API 模型成绩，也不是论文全基准复现。

环境修复：PIVOT 原 numpy==1.26.4 与 manim==0.19.1 冲突，改为 numpy==2.2.6；原 edge-tts==7.2.8 访问语音服务返回 403，升级到已验证的 7.3.1。保留源码差异。ALGOGEN 需要将作者 renderer 目录加入 PYTHONPATH 才能找到 manim_renderer；不改算法或提示。

已验证 PIVOT 作者 TTS 服务真实生成英文语音，六项作者测试通过；两个 CLI 均可加载。以上准备检查不代表模型试跑完成。

实际产物与失败保留在 results/pivot_algogen_pilot_20261110/{pivot,algogen}/。完整解码通过的成片分别交付 delivery/最终视频/PIVOT_试跑/ 和 delivery/最终视频/ALGOGEN_试跑/，不混入中间片段。完成后会记录方法结果、媒体信息、作者会话或 AES、抽帧，并自动推送结果报告。渲染成功、作者流程完成、英文语音与教学质量验收分开报告。
