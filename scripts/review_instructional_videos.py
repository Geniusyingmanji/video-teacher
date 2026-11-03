"""Audit actual presentation value without rewriting old benchmark grades.

This produces the new standalone presentation assessment. It is not a full
fresh eight-axis evaluation and never labels reused v6 scores as v7 scores.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from eval.instructional_video import assess_video, VERSION
from eval.frame_extractor import extract_frames
from eval.run_benchmark_v2 import scoring_code_sha256
from eval.judges.gpt55 import judge_config


def dump(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');temp.replace(path)


def rows_for(args):
    if args.manifest:
        return json.loads(args.manifest.read_text())
    cases=[json.loads(x) for x in (args.run/'prompts.jsonl').read_text().splitlines() if x.strip()]
    rows=[]
    for case in cases:
        d=json.loads((args.run/f"final_{case['id']}.json").read_text());g=d['entry']['generation']
        rows.append({'id':case['id'],'case':case,'video_path':g.get('video') or g.get('strict_diagnostics',{}).get('rendered_video'),
                     'legacy_v6_score':d['evaluation'].get('scoring',{}).get('score'),
                     'generation_accepted':d['entry']['status']=='ok'})
    return rows


def process(row,out):
    path=Path(row['video_path']) if row.get('video_path') else None
    if not path or not path.is_file():
        dump(out/f"{row['id']}.json",{**row,'review':{'valid':False,'passed':False,'error':'no_video'}});return
    identity={'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'case_sha256':hashlib.sha256(json.dumps(row['case'],sort_keys=True).encode()).hexdigest(),
              'code_sha256':scoring_code_sha256(),'judge':judge_config(),'version':VERSION}
    target=out/f"{row['id']}.json"
    previous=None
    if target.exists():
        old=json.loads(target.read_text())
        if old.get('identity')==identity:previous=old.get('review')
        if old.get('identity')==identity and old.get('review',{}).get('valid') is True:
            print(row['id']+' cached',flush=True);return
    try:
        review=assess_video(row['case'],path,resize_max=854,previous=previous)
    except Exception as exc:
        review={'valid':False,'passed':False,'score':None,'error':f'{type(exc).__name__}: {exc}'}
    result={**row,'identity':identity,'review':review}
    if 'expected_presentation_pass' in row:
        result['expectation_matches']=review.get('valid') is True and review.get('passed')==row['expected_presentation_pass']
    dump(target,result)
    print(json.dumps({'id':row['id'],'score':review.get('score'),'passed':review.get('passed'),
                      'valid':review.get('valid'),'expectation_matches':result.get('expectation_matches')}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--run',type=Path);source.add_argument('--manifest',type=Path)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--ports',nargs='+',type=int,default=[8000,8001])
    p.add_argument('--per-port-concurrency',type=int,choices=[1,2],default=1)
    p.add_argument('--case');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if not a.ports or len(set(a.ports))!=len(a.ports):p.error('ports must be nonempty and unique')
    rows=rows_for(a)
    if not rows:p.error('review set must not be empty')
    if a.case:
        row=next(row for row in rows if row['id']==a.case);process(row,a.out);return
    # One independent process per model service avoids thread-local environment races.
    slots=[port for port in a.ports for _ in range(a.per_port_concurrency)]
    groups=[rows[i::len(slots)] for i in range(len(slots))]
    def worker(port,group):
        env=dict(os.environ,VIDEO_TEACHER_API_KEY='local',VIDEO_TEACHER_BASE_URL=f'http://127.0.0.1:{port}/v1',
                 VIDEO_TEACHER_MODEL='qwen3.8-27b',VIDEO_TEACHER_ENABLE_THINKING='false')
        for row in group:
            command=[sys.executable,'-u',__file__,'--out',str(a.out),'--case',row['id']]
            command+=['--manifest',str(a.manifest)] if a.manifest else ['--run',str(a.run)]
            with (a.out/f"{row['id']}.log").open('a') as log:
                code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
            print(json.dumps({'id':row['id'],'worker_exit':code}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(slots)) as pool:
        futures=[pool.submit(worker,port,group) for port,group in zip(slots,groups)]
        for future in futures:future.result()
    results=[json.loads((a.out/f"{row['id']}.json").read_text()) for row in rows if (a.out/f"{row['id']}.json").exists()]
    summary={'total':len(rows),'processed':len(results),'valid_reviews':sum(r['review'].get('valid') is True for r in results),
             'complete_comparisons':sum(r['review'].get('comparison_valid') is True for r in results),
             'bounded_rejections':sum(r['review'].get('decision_type')=='bounded_rejection' for r in results),
             'missing_videos':sum(r['review'].get('error')=='no_video' for r in results),
             'unverified_ids':[r['id'] for r in results if r['review'].get('valid') is not True],
             'presentation_passed':sum(r['review'].get('passed') is True for r in results),
             'control_expectations_met':len(results)==len(rows) and all(r.get('expectation_matches') is True for r in results) if a.manifest else None}
    dump(a.out/'summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
