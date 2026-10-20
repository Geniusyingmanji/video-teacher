# 本地完整研究原型 v1

第一版的可运行范围是 **60 题短教学片段研究原型**：题目与首帧、三份可执行教学契约生成的 5 秒代码视频、一个三分支交互教学样例、已有 Wan 自动评分、已有 Qwen3-VL 代理测验结果，以及独立的长视频样例审查。统一入口把这些真实资产联起来，保留原始数据与结论边界。

## 一条命令重建本地交付物

在仓库根目录运行：

```powershell
python -m scripts.build_v1
```

打开生成的 `results/v1/index.html`。构建会写入：

| 文件 | 用途 |
| --- | --- |
| `results/v1/index.html` | 本地浏览入口：题目覆盖、契约画面、交互和已有评测。 |
| `results/v1/manifest.json` | 可机器读取的题数、分布、证据覆盖、输入 SHA-256 和边界。 |
| `results/v1/contract_frames/` | 三份契约的初始与结果画面。 |
| `results/v1/videos/` | 三条实际编码、重新解码核验的 5 秒无声 MP4。 |
| `results/v1/interactive_lesson.html` | 独立交互教学实验，可导出本次作答记录。 |

该命令不调用云服务、不下载模型。它实际生成三条确定性代码视频，并检查 MP4 帧数、时长和首尾画面；不会重新运行 Wan 像素视频生成或模型评分。评测表读取仓库中已有的 `results/`，因此表格展示的是既有实验记录。对每个评分配置，构建器核对逐题文件、汇总文件和 60 题 ID 交集；缺失配置会在页面中显示，不会自动当作完成。

## 研究流程与输入

1. **题目与首帧**：`data/prompts/pilot_v0_1.jsonl` 有 60 个唯一题目，涵盖 12 学科；`data/first_frames/` 有相应的 60 张原始首帧。第一版还保留原始题目的课程内容范围，不能把 3–5 秒成片当作完整讲解。
2. **知识约束与代码成片**：`data/teaching_contracts/examples.jsonl` 仅有 3 份示范契约。构建器验证断言、时长与画面布局后，输出前后态图像，并按约 40% 前态、60% 后态编码成 5 秒无声视频。这是可复现的代码视频基线，尚不是自动生成完整讲解的像素模型。契约内部自洽不等于外部科学真值已由专家认证。
3. **交互教学**：`data/interactive/convex_lens.json` 基于凸透镜契约产生 3 个条件分支，学生先预测后揭示。作答记录只在浏览器中，可下载 JSON。
4. **视频生成与评测**：Wan 生成入口为 `generation.runners.wan_runner` 和 `generation.runners.wan_ti2v_runner`，自动评分入口为 `eval.run_eval`，代理测验入口为 `eval.run_teachquiz`。这一步需要相应模型、视频产物及计算资源；离线构建器不会伪造这些产物。
5. **人工审查**：人工评分导出与分析入口在 `scripts/human_eval.py`。已有的 8 条 Code2Video 长视频审查见 [`VIDEO_SAMPLE_AUDIT.md`](VIDEO_SAMPLE_AUDIT.md)，与短片 benchmark 分轨记录。

## 第一版能回答什么

已有 60 题、五组 Wan 短片自动评分配置及两组 Qwen3-VL 代理测验记录，足以演示题目、评测、分析和知识状态生成接口如何衔接。三维与六维评分配置不能直接按总分比较。当前代理测验使用**各模型输出后生成**的视觉题，因此它反映模型特定的感知性诊断，不能用于跨模型公平排名或人类学习收益结论。统一页面将该限制与证据数字放在一起。

要把原型升级成可公开发布的研究基准，还需真人评分、冻结且共用的测验题包、独立视频模型家族、同题同条件的 TI2V 对照、专家真值审查与素材授权核查。这些是待收集的证据，不属于本地构建成功的含义。

## 验收

```powershell
python -m scripts.build_v1
python -m unittest discover -s tests -p test_interactive_lesson.py -v
```

构建输出应报告 `60 prompts`、`7/7 evidence arms`、`3 validated contracts`。页面应能从文件系统直接打开，三条 MP4 应各为 120 帧、5 秒，交互页能完成“选择条件 → 预测 → 揭示 → 下载记录”。如果未来替换了评测数据，重新构建后检查 `manifest.json` 中每个配置的 `rows`、`aggregate_n`、`pilot_overlap` 与 `consistent`；不一致时先修复数据再做比较。
