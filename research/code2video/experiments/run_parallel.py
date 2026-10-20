"""Run 8 pilot cases on four local Qwen replicas; retain per-case logs."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
GROUPS = [
    ['math_exp_01', 'math_prob_01'],
    ['math_exp_02', 'math_prob_02'],
    ['phys_exp_02', 'phys_prob_01'],
    ['chem_exp_01', 'chem_prob_02'],
]


def wait_for_service(port):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f'Service {port} did not become healthy')


def run_case(case_id, port):
    wait_for_service(port)
    env = dict(os.environ, LOCAL_BASE_URL=f'http://127.0.0.1:{port}/v1')
    with (HERE / f'{case_id}.log').open('w') as output:
        result = subprocess.run(['bash', str(HERE / 'run_model_case.sh'), '--case-id', case_id],
            env=env, stdout=output, stderr=subprocess.STDOUT)
    print(json.dumps({'case_id': case_id, 'port': port, 'exit_code': result.returncode}), flush=True)
    return {'case_id': case_id, 'port': port, 'exit_code': result.returncode}


if __name__ == '__main__':
    replicas = []
    for gpu in range(1, 4):
        port = 8000 + gpu
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models', timeout=3) as response:
                models = json.load(response)
            if any(model['id'] == 'qwen3.8-27b' for model in models['data']):
                replicas.append({'gpu': gpu, 'port': port, 'reused': True})
                continue
            raise RuntimeError(f'Port {port} is serving another model')
        except OSError:
            pass
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), QWEN_PORT=str(8000+gpu))
        with (HERE.parent / f'qwen38-gpu{gpu}.log').open('w') as output:
            process = subprocess.Popen(['bash', str(HERE / 'start_qwen38.sh')], env=env,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        replicas.append({'gpu': gpu, 'pid': process.pid, 'port': 8000+gpu})
    (HERE / 'replicas.json').write_text(json.dumps(replicas, indent=2))
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_case, case_id, 8000+gpu)
                   for gpu, cases in enumerate(GROUPS) for case_id in cases]
        results = [future.result() for future in futures]
    (HERE / 'parallel_result.json').write_text(json.dumps(results, indent=2))
    if any(row['exit_code'] for row in results):
        raise SystemExit(1)
