"""Image-only diagnostic for source-reading errors, with no task or answer text."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path

from .client import MatrixClient
from .common import ROOT,digest,read_jsonl,write_json
from .provenance import file_hash,freeze_run
from .source_audit import source_material

VERSION='localbench-source-observation-dev1'
SYSTEM='''Describe only the attached image. No editing task or answer key is supplied.
Record readable labels and their positions. Describe relevant objects and their actual
geometry/connectivity. For graphs, record visible axes/domain and compare curves at the
same horizontal or vertical coordinate across the full visible plot, noting intersections
and changes of ordering. Do not infer direction or meaning from a label suffix or color.
Distinguish lines actually drawn from background gradients, borders, and imagined lines.
Do not infer a desired edit or invent missing quantities. Mark illegible/uncertain details.
Return one JSON object {id, labels:[{text,location}],
relations:[{description,location}], uncertainties:[string]}.
Use nonempty strings inside arrays; empty labels/uncertainties arrays are allowed.
At least one spatial relation is required. Locations may use top/bottom/left/right or
approximate image coordinates. Do not claim expertise or correctness certification.'''


def observation_material(row):
    source,content=source_material(row)
    # Discard all public task text too: this diagnostic reads pixels without a goal.
    content[0]={'type':'text','text':json.dumps({'id':row['id']})}
    material={'id':row['id'],'public_source_sha256':source['public_source_sha256'],
              'input_hash':digest({'id':row['id'],'public_source_sha256':source['public_source_sha256']}),
              'system_hash':digest(SYSTEM),'version':VERSION,
              'task_text_provided':False,'reference_provided':False}
    return material,content


def validate_observation(result,id_):
    if not isinstance(result,dict) or result.get('id')!=id_:
        raise ValueError('image observation requires object with requested id')
    for key,fields in (('labels',('text','location')),('relations',('description','location'))):
        values=result.get(key)
        if not isinstance(values,list) or (key=='relations' and not values):
            raise ValueError('image observation requires array '+key)
        if any(not isinstance(v,dict) or any(not isinstance(v.get(f),str) or not v[f].strip() for f in fields) for v in values):
            raise ValueError('invalid image observation '+key)
    if not isinstance(result.get('uncertainties'),list) or any(not isinstance(v,str) for v in result['uncertainties']):
        raise ValueError('image observation requires uncertainties array')
    return result


def load_for_review(row,base):
    path=Path(base)/row['id']/'result.json'
    record=json.loads(path.read_text())
    material,_=observation_material(row)
    if record.get('status')!='observed' or any(record.get(k)!=v for k,v in material.items()):
        raise ValueError('image-only observation is failed, stale, or not bound to this source')
    validate_observation(record['result'],row['id'])
    return record['result'],{'path':str(path.resolve()),'sha256':file_hash(path)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--ids',nargs='+',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--model',default='qwen3.8-flash')
    p.add_argument('--max-calls',type=int,default=12);p.add_argument('--max-tokens',type=int,default=60000)
    args=p.parse_args()
    if args.out.exists():p.error('use a fresh output directory')
    rows={r['id']:r for r in read_jsonl(args.data)}
    if set(args.ids)-rows.keys() or len(set(args.ids))!=len(args.ids):p.error('unknown/duplicate ids')
    if not 1<=args.workers<=4:p.error('use 1-4 workers')
    materials={id_:observation_material(rows[id_])[0] for id_ in args.ids}
    freeze_run(args.out,{'entrypoint':'source_observation','version':VERSION,'ids':args.ids,
                        'materials':materials,'model':args.model,'workers':args.workers,
                        'max_calls':args.max_calls,'max_tokens':args.max_tokens})
    client=MatrixClient(args.out,model=args.model,concurrency=args.workers,
                        max_calls=args.max_calls,max_tokens_total=args.max_tokens)
    def run(id_):
        try:
            material,content=observation_material(rows[id_])
            if material!=materials[id_]:raise ValueError('source material changed after freeze')
            write_json(args.out/id_/'input.json',material)
            result=client.chat([{'role':'system','content':SYSTEM},{'role':'user','content':content}],
                               purpose='image_only:'+id_,max_tokens=2500)
            validate_observation(result,id_)
            record={'id':id_,'status':'observed','result':result,**material,'expert_verified':False}
        except Exception as exc:
            record={'id':id_,'status':'observation_error','error':str(exc)[:240]}
        write_json(args.out/id_/'result.json',record)
        print(id_,record['status'],flush=True)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(run,args.ids))
    write_json(args.out/'summary.json',{'n':len(results),
        'observed':sum(r['status']=='observed' for r in results),'results':results,
        'scope':'Diagnostic model observations only; no question approval or coverage increment.'})


if __name__=='__main__':main()
