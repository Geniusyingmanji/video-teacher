"""Four independent full reviews, followed by eight author-topic reproductions."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def env_for(gpu):
    return dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu),
                VIDEO_TEACHER_API_KEY='local', VIDEO_TEACHER_MODEL='qwen3.8-27b',
                VIDEO_TEACHER_BASE_URL=f'http://127.0.0.1:{8000+gpu}/v1',
                LOCAL_BASE_URL=f'http://127.0.0.1:{8000+gpu}/v1',
                VIDEO_TEACHER_ENABLE_THINKING='false',
                VIDEO_TEACHER_SCORING_POLICY='quality-v12', OMP_NUM_THREADS='1',
                OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')


def score(run, gpu):
    out = run / f'eval_gpu{gpu}'
    with (run / f'eval_gpu{gpu}.log').open('a') as log:
        code = subprocess.run([sys.executable, '-u', '-m', 'eval.run_benchmark_v2',
            '--prompts', str(run/'prompts.jsonl'), '--manifest', str(run/'manifest.jsonl'),
            '--out', str(out), '--scoring-policy', 'quality-v12'],
            cwd=ROOT, env=env_for(gpu), stdout=log, stderr=subprocess.STDOUT).returncode
    results = out/'per_case.jsonl'
    row = json.loads(results.read_text().splitlines()[-1]) if results.is_file() else {}
    return {'gpu': gpu, 'exit_code': code, 'result': row}


def generate(run, case):
    out = run / ('author_' + case['id'])
    with (run / (case['id']+'.log')).open('a') as log:
        command = [sys.executable, '-u', str(ROOT/'scripts/reproduce_code2video_native.py'),
                   '--topic', case['topic'], '--out', str(out), '--port', str(case['port'])]
        if out.exists():
            command.append('--resume')
        code = subprocess.run(command, cwd=ROOT, env=env_for(case['gpu']),
                              stdout=log, stderr=subprocess.STDOUT).returncode
    report = out/'report.json'
    result = json.loads(report.read_text()) if report.is_file() else {'complete': False}
    # The author may merge a subset. Never deliver that as a complete lesson.
    complete = (result.get('complete') is True and result.get('sections', 0) > 0
                and result.get('rendered_sections') == result.get('sections'))
    delivered = None
    if complete:
        source = Path(result['video'])
        decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-f', 'null', '-'],
                                 capture_output=True, text=True)
        result['decode_audit'] = {'exit_code': decoded.returncode, 'stderr': decoded.stderr}
        if decoded.returncode == 0:
            folder = ROOT/'delivery/最终视频/Code2Video_新增8题_20261110'
            folder.mkdir(parents=True, exist_ok=True)
            target = folder/(case['id']+'_'+case['topic'].replace('/', '_')+'.mp4')
            shutil.copy2(source, target)
            delivered = {'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    return {**case, 'exit_code': code, 'generation': result, 'delivered': delivered}


def main():
    run = Path(sys.argv[1]).resolve()
    dump(run/'state.json', {'stage': 'full_evaluation', 'started_at': time.time(),
                           'gpus': [0, 1, 2, 3], 'batch_started': False})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        reviews = list(pool.map(lambda gpu: score(run, gpu), range(4)))
    dump(run/'four_gpu_evaluations.json', reviews)
    if any(r['exit_code'] or not r['result'] for r in reviews):
        dump(run/'state.json', {'stage': 'evaluation_process_failed', 'batch_started': False})
        raise RuntimeError('Evaluation worker failed; generation not started')
    # Preserve all evaluations including unknown scores. Never select the best review.
    summary = [{'gpu': r['gpu'], 'scoring': r['result'].get('scoring'),
                'coverage': r['result'].get('assessment_coverage'),
                'errors': r['result'].get('errors')} for r in reviews]
    dump(run/'score_summary.json', {'policy': 'quality-v12', 'reviews': summary,
        'note': 'Four repeated local-model reviews of ONE video, not four independent cases. '
                'Unknown scores remain null; missing narration is not waived.'})
    incomplete = [r['gpu'] for r in reviews if r['result'].get('instructional_presentation', {}).get('all_windows_reviewed') is not True]
    if incomplete:
        dump(run/'state.json', {'stage': 'evaluation_incomplete', 'gpus_incomplete': incomplete,
                               'batch_started': False})
        raise RuntimeError('Full timeline review incomplete; generation not started')
    dump(run/'state.json', {'stage': 'batch_generation', 'batch_started': True,
                           'scoring_finished_at': time.time()})
    cases = json.loads((run/'batch_plan.json').read_text())
    completed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(generate, run, case) for case in cases]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            completed.append(row)
            dump(run/(row['id']+'_result.json'), row)
            dump(run/'batch_results.json', completed)
    dump(run/'state.json', {'stage': 'finished', 'batch_started': True, 'processed': len(completed),
                           'delivered': sum(bool(r['delivered']) for r in completed)})


if __name__ == '__main__':
    main()
