# 英文有声教学视频 v2 / 评分 v9

新版题库 `candidate_400_lessons_v2.jsonl` 沿用 60/120/180 秒预算、知识讲解与解题分类，
400 题全部要求英文旁白。无声 v1 和五秒原题继续保留。当前用户约束是：
**只使用 GPU 0、1，GPU 2、3 完全空闲，连驻留服务也不能占用。**

## 配音与内容

每个章节必须有真实可朗读的 `narration`，与该章图示、推理和操作顺序一致。
默认普通英文合成音色 `en-US-AriaNeural`，没有自定义声音或真人模仿。
解题旁白解释条件、策略、操作理由、单位和结果核查；知识讲解旁白解释关系与机制，
不能只读屏幕标签。字幕另存 SRT，当前不烧录到画面。

使用 [edge-tts](https://github.com/rany2/edge-tts) 在线合成每章语音，在 CPU 上解码并按章节
时间点组合。语音太长时有界改写讲稿，不截断、不大幅变速、不拖长画面。每章实际合成
语音应占章节时间至少 45%，完整放在章节内，总覆盖率也须至少 45%。这是初始工程门槛，
没有独立人工校准，不是最优语速或最佳内容密度结论。

旁白 WAV 对应目标时长，AAC 音轨封装到视频；视频流直接复制，保留原来的解码帧。
渲染、原图保护、章节时间点、布局和内容核查继续保留。出现语音服务故障、缺失讲稿或
时长溢出时记录失败，不能退回无声视频并宣称成功。

配乐默认关闭。明确提供 `background_music_path` 时可选低音量混入独立素材，增益 0.025；
不能以配乐代替旁白。题目不自动下载或选择音乐。

## 实际音轨与评分

用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 对**实际提交视频音轨**做 CPU/int8
语音识别，保存语言、置信度、文本及词级时间戳。本地使用多语种 base 模型，权重哈希
和模型配置进入评测缓存标识。识别失败或置信度不足不能通过。

逐窗口画面审查收到相应时间范围的实际识别文本。全片另核查口述正确性、关键解释覆盖、
音画对应和讲解节奏，必须引用真实语音片段与画面窗口。口述严重错误不能被清晰画面
或其他高分抵消。配乐、提示音或答案朗读不能满足有声教学验收。总体分同时受原八轴、
视频呈现和口述教学最低分约束。

末帧对照两种呈现保留相同旁白，只比较运动画面贡献的信息，不把旁白优势计作动画优势。
ASR 是代理，不等于直接听音或人工发音评估；术语可能被误识别，同模型语义判断仍可能
出错。没有真人学习效果实验或独立人工校准。

## 环境与两卡十题实测

```bash
python -m pip install -r requirements-local-generation.txt
python -c 'from faster_whisper.utils import download_model; download_model("base", output_dir="/root/models/faster-whisper-base")'
python scripts/build_lesson_prompts.py --language en-US
python scripts/preflight_candidate400.py
python -m unittest discover -s tests -v
python scripts/select_lesson_cases.py
python scripts/run_qwen_multigpu.py --gpus 0 1 --ports 8000 8001 \
  --prompts data/prompts/lesson_validation_10_v2.jsonl \
  --out results/optimization_20261103/narrated_lessons10_gpu01_v2 --max-attempts 1
```

先完成代码及检查，再冻结十题启动。一分钟四题、两分钟三题、三分钟三题，知识讲解
和解题各五题，包含简单、标准、较难任务及原图操作。这是预定义覆盖验证，不是随机
抽样或 400 题全量实测。首轮每题一次外层尝试，保留内部有界修复和所有失败证据。

大纲输出独立限制为 2048 tokens，分镜为 6000，代码为 8192；详细教学由实际分镜、
图示和旁白展开。GPU 0、1 各有一个 Qwen vision 服务，TTS 组合和 ASR 使用 CPU。
生成、音轨验证、任务完成与质量通过分别报告，以 completion.json、逐题报告和语音
证据为准，不能用少量有效高分代替十题完成。
