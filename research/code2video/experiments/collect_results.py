"""Verify output files and export a manifest compatible with rise-teacher eval."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import re
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent

if __name__ == '__main__':
    verified = []
    manifest = []
    for result_file in sorted(HERE.glob('model_result_*.json')):
        result = json.loads(result_file.read_text())
        case_id = result['source_case_id']
        log = HERE / f'{case_id}.log'
        if log.exists():
            attempts = re.findall(r'Debugging (section_\d+) \(attempt (\d+)/(\d+)\)', log.read_text())
            counts = {}
            for section_id, attempt, limit in attempts:
                counts[section_id] = counts.get(section_id, 0) + 1
            result['render_invocations_observed'] = counts
        result['token_usage_scope'] = 'parent planner/storyboard/coder calls; excludes worker repair calls'
        initial_file = HERE / 'initial_batch' / f'{case_id}.json'
        if initial_file.exists() and result.get('complete'):
            initial = json.loads(initial_file.read_text())
            if not initial['complete']:
                result['initial_batch_complete'] = False
                result['initial_attempt_elapsed_seconds'] = initial['elapsed_seconds']
                result['cumulative_task_elapsed_seconds'] = initial['elapsed_seconds'] + result['elapsed_seconds']
        video = result.get('video')
        if video and Path(video).is_file():
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                '-of', 'json', video], capture_output=True, text=True, check=True)
            result['ffprobe'] = json.loads(probe.stdout)
            decode = subprocess.run(['ffmpeg', '-v', 'error', '-i', video,
                '-f', 'null', '-'], capture_output=True, text=True)
            result['decode_ok'] = decode.returncode == 0
            result['complete'] = bool(result['complete'] and result['decode_ok'])
            if result['complete']:
                exported = HERE / 'videos' / f'{case_id}.mp4'
                exported.parent.mkdir(exist_ok=True)
                shutil.copy2(video, exported)
                result['exported_video'] = str(exported)
        else:
            result['complete'] = False
        artifacts = HERE / 'artifacts' / case_id
        artifacts.mkdir(parents=True, exist_ok=True)
        source = Path(result['output_dir'])
        for pattern in ('outline.json', 'storyboard.json', 'section_*.py'):
            for path in source.glob(pattern):
                shutil.copy2(path, artifacts / path.name)
        manifest.append(dict(id=case_id, status='ok' if result['complete'] else 'failed',
            video_path=result.get('exported_video', video), model='Code2Video-Qwen3.8-27B',
            protocol='code_video_minutes_no_feedback_no_assets',
            expected_sections=result['expected_sections'], rendered_sections=result['rendered_sections']))
        verified.append(result)
    (HERE / 'verified_results.json').write_text(json.dumps(verified, indent=2))
    (HERE / 'manifest.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in manifest))
    report = ['# 本地 Qwen3.8-27B 试跑结果', '',
        f'已收集 {len(verified)} 道结束任务，完整成片 {sum(r["complete"] for r in verified)} 道。计划总数 8 道。', '',
        '| 题号 | 片段覆盖 | 成片秒数 | 任务累计耗时秒 | 完整解码 |',
        '|---|---:|---:|---:|---|']
    first_batch_file = HERE / 'initial_batch/verified_results.json'
    if first_batch_file.exists():
        first_batch = json.loads(first_batch_file.read_text())
        first_complete = sum(row['complete'] for row in first_batch)
        report[3:3] = ['', f'首轮完整成功 {first_complete}/{len(first_batch)}；后续复跑结果单列保存，最终产物不能当作首轮成功率。']
    for row in verified:
        duration = row.get('ffprobe', {}).get('format', {}).get('duration')
        duration_text = f'{float(duration):.2f}' if duration else '—'
        coverage = f'{row["rendered_sections"]}/{row["expected_sections"]}'
        report.append(f'| {row["source_case_id"]} | {coverage} | {duration_text} | '
                      f'{row.get("cumulative_task_elapsed_seconds", row["elapsed_seconds"]):.1f} | {"通过" if row.get("decode_ok") else "未通过"} |')
    report += ['', '所有任务关闭视觉反馈与外部素材；不能代表完整作者方法复现。',
        '任务耗时包括本地排队、生成、自动修复、渲染和合片，各题并行执行，不能把耗时相加作为墙钟时间。',
        '运行成功不代表教学内容或布局正确。抽帧问题见上级目录的本次试跑更新.md。',
        '父进程 token 统计不包含渲染子进程修复调用，不能当作总成本。', '',
        '首轮结果单独保存在 initial_batch/；复跑使用已缓存大纲和代码，不能作为独立重采样成功率。', '',
        '成片位于本目录 videos/（Git 忽略）；可提交代码、大纲与分镜位于 artifacts/。',
        'manifest.jsonl 可供主仓库评测器读取，尚未执行六维评分或 TeachQuiz。', '']
    (HERE / '实验结果.md').write_text('\n'.join(report))
    metrics = HERE / 'gpu_metrics.csv'
    if metrics.exists():
        by_gpu = {}
        initial_by_gpu = {}
        initial_end = (HERE / 'parallel_result.json').stat().st_mtime if (HERE / 'parallel_result.json').exists() else None
        for row in list(csv.reader(metrics.open()))[1:]:
            if len(row) != 5:
                continue
            by_gpu.setdefault(row[1].strip(), []).append(float(row[2].strip().split()[0]))
            if initial_end and datetime.strptime(row[0], '%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=timezone.utc).timestamp() <= initial_end:
                initial_by_gpu.setdefault(row[1].strip(), []).append(float(row[2].strip().split()[0]))
        summary = {gpu: {'samples': len(values), 'mean_utilization_percent': sum(values)/len(values),
                         'peak_utilization_percent': max(values)} for gpu, values in by_gpu.items()}
        (HERE / 'gpu_summary.json').write_text(json.dumps(summary, indent=2))
        initial_summary = {gpu: {'samples': len(values), 'mean_utilization_percent': sum(values)/len(values),
                                'peak_utilization_percent': max(values)} for gpu, values in initial_by_gpu.items()}
        (HERE / 'gpu_summary_initial_batch.json').write_text(json.dumps(initial_summary, indent=2))
    print(json.dumps({'cases': len(verified), 'complete': sum(r['complete'] for r in verified)}, indent=2))
