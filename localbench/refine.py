"""Refine existing public-input plans; preserve originals and all model proposals."""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
from pathlib import Path

from .client import MatrixClient
from .common import ROOT, digest, public_case, read_jsonl, write_json
from .content_review import review_and_repair
from .pipeline import resolve_source_plan
from .provenance import file_hash, freeze_run
from .scene import PLAN_SYSTEM, inspect_layout, validate_plan


def apply_diagrams(plan, raw, *, allow_noop=False):
    """Replace bounded visual primitives only; retain every nonvisual field exactly."""
    if not isinstance(raw,dict) or set(raw)!={'replacements'} or not isinstance(raw['replacements'],list) or not 1<=len(raw['replacements'])<=len(plan['scenes']):
        raise ValueError('diagram refinement needs bounded scene replacements')
    fixed=copy.deepcopy(plan);seen=set()
    for r in raw['replacements']:
        if not isinstance(r,dict) or set(r)!={'scene','primitives'} or type(r['scene']) is not int or not 0<=r['scene']<len(plan['scenes']) or r['scene'] in seen:
            raise ValueError('invalid or repeated diagram scene replacement')
        i=r['scene'];seen.add(i)
        if plan['scenes'][i].get('source_visual') or plan['scenes'][i].get('state_visual'):
            raise ValueError('diagram refinement cannot override source or state visual backends')
        if not isinstance(r['primitives'],list) or not 1<=len(r['primitives'])<=36 or any(not isinstance(p,dict) for p in r['primitives']):
            raise ValueError('replacement requires 1..36 primitive objects')
        fixed['scenes'][i]['primitives']=copy.deepcopy(r['primitives'])
    if fixed==plan and not allow_noop:raise ValueError('no diagram change proposed')
    return fixed


def diagram_fidelity(client,case,plan,out):
    request={'public_task':public_case(case),'proposed_plan':plan}
    write_json(out/'diagram_input.json',request)
    messages=[{'role':'system','content':PLAN_SYSTEM+'''
For this call return ONLY {replacements:[{scene:zero_based_index,primitives:[...]}]}.
Review how the current diagrams demonstrate the public task and existing narration.
Replace misleading or missing spatial relationships with directly inspectable diagrams.
Preserve every narration, title, caption, slide_text, duration and other non-primitive field.
Use the spatial primitives documented above. Use flow_path for directed spiral flows.
Keep required entities visible together when the task asks for a held final state.
Do not invent quantitative measurements, axis units or formulas for a qualitative diagram.
Do not treat a label naming a requested structure as a substitute for depicting it.
Retain scenes whose diagrams already satisfy the task. Leave source/state visual scenes alone.
This call repairs visuals only; it cannot resolve errors in existing narration or captions.'''},
        {'role':'user','content':json.dumps(request,ensure_ascii=False)}]
    for attempt in range(3):
        raw=client.chat(messages,purpose='diagram_fidelity:'+case['id'],max_tokens=5200)
        write_json(out/f'diagram_proposal_{attempt}.json',raw)
        try:
            fixed=apply_diagrams(plan,raw)
            validate_plan(fixed,case)
            issues=inspect_layout(fixed)
            if issues:raise ValueError('layout defects: '+json.dumps(issues[:8]))
            return fixed
        except (ValueError,KeyError,TypeError) as exc:
            write_json(out/f'diagram_error_{attempt}.json',{'error':str(exc)})
            if attempt==2:raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                {'role':'user','content':'Correct the schema/layout error while preserving the same public task and nonvisual fields: '+str(exc)}])


def apply_charts(plan, raw):
    if not isinstance(raw,dict) or not isinstance(raw.get('replacements'),list) or not 1<=len(raw['replacements'])<=len(plan['scenes']):
        raise ValueError('plot refinement needs bounded scene replacements')
    fixed=copy.deepcopy(plan)
    seen=set()
    for r in raw['replacements']:
        if not isinstance(r,dict) or set(r)!={'scene','primitives'} or type(r['scene']) is not int or not 0<=r['scene']<len(plan['scenes']) or r['scene'] in seen:
            raise ValueError('invalid plot scene replacement')
        seen.add(r['scene'])
        ps=r['primitives']
        if not isinstance(ps,list) or len(ps)!=1 or ps[0].get('type')!='chart':
            raise ValueError('plot replacement must be exactly one data chart')
        from .chart import compile_chart
        compile_chart(ps[0])
        fixed['scenes'][r['scene']]['primitives']=ps
    return fixed


