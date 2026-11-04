"""Fresh fixed-ten run on explicitly selected GPUs, with isolated workers and live summaries."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import random
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.strict_video_contract import VERSION
from generation.lesson_spec import contract_version, duration_spec
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


def candidate_rank(candidate):
    result,evaluation,_ = candidate
    scoring=evaluation.get('scoring',{})
    value=scoring.get('score')
    numeric=type(value) in (int,float) and math.isfinite(value)
    return (result.get('quality_gate',{}).get('passed') is True,
            result.get('complete') is True,
            scoring.get('valid') is True and numeric,
            value if numeric else -1,
            -candidate[2])


def run_case(args):
    from generation.strict_manim import inspect_exact
    from generation.quality_gate import assess
    from generation.repair_feedback import feedback_for, validated_frozen
    from eval.run_benchmark_v2 import evaluate_with_retry as evaluate
    from eval.frame_extractor import extract_frames
    case = next(json.loads(line) for line in (args.out/'prompts.jsonl').read_text().splitlines()
                if json.loads(line)['id'] == args.case)
    config = json.loads((args.out/'run_config.json').read_text())
    profile = config.get('generation_profile','strict')
    draft = profile == 'draft'
    evaluate_draft = config.get('evaluate_draft', False)
    timing = duration_spec(case)
    expected_version = contract_version(case)
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
    candidates=[]
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
                '--strict-contract', '--attempt', str(attempt)]
            command += ['--generation-profile',profile]
            if attempt == 0 and draft and config.get('reuse_run'):
                previous_run = Path(config['reuse_run'])
                candidates_to_reuse = list((ROOT/'research/code2video/Code2Video/src/CASES').glob(
                    f'{previous_run.name}-attempt_*-qwen38-{args.case}-attempt*/{args.case}/section_1.py'))
                if candidates_to_reuse:
                    old_code = max(candidates_to_reuse,key=lambda path:(
                        (path.parent/f'{args.case}.mp4').is_file(),path.stat().st_mtime))
                    command += ['--reuse-scene-from',str(old_code.parent)]
            if feedback:
                if draft:
                    # Generation retries carry actionable runtime errors, not the full quality ledger.
                    feedback = {key: feedback[key] for key in ('generation_error','source_plan_validation','instruction') if key in feedback}
                path = directory/f'{args.case}_feedback.json'
                dump(path, feedback)
                command += ['--quality-feedback', str(path)]
            with (directory/f'{args.case}.log').open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=7200)
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
            rendered = result.get('complete') is True and result.get('contract_version') == expected_version and video.is_file() and inspect_exact(video,timing['duration_seconds'],timing['fps'])['valid']
            previous = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else None
            evaluation = ({'id':args.case,'version':SCORING_VERSION,'status':'deferred',
                           'scoring':{'valid':False,'strict_pass':False,'score':None},
                           'errors':['Full quality evaluation deferred: generation-first draft delivery']}
                          if draft and not evaluate_draft else evaluate(case, {'status':'ok' if rendered else 'failed', 'video_path':str(video) if rendered else None, 'render_diagnostics':result.get('strict_diagnostics',{})}, previous=previous))
            result['quality_gate'] = assess(result, evaluation)
            result['semantic_review_status'] = ('deferred_draft_delivery' if draft and not evaluate_draft else
                'evaluated_pass' if result['quality_gate']['passed'] else 'evaluated_fail' if evaluation.get('scoring',{}).get('valid') else 'evaluation_invalid')
            dump(result_path, result)
            dump(evaluation_path, evaluation)
        candidates.append((result,evaluation,attempt))
        frozen = validated_frozen(result, frozen)
        feedback = feedback_for(result, evaluation, frozen)
        if draft and result.get('complete') and Path(result.get('video') or '').is_file():
            break
        if result.get('complete') and Path(result.get('video') or '').is_file():
            feedback['review_frames'] = []
            for index, frame in enumerate(extract_frames(result['video'], n=3, resize_max=854)):
                path = directory/f'{args.case}_review_{index}.jpg'
                frame.save(path)
                feedback['review_frames'].append(str(path))
        if result['quality_gate']['passed']:
            break
    result,evaluation,selected_attempt=max(candidates,key=candidate_rank)
    result={**result,'selected_attempt':selected_attempt,
            'candidate_history':[{'attempt':attempt,'complete':r.get('complete'),
                                  'quality_passed':r.get('quality_gate',{}).get('passed'),
                                  'evaluation_valid':e.get('scoring',{}).get('valid'),
                                  'score':e.get('scoring',{}).get('score')} for r,e,attempt in candidates]}
    video = Path(result.get('video') or '')
    rendered = result.get('complete') is True and result.get('contract_version') == expected_version and video.is_file() and inspect_exact(video,timing['duration_seconds'],timing['fps'])['valid']
    entry = dict(id=args.case, status='ok' if rendered else 'failed', video_path=str(video) if rendered else None,
        model='qwen3.8-27b', generation=result, quality_passed=result['quality_gate']['passed'],
        generation_profile=profile, quality_review_status='deferred' if draft and not evaluate_draft else result.get('semantic_review_status'))
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
    config_path=out/'run_config.json'
    draft=config_path.is_file() and json.loads(config_path.read_text()).get('generation_profile') == 'draft'
    completion = dict(total=len(cases), processed=sum((out/f'final_{case["id"]}.json').exists() for case in cases),
        generated=sum(row['status']=='ok' for row in rows), quality_passed=sum(row['quality_passed'] for row in rows),
        execution_finished=finished, complete=finished and len(rows)==len(cases) and all(row['status']=='ok' if draft else row['quality_passed'] for row in rows),
        generation_profile='draft' if draft else 'strict', quality_review_deferred=draft and not json.loads(config_path.read_text()).get('evaluate_draft',False),
        scoring_version=SCORING_VERSION, contract_versions={c['id']:contract_version(c) for c in cases}, same_model_self_evaluation=True)
    dump(out/('completion.json' if finished else 'progress.json'), completion)
    return completion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prompts', type=Path, default=ROOT/'data/prompts/lesson_validation_10_v2.jsonl')
    parser.add_argument('--gpus', type=int, nargs='+', choices=[0,1], default=[0,1])
    parser.add_argument('--ports', type=int, nargs='+', default=[8000,8001])
    parser.add_argument('--max-attempts', type=int, default=3, choices=range(1,4))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--workers-per-gpu', type=int, choices=(1,2), default=1)
    parser.add_argument('--generation-profile', choices=('strict','draft'), default='strict')
    parser.add_argument('--reuse-run', type=Path)
    parser.add_argument('--evaluate-draft', action='store_true', help='Evaluate delivered drafts without making quality a generation requirement')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--case')
    parser.add_argument('--gpu', type=int, choices=[0,1])
    args = parser.parse_args(); args.out = args.out.resolve()
    if args.case:
        run_case(args); return 0
    if len(args.gpus) != len(args.ports) or len(set(args.gpus)) != len(args.gpus) or len(set(args.ports)) != len(args.ports):
        parser.error('GPUs and ports must be unique and paired')
    cases = [json.loads(line) for line in args.prompts.read_text().splitlines() if line.strip()]
    if len(cases)==400 and len({c['id'] for c in cases})==400:
        cases=random.Random(20261102).sample(sorted(cases,key=lambda c:c['id']),10)
    if len(cases)!=10 or len({case['id'] for case in cases})!=10:
        parser.error('exactly ten unique fixed cases required')
    args.out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    config = dict(git_commit=commit, ids=[case['id'] for case in cases], gpus=args.gpus, ports=args.ports,
        evaluate_draft=args.evaluate_draft,generation_profile=args.generation_profile,workers_per_gpu=args.workers_per_gpu,
        reuse_run=str(args.reuse_run.resolve()) if args.reuse_run else None,
        contract_versions={c['id']:contract_version(c) for c in cases},
        timing={c['id']:duration_spec(c) for c in cases},
        scoring_version=SCORING_VERSION, max_attempts=args.max_attempts,
        implementation_sha256=implementation_sha256(),
        prompt_sha256=hashlib.sha256(args.prompts.read_bytes()).hexdigest(), fresh_generation=not bool(args.reuse_run))
    if args.reuse_run:
        if args.generation_profile != 'draft':parser.error('reuse-run requires draft delivery')
        previous_cases=[json.loads(line) for line in (args.reuse_run/'prompts.jsonl').read_text().splitlines() if line.strip()]
        if previous_cases != cases:parser.error('reuse-run requires identical frozen cases')
    config_path = args.out/'run_config.json'
    if args.resume:
        previous = json.loads(config_path.read_text())
        if any(previous.get(key)!=config[key] for key in ['git_commit','ids','contract_versions','timing','scoring_version','prompt_sha256','max_attempts','implementation_sha256','generation_profile','reuse_run','evaluate_draft']):
            parser.error('resume requires the identical code, task, contract and scoring configuration')
    elif any(args.out.iterdir()):
        parser.error('fresh run requires empty output directory')
    dump(config_path, config)
    (args.out/'prompts.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in cases))
    if args.prepare_only:return 0
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.gpus)*args.workers_per_gpu) as pool:
        futures = [pool.submit(worker,gpu,port) for gpu,port in zip(args.gpus,args.ports) for _ in range(args.workers_per_gpu)]
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
