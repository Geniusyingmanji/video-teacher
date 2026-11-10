"""Export the eight-video evaluation, optionally waiting and publishing reports."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['向量基础', '点积与对偶', '行列式', '矩阵乘法', '特征向量与特征值', '基变换', '分形维数', '斯涅尔定律']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    run = args.run.resolve()
    target = ROOT/'results/reports'/run.name
    expected = {json.loads(line)['id'] for line in (run/'prompts.jsonl').read_text().splitlines() if line.strip()}
    deadline = time.monotonic() + 21600
    while True:
        source = run/'eval/per_case.jsonl'
        rows = {}
        if source.is_file():
            for line in source.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    rows[row['id']] = row
        if set(rows) == expected and (run/'eval/aggregate.json').is_file():
            break
        if not args.wait or time.monotonic() > deadline:
            raise RuntimeError(f'Evaluation incomplete: {len(rows)}/{len(expected)}')
        time.sleep(30)
    target.mkdir(parents=True, exist_ok=True)
    for name in ['prompts.jsonl', 'manifest.jsonl', 'run_plan.json']:
        shutil.copy2(run/name, target/name)
    for name in ['per_case.jsonl', 'aggregate.json']:
        shutil.copy2(run/'eval'/name, target/name)
    summaries = []
    for cid, label in zip(sorted(expected), LABELS):
        row = rows[cid]
        scoring = row.get('scoring', {})
        presentation = row.get('instructional_presentation', {})
        groups = scoring.get('groups') or {}
        summaries.append({'id': cid, 'topic': label, 'video_quality': groups.get('video_quality'),
            'teaching_quality': groups.get('teaching_quality'), 'total': scoring.get('score'),
            'presentation': scoring.get('presentation_score'), 'passed': scoring.get('strict_pass'),
            'all_windows_reviewed': presentation.get('all_windows_reviewed') is True,
            'reviewed_windows': sum(not w.get('error') for w in presentation.get('segments', [])),
            'window_count': len(presentation.get('segments', [])),
            'audio_detected': row.get('narration', {}).get('detected'),
            'errors': row.get('errors', []), 'scoring_errors': scoring.get('errors', []),
            'axes': scoring.get('axis_scores', {}),
            'acceptance_failures': scoring.get('acceptance_failures', [])})
    (target/'summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2)+'\n')
    with (target/'scores.csv').open('w', newline='') as handle:
        fields = ['id', 'topic', 'video_quality', 'teaching_quality', 'presentation', 'total', 'passed', 'all_windows_reviewed']
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summaries)
    def value(v):
        return '未评分' if v is None else f'{v:.2f}'
    text = '# 八条 Code2Video 完整评分\n\n'
    text += '采用 quality-v12，四卡并行、每卡两题，按各自作者大纲与示例逐条评测。八条均要求英文旁白，未移除音频要求。未知分保留 null，不作为零分。\n\n'
    text += '| 视频 | 画质组 | 教学组 | 呈现 | 总分 | 全片窗口 | 验收 |\n|---|---:|---:|---:|---:|---|---|\n'
    for r in summaries:
        text += f"| {r['topic']} | {value(r['video_quality'])} | {value(r['teaching_quality'])} | {value(r['presentation'])} | {value(r['total'])} | {r['reviewed_windows']}/{r['window_count']} | {'通过' if r['passed'] else '未通过'} |\n"
    text += '\n原始证据见 per_case.jsonl；summary.json 保留八轴分、错误及验收缺项。全片窗口检查不等于逐帧人工验收；评委与生成模型均为本地 Qwen，仍需外部人工校准。\n'
    text += '\n视频目录：delivery/最终视频/Code2Video_新增8题_20261110/。其他可复现项目见 docs/TEACHING_VIDEO_REPRODUCTION_CANDIDATES_20261110.md。\n'
    (target/'README.md').write_text(text)
    delivery = ROOT/'delivery/最终视频/Code2Video_新增8题_20261110'
    if delivery.is_dir():
        (delivery/'评分结果.md').write_text(text)
    print(json.dumps({'evaluated': len(rows), 'full_timeline_reviews': sum(r['all_windows_reviewed'] for r in summaries),
                      'valid_totals': sum(r['total'] is not None for r in summaries), 'report': str(target)}, ensure_ascii=False), flush=True)
    if args.publish:
        subprocess.run(['git', 'add', str(target)], cwd=ROOT, check=True)
        changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', str(target)], cwd=ROOT)
        if changed.returncode == 1:
            subprocess.run(['git', '-c', 'user.name=Codex', '-c', 'user.email=codex@openai.com',
                            'commit', '-m', 'Archive complete eight-video quality-v12 evaluations', '--', str(target)], cwd=ROOT, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
