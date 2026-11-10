# 其他教学视频生成项目：复现筛选（2026-11-10）

核查作者论文、官方仓库、源码入口、依赖与版本；以下是可行性判断，不是已经运行成功的复现结果。当前四卡在给八条 Code2Video 视频执行 quality-v12 全片评分，未启动其他项目推理，避免争抢评测服务。

建议顺序：PIVOT → TheoremExplainAgent → ALGOGEN。前两者重点检验完整有声讲解，第三个检验算法过程与中间状态的可验证性。所有本地 Qwen 替换均需单独标注，不能作为原论文 API 模型成绩。

| 项目 | 匹配的任务 | 已核实的执行资产 | 当前主要障碍 | 建议 |
|---|---|---|---|---|
| PIVOT | 带旁白的 STEM 讲解、测验、针对错误的补讲 | 安装包、CLI、Manim、TTS、修复及组合源码 | edge-tts 需联网；需验证 Qwen 输出、分镜完整性与音画同步；独立依赖环境 | 第一优先，先一题有声成片 |
| TheoremExplainAgent | 长篇定理与概念可视化 | 生成与评测入口、Manim、Kokoro 旁白、可选 RAG | 旧依赖栈；LiteLLM 多模态格式与本地模型适配；RAG 资料需另取 | 第二优先，先复现不带 RAG 的明确配置 |
| ALGOGEN | 算法执行过程与结构化动画 | tracker → trace → RSL → Manim 流程及示例 | SiliconFlow 地址和模型硬编码，需改端点；未确认完整讲课旁白 | 第三优先，排序/图遍历的过程对照 |
| Paper2Video（Show Lab） | 论文变带讲解的演示视频 | 完整版与无数字人轻量版入口，语音与游标源码 | LaTeX 论文及参考音频、F5-TTS/WhisperX 权重和独立环境 | 第二阶段，先轻量版 |
| VisualEDU | 数学题逐步解答与动画反馈 | 公开生成、渲染反馈与视觉反馈代码 | main.py 未填写参数导致语法错误；Windows 硬编码路径；引用 library 模块但当前文件清单缺失 | 可研究，不能直接宣称可运行 |
| Preacher（Gen-Verse） | 论文视频摘要、多种视觉素材 | run_pdf.py、规划与工具调用代码 | 默认工具涉及外部 TTS、视频和数字人 API，需凭据及服务替换 | 暂后，当前资源下不如前两者直接 |
| ManimCode | 对已渲染教学动画做视觉自修复 | 作者论文与项目展示 | 作者页面仍写代码和 ManimData 将发布，未核实可下载的完整实现/权重 | 跟踪，不列作现在可复现的方法 |

## PIVOT：最贴近当前有声教学任务

[作者论文](https://arxiv.org/abs/2609.24083)的脚注直接链接到[官方仓库](https://github.com/Chloe-mxxxxc/Pedagogy-Guided-Generative-Video-Tutors-for-STEM-Learning)。已固定 `ffc28ae3d05e2f2f2c3e58dc38e9aca7f1ac1d0b`，许可证 Apache-2.0。核查了 config.py、llm_client.py、tts_service.py、pipeline.py 和 pyproject.toml，存在 OpenAI 兼容地址与模型配置、英文 TTS、场景级音画组合、测验和后续补讲入口。

建议先用现有“行列式”或“基变换”主题，英文、完整旁白，走作者正常教学生成路径；后续再测错题补讲。先验证 TTS 联网和最终音轨，再运行分镜。默认模型改为本地 Qwen 应作为方法适配记录；不要关闭事实与测验检查来追求通过率。CLI 的 dry-run 只能验证计划，不等于生成成功。

## TheoremExplainAgent：成熟的有声 Manim 比较对象

[官方仓库](https://github.com/TIGER-AI-Lab/TheoremExplainAgent)明确提供单题、批量和评测入口，MIT；固定 `e9ece5db7756b6ded8a812eceeb936cfd02aae21`。源码和依赖包含 Manim 0.18.1、manim-voiceover、Kokoro 服务与 LiteLLM。旁白可采用作者公开 Kokoro 模型，避免将无声渲染当作完整讲解。

本地适配仍需检查 LiteLLM 的模型命名、端点及图像消息路径，不能只改 API key。RAG 文档及嵌入依赖属于额外设置；首轮明确标为无 RAG 配置，随后再补对应消融。另建环境，不覆盖当前 Code2Video 环境。

## ALGOGEN：验证执行状态而不是只看成片

[官方仓库](https://github.com/MAC-AutoML/ALGOGEN-lab)提供 `run_pipeline.py`，会运行生成的 tracker 并产生 trace.json，之后生成 RSL 和渲染配置再成片；固定 `1bb093c76499135ecf54fc8030219a4e7ee4424c`。静态检查 `toolmaker/tool_maker_agent.py` 发现 SiliconFlow 地址与 DeepSeek-V3.2 模型硬编码。改为 Qwen 必须保留补丁与替换说明，并逐一核查追踪、风格生成与评测调用，而非仅修改一个客户端。

建议排序与图遍历各一题，核对每一步数组或图状态、最终答案和视频状态对应关系。其定位是算法可视化，不能因运行成功就声称具备完整旁白讲课。仓库 API 未识别许可证；论文中许可证描述不替代实际仓库文件核验。

## 其他候选的复现边界

[Show Lab Paper2Video](https://github.com/showlab/Paper2Video)固定 `47beb503e24218f8f8b3075f5d2bed7844d199b4`，MIT。先走 `src/pipeline_light.py`，保留演示文稿、语音和游标，避免先引入数字人环境。已核查 `src/speech_gen.py` 调用 F5-TTS 与 WhisperX；现有四卡大部分显存被 Qwen 服务占用，后续部署语音模型需规划显存，不能只按机器总显存判断可用性。

[VisualEDU](https://github.com/UchihaIchigo/VisualEDU)固定 `9f130301d1477d0ed2c4f6f17c3cf8cd0296ddcb`。静态解析 main.py 在未赋值的 `num =` 处失败；还含 `D:\DeepL_code\...` 路径并引用当前树中缺失的 library.py。API 调用支持自定义 base_url，但必须修复入口、路径与缺失组件后才有可运行性证据。它更适合解题逐步覆盖比较，不直接替代完整讲课系统。

[Preacher](https://github.com/Gen-Verse/Paper2Video)固定 `1cc86fb3076181267c989337b0995bf0b65362d0`，有实际源码，并非仅论文展示。其默认配置依赖多个外部生成服务，完全本地替换会明显改变系统，因此暂后。

[ManimCode 作者页](https://liang-zhengyang.github.io/manimcode/)截至本次核查仍标注代码及数据将发布；有论文结果不等于已有完整复现资产。另注意 Show Lab Paper2Video、Gen-Verse Preacher 和众多同名社区 paper2video 是不同项目，不混用成果或安装指令。

## 记录与最小试跑验收

源码清单、固定提交与所检查文件的 Python 语法结果保存在 `results/reports/reproduction_candidates_20261110/repository_audit.json`，下载的检查用源码在 `/root/research/reproduction_candidates_20261110/`。本次未安装或执行候选方法，也未产生候选方法新视频。

后续每个方法至少保存：原始题目、作者配置、模型替换、代码版本、依赖、全部模型请求及失败、分镜覆盖、完整解码、音轨与实际英文语音、八轴评分与教学缺陷证据。优先匹配已有主题与要求，不硬对齐作者不支持的任务，也不根据预期高低分换题。
