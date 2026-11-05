"""Follow base evaluations, verify severe claims, and preserve both scoring stages."""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from eval.run_benchmark_v2 import read_jsonl, unique_by_id, report, assessment_coverage
from eval.verified_scoring import apply_grounding, code_hash, VERSION
from eval.structured_transport import structured_stop_token_guard, guard_config
from eval.judges.gpt55 import judge_config


def row_digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()


def source_finished(directory, expected_rows=None):
    """A full row count alone may still describe a previous evaluation attempt."""
    try:
        aggregate = json.loads((directory/'aggregate.json').read_text())
        data = (directory/'per_case.jsonl').read_bytes()
        if aggregate.get('per_case_sha256') != hashlib.sha256(data).hexdigest():
            return False
        if expected_rows is not None:
            actual = unique_by_id([json.loads(line) for line in data.splitlines() if line.strip()], latest=True)
            return actual == expected_rows
        return True
    except (OSError, ValueError):
        return False


def choose_endpoint(previous_claims, endpoints, counter):
    # Keep incomplete cases on an explicitly allowed, previously used service.
    for claim in previous_claims:
        previous = claim.get('judge', {}).get('base_url')
        if previous in endpoints:
            return previous
    return endpoints[counter % len(endpoints)] if endpoints else None


def process(base, case, endpoint, directory, previous_claims, stop_token_ids=()):
    if endpoint:
        os.environ['VIDEO_TEACHER_BASE_URL']=endpoint
    path=Path(directory)/(hashlib.sha256(case['id'].encode()).hexdigest()[:24]+'.json')
    def checkpoint(results):
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(results,ensure_ascii=False))
        temporary.replace(path)
        print(json.dumps({'case':case['id'],'claims_checked':len(results),
                          'last_decision':results[-1]['decision']}),flush=True)
    try:
        with structured_stop_token_guard(stop_token_ids):
            result=apply_grounding(base,case,previous_claims=previous_claims,checkpoint=checkpoint)
    except Exception as exc:
        result={**base,'base_evaluation':base,'version':VERSION,
                'scoring':{**base['scoring'],'valid':False,'score':None,'groups':None,'strict_pass':False},
                'claim_grounding':{'status':'verification_failed','error':f'{type(exc).__name__}: {exc}'[:1000]}}
    if stop_token_ids:
        result.setdefault('verification_config', {})['transport_guard'] = guard_config(stop_token_ids)
    result['assessment_coverage']=assessment_coverage(result)
    result['base_row_sha256']=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-dir',type=Path,required=True)
    parser.add_argument('--prompts',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--judge-base-url',action='append',default=[])
    parser.add_argument('--follow',action='store_true')
    parser.add_argument('--structured-stop-token-id',action='append',type=int,default=[],
                        help='Repeat for tokenizer stop IDs implicated in a local structured-decoding failure')
    args=parser.parse_args()
    if args.workers<1:parser.error('--workers must be positive')
    try: guard_config(args.structured_stop_token_id)
    except ValueError as exc: parser.error(str(exc))
    if args.structured_stop_token_id and judge_config()['provider'] != 'openai_compatible':
        parser.error('stop-token guard requires an OpenAI-compatible judge')
    prompts=unique_by_id(read_jsonl(args.prompts))
    args.out.mkdir(parents=True,exist_ok=True)
    checkpoints=args.out/'claim_checkpoints';checkpoints.mkdir(exist_ok=True)
    target=args.out/'per_case.jsonl'
    completed=unique_by_id(read_jsonl(target),latest=True) if target.exists() else {}
    running={};submitted={};counter=0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, target.open('a') as handle:
        while True:
            try:base=unique_by_id(read_jsonl(args.base_dir/'per_case.jsonl'),latest=True)
            except (OSError,ValueError):base={}
            for case_id,row in base.items():
                if case_id not in prompts:raise ValueError('unexpected base case ID')
                digest=row_digest(row)
                if submitted.get(case_id)==digest or case_id in running.values():continue
                old=completed.get(case_id,{})
                if (old.get('base_row_sha256')==digest and old.get('verification_config',{}).get('code_sha256')==code_hash()
                        and (old.get('scoring',{}).get('valid') is True
                             or 'generation_missing_or_failed' in old.get('errors',[]))):
                    submitted[case_id]=digest;continue
                if len(running)>=args.workers:break
                cached=checkpoints/(hashlib.sha256(case_id.encode()).hexdigest()[:24]+'.json')
                previous=json.loads(cached.read_text()) if cached.exists() else []
                endpoint=choose_endpoint(previous,args.judge_base_url,counter)
                future=pool.submit(process,row,prompts[case_id],endpoint,str(checkpoints),previous,
                                   args.structured_stop_token_id)
                running[future]=case_id;submitted[case_id]=digest;counter+=1
            if running:
                done,_=wait(running,timeout=2,return_when=FIRST_COMPLETED)
                for future in done:
                    case_id=running.pop(future);row=future.result();completed[case_id]=row
                    handle.write(json.dumps(row,ensure_ascii=False)+'\n');handle.flush()
                    print(json.dumps({'verified_cases':len(completed),'total':len(prompts),'id':case_id,
                                      'score':row['scoring'].get('score'),'valid':row['scoring'].get('valid')}),flush=True)
            (args.out/'progress.json').write_text(json.dumps({'total':len(prompts),'completed':list(completed),
                'pending':[i for i in prompts if i not in completed],'running':list(running.values())},indent=2))
            current = all(submitted.get(i)==row_digest(row) for i,row in base.items())
            if (len(completed)==len(prompts) and len(base)==len(prompts) and not running
                    and current and (not args.follow or source_finished(args.base_dir, base))):break
            if not args.follow and not running and current:break
            if not running:time.sleep(2)
    rows=[completed[i] for i in prompts if i in completed]
    target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    aggregate=report(rows,prompts);aggregate['version']=VERSION
    aggregate['n_requested']=len(prompts)
    aggregate['verification_policy']=code_hash()
    aggregate['base_report_dir']=str(args.base_dir)
    aggregate['transport_guard']=guard_config(args.structured_stop_token_id)
    if len(rows)!=len(prompts):aggregate.update(ranking_publishable=False,ranking_score=None)
    (args.out/'aggregate.json').write_text(json.dumps(aggregate,ensure_ascii=False,indent=2))
    print(json.dumps({'n_total':len(rows),'n_valid':aggregate['n_valid'],'out':str(args.out)}),flush=True)


if __name__=='__main__':main()
