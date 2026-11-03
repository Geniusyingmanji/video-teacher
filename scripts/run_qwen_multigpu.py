"""Fresh fixed-ten run on explicitly selected GPUs, with isolated workers and live summaries."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.strict_video_contract import VERSION
from eval.benchmark_scoring import VERSION as SCORING_VERSION


def dump(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def implementation_sha256():
    paths = sorted([*ROOT.glob('generation/**/*.py'), *ROOT.glob('eval/**/*.py'),
                    *ROOT.glob('scripts/*.py'), *ROOT.glob('research/code2video/experiments/*.py'),
                    *ROOT.glob('research/code2video/experiments/*.sh')])
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def environment(gpu, port):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), LOCAL_BASE_URL=f'http://127.0.0.1:{port}/v1',
        LOCAL_MODEL='qwen3.8-27b', VIDEO_TEACHER_API_KEY='local',
        VIDEO_TEACHER_BASE_URL=f'http://127.0.0.1:{port}/v1', VIDEO_TEACHER_MODEL='qwen3.8-27b',
        VIDEO_TEACHER_ENABLE_THINKING='false', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env['PATH'] = '/root/code2video-env/bin:' + env['PATH']
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    return env


def run_case(args):
    from generation.strict_manim import inspect_exact
    from generation.quality_gate import assess
    from generation.repair_feedback import feedback_for, validated_frozen
    from eval.run_benchmark_v2 import evaluate_with_retry as evaluate
    from eval.frame_extractor import extract_frames
    case = next(json.loads(line) for line in (args.out/'prompts.jsonl').read_text().splitlines()
                if json.loads(line)['id'] == args.case)
    deadline = time.monotonic() + 1200
    while True:
        try:
            urllib.request.urlopen(os.environ['LOCAL_BASE_URL'].replace('/v1', '/health'), timeout=3).close()
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise RuntimeError('model health timeout')
            time.sleep(3)
    feedback, frozen = None, None
    for attempt in range(args.max_attempts):
        directory = args.out/f'attempt_{attempt}'
        directory.mkdir(exist_ok=True)
        result_path = directory/f'model_result_{args.case}.json'
        evaluation_path = directory/f'{args.case}_evaluation.json'
        print(f'{args.case} attempt {attempt+1}/{args.max_attempts} GPU {args.gpu}', flush=True)
        if result_path.exists() and evaluation_path.exists():
            result = json.loads(result_path.read_text())
            evaluation = json.loads(evaluation_path.read_text())
        else:
            command = ['bash', 'research/code2video/experiments/run_model_case.sh', '--case-id', args.case,
                '--prompts', str(args.out/'prompts.jsonl'), '--out', str(directory),
                '--strict-five-seconds', '--attempt', str(attempt)]
            if feedback:
                path = directory/f'{args.case}_feedback.json'
                dump(path, feedback)
                command += ['--quality-feedback', str(path)]
            with (directory/f'{args.case}.log').open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=3600)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    code = 124
            result = json.loads(result_path.read_text()) if result_path.exists() else {'error':f'generation exited {code} without result'}
            result['exit_code'] = code
            video = Path(result.get('video') or '')
            rendered = result.get('complete') is True and result.get('contract_version') == VERSION and video.is_file() and inspect_exact(video)['valid']
            previous = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else None
            evaluation = evaluate(case, {'status':'ok' if rendered else 'failed', 'video_path':str(video) if rendered else None}, previous=previous)
            result['quality_gate'] = assess(result, evaluation)
            result['semantic_review_status'] = ('evaluated_pass' if result['quality_gate']['passed'] else 'evaluated_fail' if evaluation.get('scoring',{}).get('valid') else 'evaluation_invalid')
            dump(result_path, result)
            dump(evaluation_path, evaluation)
        frozen = validated_frozen(result, frozen)
        feedback = feedback_for(result, evaluation, frozen)
        if result.get('complete') and Path(result.get('video') or '').is_file():
            feedback['review_frames'] = []
            for index, frame in enumerate(extract_frames(result['video'], n=3, resize_max=854)):
                path = directory/f'{args.case}_review_{index}.jpg'
                frame.save(path)
                feedback['review_frames'].append(str(path))
        if result['quality_gate']['passed']:
            break
    video = Path(result.get('video') or '')
    rendered = result.get('complete') is True and result.get('contract_version') == VERSION and video.is_file() and inspect_exact(video)['valid']
    entry = dict(id=args.case, status='ok' if rendered else 'failed', video_path=str(video) if rendered else None,
        model='qwen3.8-27b', generation=result, quality_passed=result['quality_gate']['passed'])
    dump(args.out/f'final_{args.case}.json', {'entry':entry, 'evaluation':evaluation})
    print(f'{args.case}: generated={rendered}, quality_passed={entry["quality_passed"]}', flush=True)


def summarize(out, cases, finished=False):
    from eval.run_benchmark_v2 import report
    rows, evaluations = [], []
    for case in cases:
        path = out/f'final_{case["id"]}.json'
        if path.exists():
            final = json.loads(path.read_text())
            rows.append(final['entry']); evaluations.append(final['evaluation'])
        elif finished:
            # Infrastructure failures remain in the ten-case denominator.
            from eval.benchmark_scoring import score_case
            rows.append(dict(id=case['id'], status='failed', video_path=None, quality_passed=False,
                             error='worker exited without final result'))
            evaluations.append(dict(id=case['id'], scoring=score_case({}), errors=['worker_missing_final']))
    dump(out/'generation_summary.json', rows)
    (out/'manifest.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
    directory = out/SCORING_VERSION; directory.mkdir(exist_ok=True)
    (directory/'per_case.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in evaluations))
    if finished:
        aggregate = report(evaluations, {case['id']:case for case in cases})
        dump(directory/'aggregate.json', aggregate)
    completion = dict(total=len(cases), processed=sum((out/f'final_{case["id"]}.json').exists() for case in cases),
        generated=sum(row['status']=='ok' for row in rows), quality_passed=sum(row['quality_passed'] for row in rows),
        execution_finished=finished, complete=finished and len(rows)==len(cases) and all(row['quality_passed'] for row in rows),
        scoring_version=SCORING_VERSION, contract_version=VERSION, same_model_self_evaluation=True)
    dump(out/('completion.json' if finished else 'progress.json'), completion)
    return completion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prompts', type=Path, default=ROOT/'results/reports/sample10_four_gpu_20261102/prompts.jsonl')
    parser.add_argument('--gpus', type=int, nargs='+', default=[0,1])
    parser.add_argument('--ports', type=int, nargs='+', default=[8000,8001])
    parser.add_argument('--max-attempts', type=int, default=3, choices=range(1,4))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--case')
    parser.add_argument('--gpu', type=int)
    args = parser.parse_args(); args.out = args.out.resolve()
    if args.case:
        run_case(args); return 0
    if len(args.gpus) != len(args.ports) or len(set(args.gpus)) != len(args.gpus) or len(set(args.ports)) != len(args.ports):
        parser.error('GPUs and ports must be unique and paired')
    cases = [json.loads(line) for line in args.prompts.read_text().splitlines() if line.strip()]
    if len(cases)!=10 or len({case['id'] for case in cases})!=10:
        parser.error('exactly ten unique fixed cases required')
    args.out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    config = dict(git_commit=commit, ids=[case['id'] for case in cases], gpus=args.gpus, ports=args.ports,
        contract_version=VERSION, scoring_version=SCORING_VERSION, max_attempts=args.max_attempts,
        implementation_sha256=implementation_sha256(),
        prompt_sha256=hashlib.sha256(args.prompts.read_bytes()).hexdigest(), fresh_generation=True)
    config_path = args.out/'run_config.json'
    if args.resume:
        previous = json.loads(config_path.read_text())
        if any(previous.get(key)!=config[key] for key in ['git_commit','ids','contract_version','scoring_version','prompt_sha256','max_attempts','implementation_sha256']):
            parser.error('resume requires the identical code, task, contract and scoring configuration')
    elif any(args.out.iterdir()):
        parser.error('fresh run requires empty output directory')
    dump(config_path, config)
    (args.out/'prompts.jsonl').write_bytes(args.prompts.read_bytes())
    tasks = queue.Queue()
    for case in cases:
        if not (args.out/f'final_{case["id"]}.json').exists(): tasks.put(case['id'])
    def worker(gpu,port):
        codes = []
        while True:
            try: cid = tasks.get_nowait()
            except queue.Empty: return codes
            command = [sys.executable,'-u',__file__,'--out',str(args.out),'--case',cid,'--gpu',str(gpu),'--max-attempts',str(args.max_attempts)]
            with (args.out/f'worker_gpu{gpu}_{cid}.log').open('a') as log:
                code = subprocess.run(command,cwd=ROOT,env=environment(gpu,port),stdout=log,stderr=subprocess.STDOUT).returncode
            codes.append({'id':cid,'exit_code':code,'gpu':gpu})
            print(json.dumps(codes[-1]),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.gpus)) as pool:
        futures = [pool.submit(worker,gpu,port) for gpu,port in zip(args.gpus,args.ports)]
        while any(not future.done() for future in futures):
            summarize(args.out,cases)
            time.sleep(10)
        codes = [row for future in futures for row in future.result()]
    dump(args.out/'worker_results.json', codes)
    completion = summarize(args.out,cases,True)
    print(json.dumps(completion),flush=True)
    return 0 if completion['complete'] else 1


if __name__=='__main__':
    raise SystemExit(main())
