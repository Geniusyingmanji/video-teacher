"""Author TikZero+ checkpoint inference on a fixed educational pilot.

This is checkpoint inference, not a reproduction of a full paper benchmark.
Run in the upstream DeTikZify environment, with one visible free GPU.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',default='/root/models/tikzero-plus-10b')
    p.add_argument('--prompts',type=Path,default=Path(__file__).resolve().parents[1]/'research/code2image_prompts.jsonl')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--limit',type=int,default=6)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    from transformers import set_seed
    from detikzify.model import load
    from detikzify.infer import DetikzifyPipeline
    started=time.time()
    pipeline=DetikzifyPipeline(*load(args.model,device_map='auto',torch_dtype='bfloat16'),metric='fast')
    report={'method':'author TikZero+ 10B checkpoint, single sampling',
            'benchmark_scope':'six matched educational prompts; not published benchmark replication',
            'model':args.model,'seed':args.seed,'sampling':{'temperature':.8,'top_p':.95,'top_k':0},
            'prompt_sha256':hashlib.sha256(args.prompts.read_bytes()).hexdigest(),
            'environment':{k:importlib.metadata.version(k) for k in ['detikzify','torch','transformers','Pillow']},
            'load_seconds':time.time()-started,'cases':[]}
    for i,line in enumerate(args.prompts.read_text().splitlines()[:args.limit]):
        case=json.loads(line);out=args.out/case['id'];out.mkdir(exist_ok=True)
        (out/'prompt.json').write_text(json.dumps(case,indent=2))
        set_seed(args.seed+i);t=time.time()
        try:
            fig=pipeline.sample(text=case['text'])
            fig.save(str(out/'figure.tex'))
            row={'id':case['id'],'compile_status':fig.status,'rasterizable':fig.is_rasterizable,
                 'has_content':fig.has_content,'seconds':time.time()-t,'content_review':'pending'}
            (out/'compile.log').write_text(fig.log)
            if fig.is_rasterizable:
                fig.save(str(out/'figure.pdf'));fig.save(str(out/'figure.png'),size=1200)
        except Exception as exc:
            row={'id':case['id'],'error':repr(exc),'seconds':time.time()-t}
        report['cases'].append(row)
        (args.out/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