def numeric_plots(client, case, plan, out):
    request={'public_task':public_case(case),'proposed_plan':plan}
    write_json(out/'plot_input.json',request)
    messages=[{'role':'system','content':PLAN_SYSTEM+'''
For this call return ONLY {replacements:[{scene:zero_based_index,primitives:[one_chart]}]}.
Convert existing quantitative trend diagrams to data-driven chart primitives. Infer the
quantity, data/formula and units from the PUBLIC task and current explanation. Preserve every
spoken/visible claim outside replaced primitives. Do not replace cash-flow summaries, equations,
or decorative shapes unrelated to a numeric plot. Use labelled axes; exact numeric expressions
are preferable to manually rounded y values. This is a diagram compiler upgrade, not a rewrite.
The supplied old diagram may have erroneous pixel positions: derive data from the public givens.
Return no empty replacements if a quantitative trend plot is present.'''},
        {'role':'user','content':json.dumps(request,ensure_ascii=False)}]
    for attempt in range(2):
        raw=client.chat(messages,purpose='numeric_plot_upgrade:'+case['id'],max_tokens=2400)
        write_json(out/f'plot_proposal_{attempt}.json',raw)
        try:return apply_charts(plan,raw)
        except ValueError as exc:
            if attempt:raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                             {'role':'user','content':'Correct this schema/numeric error: '+str(exc)}])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--plans-from',type=Path,required=True)
    p.add_argument('--ids',nargs='+',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--numeric-plots',action='store_true')
    p.add_argument('--diagrams',action='store_true',help='Refine spatial task fidelity while preserving narration and timing')
    p.add_argument('--review-content',action='store_true')
    p.add_argument('--claim-quotes',type=Path,help='Experimental targeted repair: JSON mapping case IDs to exact quotes')
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--max-calls',type=int,default=32)
    p.add_argument('--max-tokens',type=int,default=260000)
    args=p.parse_args()
    if not(args.numeric_plots or args.diagrams or args.review_content or args.claim_quotes):p.error('choose at least one refinement')
    if args.out.exists():p.error('use a new output directory')
    rows={r['id']:r for r in read_jsonl(args.data)}
    if len(set(args.ids))!=len(args.ids) or any(x not in rows or Path(x).name!=x for x in args.ids):
        p.error('IDs must be unique known path components')
    sources={id_:resolve_source_plan(args.plans_from,id_) for id_ in args.ids}
    claim_quotes=json.loads(args.claim_quotes.read_text()) if args.claim_quotes else {}
    if args.claim_quotes and (not isinstance(claim_quotes,dict) or set(claim_quotes)!=set(args.ids)):
        p.error('claim quote mapping must match selected case IDs')
    freeze_run(args.out,{'entrypoint':'refine','model':'qwen3.8-flash','ids':args.ids,
        'source_plans':{k:{'path':str(v.resolve()),'sha256':file_hash(v)} for k,v in sources.items()},
        'public_input_hashes':{k:digest(public_case(rows[k])) for k in args.ids},
        'numeric_plots':args.numeric_plots,'diagrams':args.diagrams,'review_content':args.review_content,
        'claim_quotes':claim_quotes,
        'workers':args.workers,'max_calls':args.max_calls,'max_tokens':args.max_tokens})
    client=MatrixClient(args.out,model='qwen3.8-flash',concurrency=args.workers,
                        max_calls=args.max_calls,max_tokens_total=args.max_tokens)
    def work(id_):
        out=args.out/id_;out.mkdir(parents=True)
        plan=json.loads(sources[id_].read_text());case=rows[id_]
        write_json(out/'original.json',plan)
        try:
            if args.claim_quotes:
                from .claim_scope import repair_targeted_claims
                plan=repair_targeted_claims(client,case,plan,claim_quotes[id_],out/'claim_scope')
            if args.numeric_plots:plan=numeric_plots(client,case,plan,out)
            if args.diagrams:plan=diagram_fidelity(client,case,plan,out)
            if args.review_content:plan=review_and_repair(client,case,plan,out/'content')
            validate_plan(plan,case)
            issues=inspect_layout(plan)
            if issues:raise ValueError('refined layout defects: '+json.dumps(issues[:8]))
            write_json(out/'plan.json',plan)
            result={'id':id_,'status':'refined','plan_hash':digest(plan),'requires_final_media_evaluation':True}
        except Exception as exc:
            write_json(out/'failed_plan.json',plan)
            result={'id':id_,'status':'refinement_failed','error':str(exc)[:2000]}
        write_json(out/'status.json',result);print(json.dumps(result),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(work,args.ids))
    write_json(args.out/'summary.json',results)


if __name__=='__main__':main()
