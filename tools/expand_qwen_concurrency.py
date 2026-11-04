"""Hand off a live fixed-case run to more slots without restarting case workers."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_qwen_multigpu as runner


def command(pid):
    try:
        return Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')[:-1]
    except (OSError, UnicodeError):
        return []


def alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except OSError:
        return False


def existing_workers(out, ids):
    result = {}
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        args = command(int(item.name))
        if '--case' not in args or '--out' not in args or not any(Path(arg).name == 'run_qwen_multigpu.py' for arg in args):
            continue
        if Path(args[args.index('--out')+1]).resolve() != out:
            continue
        case = args[args.index('--case')+1]
        gpu = int(args[args.index('--gpu')+1])
        if case not in ids or case in result:
            raise ValueError('unknown or duplicate active case: '+case)
        result[case] = {'pid': int(item.name), 'gpu': gpu}
    return result


def slots(gpus, ports, count, active):
    result = []
    for gpu, port in zip(gpus, ports):
        current = [(cid, row['pid']) for cid, row in active.items() if row['gpu'] == gpu]
        if len(current) > count:
            raise ValueError('requested concurrency is below active workers')
        result.extend((gpu, port, current[i] if i < len(current) else None) for i in range(count))
    if any(row['gpu'] not in gpus for row in active.values()):
        raise ValueError('active worker uses a GPU outside this run')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--parent-pid', type=int, required=True)
    parser.add_argument('--workers-per-gpu', type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    out = args.out.resolve()
    config = json.loads((out/'run_config.json').read_text())
    if runner.implementation_sha256() != config['implementation_sha256']:
        raise ValueError('generation implementation changed; do not mix versions')
    if config['gpus'] != [0, 1] or len(config['ports']) != 2:
        raise ValueError('this handoff requires GPU 0 and 1')
    cases = [json.loads(line) for line in (out/'prompts.jsonl').read_text().splitlines() if line.strip()]
    if [case['id'] for case in cases] != config['ids']:
        raise ValueError('frozen cases changed')
    parent = command(args.parent_pid)
    if '--case' in parent or '--out' not in parent or not any(Path(arg).name == 'run_qwen_multigpu.py' for arg in parent):
        raise ValueError('parent PID is not the batch coordinator')
    if Path(parent[parent.index('--out')+1]).resolve() != out:
        raise ValueError('parent PID belongs to another run')
    os.kill(args.parent_pid, signal.SIGSTOP)
    transferred = False
    try:
        active = existing_workers(out, config['ids'])
        work_slots = slots(config['gpus'], config['ports'], args.workers_per_gpu, active)
        pending = queue.Queue()
        for case in cases:
            if case['id'] not in active and not (out/f'final_{case["id"]}.json').exists():
                pending.put(case['id'])
        runner.dump(out/'concurrency.json', {
            'coordinator_pid': os.getpid(), 'previous_coordinator_pid': args.parent_pid,
            'workers_per_gpu': args.workers_per_gpu, 'total_slots': len(work_slots),
            'adopted_workers': active, 'generation_implementation_sha256': config['implementation_sha256'],
            'scheduler_path': str(Path(__file__).resolve()), 'started_at': time.time()})
        # Signal only the old coordinator. Existing case processes remain alive.
        os.kill(args.parent_pid, signal.SIGTERM)
        os.kill(args.parent_pid, signal.SIGCONT)
        transferred = True
        out.with_suffix('.pid').write_text(str(os.getpid()))
    finally:
        if not transferred:
            os.kill(args.parent_pid, signal.SIGCONT)

    def worker(gpu, port, adopted):
        results = []
        if adopted:
            cid, pid = adopted
            while alive(pid):
                time.sleep(2)
            results.append({'id': cid, 'gpu': gpu, 'adopted': True,
                            'final_result_present': (out/f'final_{cid}.json').exists()})
        while True:
            try:
                cid = pending.get_nowait()
            except queue.Empty:
                return results
            cmd = [sys.executable, '-u', str(ROOT/'scripts/run_qwen_multigpu.py'),
                   '--out', str(out), '--case', cid, '--gpu', str(gpu),
                   '--max-attempts', str(config['max_attempts'])]
            print(json.dumps({'started': cid, 'gpu': gpu}), flush=True)
            with (out/f'worker_gpu{gpu}_{cid}.log').open('a') as log:
                code = subprocess.run(cmd, cwd=ROOT, env=runner.environment(gpu, port),
                                      stdout=log, stderr=subprocess.STDOUT).returncode
            results.append({'id': cid, 'gpu': gpu, 'exit_code': code})
            print(json.dumps(results[-1]), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(work_slots)) as pool:
        futures = [pool.submit(worker, *slot) for slot in work_slots]
        while any(not future.done() for future in futures):
            runner.summarize(out, cases)
            time.sleep(10)
        results = [row for future in futures for row in future.result()]
    runner.dump(out/'worker_results_concurrent.json', results)
    completion = runner.summarize(out, cases, True)
    runner.dump(out/'progress.json', completion)
    print(json.dumps(completion), flush=True)
    return 0 if completion['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
