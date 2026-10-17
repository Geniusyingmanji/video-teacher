# Code2Video 调研与试跑记录

日期：2026-10-17。本文下方为早期网络受限时的记录，已被本次联网试跑更新；最新结果见 `本次试跑更新.md`。当前已克隆作者源码、安装独立环境并部署 Qwen3.8-27B；四卡首轮 7/8 题完整成功，修复验证逻辑并复跑后已有 8 道完整成片。

补充复查：`/proc/driver/nvidia/gpus/*/information` 能读到宿主机四张 NVIDIA A100 80GB PCIe 的信息，证明硬件存在；当前容器没有暴露 `/dev/nvidia*`，`nvidia-smi -L` 无法连接驱动。不能将当前容器不能访问 GPU 等同于机器没有 GPU。

实际下载尝试：Miniconda 官方安装包下载失败，`Could not resolve host: repo.anaconda.com`；再次克隆用户仓库仍为 GitHub DNS 失败。通过 `apt-get download python3-minimal` 下载也失败，软件包下载进程报 `setgroups ... Operation not permitted`。未绕过沙箱或修改系统限制，依赖尚未安装。

## 本地资料与仓库

已阅读 `主计划.html` 和 `教学视频生成_统计调研.html`。本地 `videoteacher/` 只有这两份 HTML，不是 Git 仓库。用户随后确认远程为 https://github.com/Geniusyingmanji/video-teacher.git 。

已尝试克隆到 `/root/video-teacher`，退出码 128：`Could not resolve host: github.com`。浏览工具能够打开公开仓库页面；在线 README 显示这是教学视频生成与评测项目，包含 data、generation、eval、docs 等目录。未获得完整本地检出，未将在线阅读视为拉取成功。此前列出的待办中，仓库地址已经解决。

Code2Video 官方仓库：https://github.com/showlab/Code2Video

与主计划的关系：作为代码生成教学视频的参照，检查教学步骤、可执行状态和画面布局。按主计划要求，分钟级教程与 3–5 秒像素视频应分别报告，不能直接用完整片总分排名。首轮拟采用官方示例主题 `Linear transformations and matrices`，之后再对齐本项目同题提示。尚未进行实验，不报告成功率、耗时或生成成本。

## 官方实现核对

流程：知识点 → 大纲 → 分镜 → Manim 代码 → 渲染与修复 → 可选视觉反馈 → FFmpeg 合片。源码使用低质量渲染参数，片段查找路径包含 `480p15`。单题 shell 默认同时开启素材、视觉反馈和并行；最小排障可直接使用 agent.py 关闭这些选项。具体参数见 [agent.py](https://github.com/showlab/Code2Video/blob/main/src/agent.py) 和 [单题脚本](https://github.com/showlab/Code2Video/blob/main/src/run_agent_single.sh)。

依赖重点：Manim 0.19.0、ManimPango 0.6.0、OpenAI SDK 1.90.0、NumPy 2.2.6，以及图像/视频处理库；没有必要为这个 API 驱动流程安装本地大模型。系统还需可用的文本/图形编译依赖和 FFmpeg；使用数学公式时应检查 LaTeX。完整版本以 [requirements.txt](https://github.com/showlab/Code2Video/blob/main/src/requirements.txt) 为准，当前尚未验证依赖解析。

API 由 `src/api_config.json` 配置。[请求实现](https://github.com/showlab/Code2Video/blob/main/src/gpt_request.py)支持按服务名读取环境变量；其中部分请求使用 AzureOpenAI，Claude 分支使用 OpenAI 兼容客户端，不能假定任意官方厂商密钥直接适配所有分支。反馈分支需视频与图片输入能力。配置需结合实际可用端点核对。

源码静态发现，尚未通过运行验证：

- `agent.py` 按 CASES 上级查找 json_files 和 assets，但仓库顶层展示了这些目录；克隆后先核对 src 下相应路径，再决定链接或路径修复。
- 并行渲染在子进程重建 Agent，序列化状态没有包含已生成 section_codes；可能导致渲染阶段缺失代码状态，需重点验证。
- 视觉反馈异常会返回“无问题”状态，部分失败会被捕获；退出码或成功文案不足以验收，必须检查片段数和实际 MP4。
- 入口会打印素材 API key，配置真实凭据前应移除该输出。

## 本次实际尝试

执行：

```sh
git clone --depth 1 https://github.com/showlab/Code2Video.git /root/videoteacher/Code2Video
```

结果：退出码 128，`Could not resolve host: github.com`。环境声明 `CODEX_SANDBOX_NETWORK_DISABLED`，终端不能联网；浏览工具可以读取公开页面，但不等于终端能克隆或下载依赖。没有尝试绕过网络限制。

环境检查：`python`、`python3`、`pip3`、`uv`、`manim`、`ffmpeg` 均未找到；未发现模型 API 配置环境变量。未读取或输出任何密钥。原始环境检查见 `Code2Video_环境检查.log`。

## 环境具备后的复现步骤（未执行）

1. 克隆 https://github.com/Geniusyingmanji/video-teacher.git 到独立目录，比较本地两份调研，保留现有文件。
2. 在允许联网且有 Python 的机器克隆官方 Code2Video，记录 `git rev-parse HEAD`，建立独立虚拟环境，按 requirements 安装；验证 Manim、FFmpeg、文本和公式渲染。
3. 核对资源路径、上述静态问题和端点协议，配置实际可用模型。不要将真实密钥提交到 Git。
4. 首次仅运行一个主题，限制重试，先关闭反馈与素材；以下命令仅验证基础链路，不代表完整方法复现：

```sh
cd /root/videoteacher/Code2Video/src
python3 agent.py --API gpt-41 \
  --knowledge_point 'Linear transformations and matrices' \
  --folder_prefix VIDEOTEACHER-smoke \
  --no_feedback --no_assets --no_parallel \
  --max_fix_bug_tries 2 --max_regenerate_tries 2
```

`--no_parallel` 只关闭知识点批处理并行；片段渲染仍使用进程池。若静态发现的状态问题复现，需要先修复再继续。

5. 验收大纲、分镜、每段代码、片段覆盖率和合片，用 ffprobe 检查文件时长与分辨率并抽帧看布局；逐项检查教学顺序、数学正确性和关键状态。基础链路通过后再开启视觉反馈，分别记录生成耗时、修复轮数和调用成本。

缺少条件：允许联网的 Python/Manim 运行环境，以及与代码协议匹配的模型端点配置。远程地址已确认。
