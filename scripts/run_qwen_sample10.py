"""Reproducible GPU-0 Code2Video generation and eight-axis smoke evaluation."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import urllib.request
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.strict_video_contract import VERSION
from generation.strict_manim import inspect_exact
from eval.benchmark_scoring import VERSION as SCORING_VERSION
OUT = ROOT / 'results/qwen38_gpu0_sample10_strict5s_20261102'
SOURCE = ROOT / 'data/prompts/candidate_400.jsonl'
SEED = 20261102


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.out.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'completion.json').exists():
        (OUT / 'completion.json').rename(OUT / f'previous_completion_{time.time_ns()}.json')
    rows = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]
    assert len(rows) == len({r['id'] for r in rows}) == 400
    selected = random.Random(SEED).sample(sorted(rows, key=lambda r: r['id']), 10)
    prompts = OUT / 'prompts.jsonl'
    prompts.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected))
    dump(OUT / 'run_config.json', dict(seed=SEED, source=str(SOURCE),
         source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         ids=[r['id'] for r in selected], gpu=0, model='qwen3.8-27b',
         self_judge=True, use_feedback=False, use_assets=False,
         contract_version=VERSION, duration_seconds=5, fps=15, frame_count=75,
         scoring_version=SCORING_VERSION))
    evaluation_dir = OUT / SCORING_VERSION
    print('Selected: ' + ', '.join(r['id'] for r in selected), flush=True)
    deadline = time.monotonic() + 600
    while True:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3) as response:
                assert response.status == 200
            break
        except Exception:
            if time.monotonic() > deadline:
                raise RuntimeError('Qwen health timeout')
            time.sleep(3)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', LOCAL_BASE_URL='http://127.0.0.1:8000/v1',
               LOCAL_MODEL='qwen3.8-27b', VIDEO_TEACHER_API_KEY='local',
               VIDEO_TEACHER_BASE_URL='http://127.0.0.1:8000/v1',
               VIDEO_TEACHER_MODEL='qwen3.8-27b', VIDEO_TEACHER_ENABLE_THINKING='false')
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env['PATH'] = '/root/code2video-env/bin:' + env['PATH']
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    results = []
    manifest = OUT / 'manifest.jsonl'
    for index, case in enumerate(selected, 1):
        case_id = case['id']
        result_path = OUT / f'model_result_{case_id}.json'
        result = json.loads(result_path.read_text()) if result_path.exists() else {}
        reusable = (result.get('complete') and result.get('contract_version') == VERSION
                    and Path(result.get('video') or '').is_file()
                    and inspect_exact(Path(result['video']))['valid'])
        if not reusable:
            print(f'[{index}/10] generating {case_id}', flush=True)
            with (OUT / f'{case_id}.log').open('w') as log:
                try:
                    run = subprocess.run(['bash', 'research/code2video/experiments/run_model_case.sh',
                          '--case-id', case_id, '--prompts', str(prompts), '--out', str(OUT), '--strict-five-seconds'],
                          cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
                    code = run.returncode
                except subprocess.TimeoutExpired:
                    code = 124
            result = json.loads(result_path.read_text()) if result_path.exists() else {}
            result['exit_code'] = code
        ok = bool(result.get('complete') and result.get('contract_version') == VERSION
                  and Path(result.get('video') or '').is_file()
                  and inspect_exact(Path(result['video']))['valid'])
        results.append(dict(id=case_id, status='ok' if ok else 'failed',
                            video_path=result.get('video') if ok else None,
                            model='qwen3.8-27b', generation=result))
        manifest.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in results))
        dump(OUT / 'generation_summary.json', results)
        print(f'[{index}/10] {case_id}: {"ok" if ok else "failed"}', flush=True)
    print('Running eight-axis evaluation (same-model self-evaluation).', flush=True)
    with (OUT / f'{SCORING_VERSION}.log').open('a') as log:
        run = subprocess.run([sys.executable, '-m', 'eval.run_benchmark_v2', '--prompts', str(prompts),
                              '--manifest', str(manifest), '--out', str(evaluation_dir), '--limit', '10'],
                             cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    aggregate_path = evaluation_dir / 'aggregate.json'
    aggregate = json.loads(aggregate_path.read_text()) if aggregate_path.exists() else {}
    engagement_valid = aggregate.get('supplementary', {}).get('teaching_engagement', {}).get('n_valid', 0)
    complete = (all(r['status'] == 'ok' for r in results) and run.returncode == 0
                and aggregate.get('n_valid') == 10 and engagement_valid == 10)
    dump(OUT / 'completion.json', dict(generated=sum(r['status'] == 'ok' for r in results),
         total=10, evaluation_exit_code=run.returncode, same_model_self_evaluation=True,
         evaluation_valid=aggregate.get('n_valid', 0), complete=complete,
         scoring_version=SCORING_VERSION, engagement_valid=engagement_valid,
         evaluation_dir=str(evaluation_dir)))
    print('Finished. Outputs: ' + str(OUT), flush=True)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
