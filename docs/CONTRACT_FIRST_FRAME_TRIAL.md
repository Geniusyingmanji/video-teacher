# 可执行知识约束首帧：三题试运行

本地试运行只比较**首帧阶段**，未重新生成 MP4，也未运行 Wan。普通首帧是仓库已有的 `data/first_frames/*.png`；新首帧由同题的结构化知识状态与通用图元渲染器生成。三题是方法原型与故障检查，不足以估计总体优势。

| 题目 | 已有普通首帧 | 契约首帧 | 观察 |
|---|---|---|---|
| 求导 `math_prob_02` | [查看](../data/first_frames/math_prob_02.png) | [查看](../results/contract_first_frame_trial/math_prob_02.png) | 两者公式均清楚。普通首帧已展示完整推导；契约首帧只给前态和本步问题，更符合“从一个可核验步骤开始”的片段设定，但信息量较少，不能据此判视觉质量更好。原有首帧检查记录为 `ERROR`，不作为失败证据。 |
| 凸透镜 `phys_exp_02` | [查看](../data/first_frames/phys_exp_02.png) | [查看](../results/contract_first_frame_trial/phys_exp_02.png) | 普通首帧画了 **4** 条入射光线，题目指定 **3** 条；其 1024×1024 方形画布还需适配 832×480 视频。契约首帧在视频比例下画 3 条平行入射线，焦点 F 在主光轴上。原首帧自动检查给了 `PASS`，但同时记录了“4 而非 3 条”的问题，说明单一总判定会漏缺陷。 |
| NaCl `chem_exp_01` | [查看](../data/first_frames/chem_exp_01.png) | [查看](../results/contract_first_frame_trial/chem_exp_01.png) | 普通首帧在 Na 图下误标 `Cl atom`，并混放反应前后元素；契约首帧只显示准确标名的反应前 Na、Cl，分别有 1、7 个价电子。离子产物属于后续状态，**不能**凭开场首帧认定最终成片正确。原首帧自动检查为 `FAIL`。 |

[并排图：求导](../results/contract_first_frame_trial/comparisons/math_prob_02.png) · [凸透镜](../results/contract_first_frame_trial/comparisons/phys_exp_02.png) · [NaCl](../results/contract_first_frame_trial/comparisons/chem_exp_01.png)。比较图对方形图片使用留边适配，未拉伸原图。

这次比较使用题目要求和肉眼检查，未将旧自动 judge 分数当作两组共同评分器。契约首帧的几何/数量由 `pre_state` 绑定：改动状态中的价电子数会改变绘出的点数；凸透镜的轴、透镜和焦点坐标也从同一状态读取。渲染代码是 [`generation/contract_frame.py`](../generation/contract_frame.py)，运行入口是 [`scripts/render_contract_first_frames.py`](../scripts/render_contract_first_frames.py)。

复现命令：

```bash
python -m scripts.render_contract_first_frames \
  --prompts data/prompts/pilot_v0_1.jsonl \
  --contracts data/teaching_contracts/examples.jsonl \
  --out results/contract_first_frame_trial

python -m scripts.compare_first_frame_arms \
  --baseline data/first_frames \
  --candidate results/contract_first_frame_trial \
  --out results/contract_first_frame_trial/comparisons
```

**还不能得出的结论：**本地没有可直接加载的 Wan 权重；因此纯文本 T2V、普通首帧 TI2V、代码首帧 TI2V 的**最终视频**正确率与学习效果对照尚未运行。现有普通首帧质量有好有坏，代码首帧也仍需专家审核其知识真值。下一步真正的方法对照应冻结题目和人工真值，用同一底座、时长、随机种子策略与预算生成成片，再测首帧到成片的事实保持率。

仓库另有 [Code2Video 本地试跑](../research/code2video/experiments/实验结果.md)：8/8 题最终生成完整的 50–97 秒代码视频，其生成脚本与本地视频可作为**代码视频参照**。这些视频在[样例审计](VIDEO_SAMPLE_AUDIT.md)中仍可见公式叠字、图示错误和排版问题。由于片长与输出介质不同，本试运行没有把它们与 5 秒首帧或尚未生成的像素视频合并成一个质量排名。
