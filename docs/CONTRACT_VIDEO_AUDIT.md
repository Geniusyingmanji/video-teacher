# 契约视频逐帧审查

运行 `python -m scripts.build_v1` 后，查看 `results/v1/contract_video_audit.jsonl`。构建器会重新读取三段实际 MP4，对照契约编译出的 120 帧时间线；任何一段未通过就停止构建。

也可单独检查保存后的文件：

```powershell
python -m eval.contract_video_audit --case-id math_prob_02 --video results/v1/videos/math_prob_02.mp4
```

命令会输出 JSON；未通过时返回非零退出码。

每条记录提供 `status`、`reason`、各阶段失败帧数，以及带帧号和秒数的 `evidence`：

| 状态 | 含义 |
| --- | --- |
| `pass` | 全部解码帧与契约画面相符，允许 MP4 编码误差。 |
| `missing` | 结果阶段多数帧仍更接近初始画面，预期结果没有出现。 |
| `wrong` | 画面与契约时间线不符，且不能归为停留在初始画面。 |
| `unobservable` | 文件打不开、视频规格不符或部分帧无法解码。 |

审查按画面中有内容或预计发生变化的区域计算误差，避免白色背景掩盖小公式或细线缺失。它只能检查这三条**确定性代码渲染**视频是否按契约播放；不能直接给 Wan 等生成模型的视频判科学正确性，也不能代替学科专家审查契约本身。

可运行 `python -m unittest discover -s tests -p test_contract_video_audit.py -v` 验证停在初始画面、黑屏和缺失文件的判定。
