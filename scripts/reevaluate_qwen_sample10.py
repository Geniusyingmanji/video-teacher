"""Reevaluate available strict clips under v4 and follow generation to all ten IDs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.benchmark_scoring import VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=ROOT / 'results/qwen38_gpu0_sample10_strict5s_20261102')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    source = args.run_dir.resolve()
    output = source / VERSION
    output.mkdir(parents=True, exist_ok=True)
    prompts = source / 'prompts.jsonl'
    cases = [json.loads(line) for line in prompts.read_text().splitlines() if line.strip()]
    wanted = {r['id'] for r in cases}
    if len(cases) != 10 or len(wanted) != 10:
        raise ValueError('expected the frozen ten-case sample')
    (output / 'prompts.jsonl').write_bytes(prompts.read_bytes())
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', VIDEO_TEACHER_API_KEY='local',
               VIDEO_TEACHER_BASE_URL='http://127.0.0.1:8000/v1', VIDEO_TEACHER_MODEL='qwen3.8-27b',
               VIDEO_TEACHER_ENABLE_THINKING='false', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    env['PATH'] = '/root/code2video-env/bin:' + env.get('PATH', '')
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    last = None
    while True:
        try:
            manifest = [json.loads(line) for line in (source / 'manifest.jsonl').read_text().splitlines() if line.strip()]
        except (FileNotFoundError, json.JSONDecodeError):
            if args.once:
                raise
            time.sleep(15)
            continue
        if any(r['id'] not in wanted for r in manifest):
            raise ValueError('unexpected case ID in generation manifest')
        signature = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        if signature != last:
            snapshot = output / 'manifest_snapshot.jsonl'
            snapshot.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in manifest))
            print(f'v4 evaluation: {sum(r.get("status") == "ok" for r in manifest)}/10 available clips', flush=True)
            with (output / 'run.log').open('a') as log:
                command = [sys.executable, '-m', 'eval.run_benchmark_v2', '--prompts', str(output/'prompts.jsonl'),
                           '--manifest', str(snapshot), '--out', str(output), '--limit', '10']
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f'v4 evaluator exited {result.returncode}; see {output / "run.log"}')
            last = signature
            aggregate = json.loads((output / 'aggregate.json').read_text())
            complete = aggregate['n_valid'] == 10 and aggregate['supplementary']['teaching_engagement']['n_valid'] == 10
            status = {'scoring_version': VERSION, 'git_commit': subprocess.check_output(
                        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      'generation_entries': len(manifest), 'evaluated_valid': aggregate['n_valid'],
                      'engagement_valid': aggregate['supplementary']['teaching_engagement']['n_valid'],
                      'complete': complete, 'same_model_self_evaluation': True}
            (output / 'reevaluation_status.json').write_text(json.dumps(status, indent=2))
            print(json.dumps(status), flush=True)
            if complete or args.once or len({r['id'] for r in manifest}) == 10:
                return 0 if complete else (0 if args.once else 1)
        time.sleep(15)


if __name__ == '__main__':
    raise SystemExit(main())
