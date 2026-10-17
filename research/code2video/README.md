# Code2Video 调研与本地复现

本目录合并了原 `/root/videoteacher` 的调研与实验。主 Git 仓库为
`/root/video-teacher`；旧路径 `/root/videoteacher` 是本目录的兼容符号链接。
后续请在主仓库提交和推送。

- `主计划.html`、`教学视频生成_统计调研.html`：研究计划与相关工作。
- `Code2Video_调研与试跑.md`：此前记录，最新结果见后续更新。
- `experiments/render_smoke.py`：读取主仓库 `math_exp_01`，用预置 Manim 代码验证作者渲染进程与合片。
- `experiments/code2video-local.patch`：针对作者固定版本的修复及本地模型接口。
- `Code2Video/`：作者源码本地检出，忽略提交，避免嵌套 Git 仓库。

Python/推理环境和模型权重位于仓库外。生成媒体和安装日志保留在本地，
不随 Git 提交。离线渲染成功不代表模型生成成功，也不代表完整方法复现。

最新环境、修复和试跑状态见 [本次试跑更新.md](本次试跑更新.md)。
逐题结果见 [实验结果](experiments/实验结果.md)：首轮完整成功 7/8，单独复跑后 8 题均有完整成片。
四卡并发入口为 `experiments/run_parallel.py`，需先启动 GPU 0 服务；
脚本启动 GPU 1–3 副本，并把 8 个案例分配到四个端点。
完成后运行 `experiments/collect_results.py` 检查解码、收集可提交中间产物，
并导出主仓库评测器兼容的 `experiments/manifest.jsonl`。
