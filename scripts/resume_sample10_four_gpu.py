"""Resume unfinished fixed-ten cases with four isolated Qwen vision servers."""
import os, sys, json, time, subprocess, pathlib, concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parents[1]
OLD=ROOT/'results/qwen38_gpu0_sample10_strict5s_v3_20261102'
OUT=ROOT/'results/resume_four_gpu_20261102'
def dump(p,x):
    tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)); tmp.replace(p)
def worker(gpu,ids):
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),LOCAL_BASE_URL=f'http://127.0.0.1:{8000+gpu}/v1',LOCAL_MODEL='qwen3.8-27b',VIDEO_TEACHER_API_KEY='local',VIDEO_TEACHER_BASE_URL=f'http://127.0.0.1:{8000+gpu}/v1',VIDEO_TEACHER_MODEL='qwen3.8-27b',VIDEO_TEACHER_ENABLE_THINKING='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    env['PATH']='/root/code2video-env/bin:'+env['PATH']; env['PYTHONPATH']=str(ROOT)
    with (OUT/f'worker_{gpu}.log').open('a') as log:
        return subprocess.run([sys.executable,__file__,'worker',str(gpu),*ids],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode

def work(gpu,ids):
    sys.path.insert(0,str(ROOT))
    from generation.strict_video_contract import VERSION
    from generation.strict_manim import inspect_exact
    from generation.quality_gate import assess
    from generation.repair_feedback import validated_frozen
    from eval.run_benchmark_v2 import evaluate
    from eval.frame_extractor import extract_frames
    import urllib.request
    for _ in range(600):
        try:
            urllib.request.urlopen(os.environ['LOCAL_BASE_URL'].replace('/v1','/health'),timeout=3).close(); break
        except Exception: time.sleep(2)
    else: raise RuntimeError('model health timeout')
    cases={r['id']:r for r in map(json.loads,(OLD/'prompts.jsonl').read_text().splitlines())}
    for cid in ids:
        final=OUT/f'final_{cid}.json'
        if final.exists(): continue
        feedback=None; frozen=None
        for attempt in range(3):
            olddir=OLD/f'attempt_{attempt}'; ad=OUT/f'attempt_{attempt}'; ad.mkdir(exist_ok=True)
            oldresult=olddir/f'model_result_{cid}.json'; oldeval=olddir/f'{cid}_evaluation.json'
            rp=ad/f'model_result_{cid}.json'; ep=ad/f'{cid}_evaluation.json'
            if oldresult.exists() and oldeval.exists():
                result=json.loads(oldresult.read_text()); evaluation=json.loads(oldeval.read_text()); evidence=olddir
                print(cid,attempt,'reusing completed attempt',flush=True)
            elif rp.exists() and ep.exists():
                result=json.loads(rp.read_text()); evaluation=json.loads(ep.read_text()); evidence=ad
            else:
                cmd=['bash','research/code2video/experiments/run_model_case.sh','--case-id',cid,'--prompts',str(OLD/'prompts.jsonl'),'--out',str(ad),'--strict-five-seconds','--attempt',str(attempt)]
                if feedback:
                    fp=ad/f'{cid}_feedback.json'; dump(fp,feedback); cmd+=['--quality-feedback',str(fp)]
                print(cid,attempt,'generating on GPU',gpu,flush=True)
                with (ad/f'{cid}.log').open('w') as log:
                    proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try: code=proc.wait(timeout=3600)
                    except subprocess.TimeoutExpired:
                        import signal
                        os.killpg(proc.pid,signal.SIGTERM); proc.wait(); code=124
                result=json.loads(rp.read_text()) if rp.exists() else {}; result['exit_code']=code
                rendered=bool(result.get('complete') and result.get('contract_version')==VERSION and pathlib.Path(result.get('video') or '').is_file() and inspect_exact(pathlib.Path(result['video']))['valid'])
                evaluation=evaluate(cases[cid],{'status':'ok' if rendered else 'failed','video_path':result.get('video')})
                result['quality_gate']=assess(result,evaluation); dump(ep,evaluation); dump(rp,result); evidence=ad
            gate=result['quality_gate']
            feedback={'gate':gate,'render_diagnostics':result.get('strict_diagnostics',{}),'generation_error':result.get('error'),'instruction':'Repair the evidenced failures while preserving the original task and target boxes.'}
            frozen = validated_frozen(result, frozen)
            if frozen is not None: feedback['frozen_source_edit_regions']=frozen
            if result.get('complete') and pathlib.Path(result.get('video') or '').is_file():
                feedback['review_frames']=[]
                for i,frame in enumerate(extract_frames(result['video'],n=3,resize_max=854)):
                    fp=ad/f'{cid}_review_{i}.jpg'; frame.save(fp); feedback['review_frames'].append(str(fp))
            if gate['passed']: break
        ok=bool(result.get('complete') and result.get('contract_version')==VERSION and pathlib.Path(result.get('video') or '').is_file() and inspect_exact(pathlib.Path(result['video']))['valid'])
        entry=dict(id=cid,status='ok' if ok else 'failed',video_path=result.get('video') if ok else None,model='qwen3.8-27b',generation=result,quality_passed=gate['passed'])
        dump(final,dict(entry=entry,evaluation=evaluation)); print(cid,'finished',entry['status'],'quality',gate['passed'],flush=True)

def main():
    from generation.strict_video_contract import VERSION
    if json.loads((OLD/'run_config.json').read_text()).get('contract_version') != VERSION:
        raise RuntimeError('Historical contract differs; use run_qwen_multigpu.py with a fresh output directory')
    OUT.mkdir(exist_ok=True)
    prior=json.loads((OLD/'generation_summary.json').read_text()); done={x['id'] for x in prior}
    ids=[json.loads(x)['id'] for x in (OLD/'prompts.jsonl').read_text().splitlines()]; pending=[x for x in ids if x not in done]
    dump(OUT/'run_config.json',dict(source=str(OLD),pending=pending,gpus=[0,1,2,3],ports=[8000,8001,8002,8003],max_attempts_including_prior=3))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        codes=list(pool.map(lambda g:worker(g,pending[g::4]),range(4)))
    rows={x['id']:x for x in prior}; ev={json.loads(x)['id']:json.loads(x) for x in (OLD/'video-teacher-2x8-v4/per_case.jsonl').read_text().splitlines()}
    for f in OUT.glob('final_*.json'):
        d=json.loads(f.read_text()); rows[d['entry']['id']]=d['entry']; ev[d['entry']['id']]=d['evaluation']
    ordered=[rows[i] for i in ids if i in rows]; dump(OUT/'generation_summary.json',ordered)
    (OUT/'manifest.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in ordered))
    ed=OUT/'video-teacher-2x8-v4'; ed.mkdir(exist_ok=True)
    (ed/'per_case.jsonl').write_text(''.join(json.dumps(ev[i],ensure_ascii=False)+'\n' for i in ids if i in ev))
    sys.path.insert(0,str(ROOT))
    from eval.run_benchmark_v2 import report
    prompts={x['id']:x for x in map(json.loads,(OLD/'prompts.jsonl').read_text().splitlines())}
    aggregate=report([ev[i] for i in ids if i in ev],prompts); dump(ed/'aggregate.json',aggregate)
    dump(OUT/'completion.json',dict(total=10,processed=len(ordered),generated=sum(x['status']=='ok' for x in ordered),quality_passed=sum(x.get('quality_passed',False) for x in ordered),worker_exit_codes=codes,execution_finished=len(ordered)==10 and not any(codes),complete=len(ordered)==10 and all(x.get('quality_passed',False) for x in ordered),same_model_self_evaluation=True))
    print((OUT/'completion.json').read_text(),flush=True)
if __name__=='__main__':
    if len(sys.argv)>1: work(int(sys.argv[2]),sys.argv[3:])
    else: main()
