"""Exact-media judge/human comparison; no synthetic ratings in study results."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np

from .common import read_jsonl, write_json
from .human import validated_responses
from .provenance import file_hash
from .rubric import DIMENSIONS


def criterion_score(score, dimension, criterion):
    value=score.get('dimensions',{}).get(dimension,{})
    if value.get('score') is None:return None
    if dimension!='audio_quality':
        c=value.get('criteria',{}).get(criterion,{})
        return c.get('score') if c.get('status')=='observed' else None
    chunks=value.get('chunk_reviews',[])
    if not chunks or any(c.get('status')!='reviewed' for c in chunks):return None
    weights=[c['end_s']-c['start_s'] for c in chunks]
    if any(w<=0 for w in weights):return None
    scores=[c.get('criteria',{}).get(criterion,{}).get('score') for c in chunks]
    if any(s is None for s in scores):return None
    return float(np.average(scores,weights=weights))


def rank(values):
    a=np.asarray(values,dtype=float)
    # Average ranks for ties, preserving small ordinal scales.
    return np.array([1+np.sum(a<x)+(np.sum(a==x)-1)/2 for x in a])


def metrics(pairs, seed=20261111, draws=4000):
    if not pairs:return {'n_videos':0,'n_tasks':0,'mae':None,'mean_judge_minus_human':None,
                         'spearman':None,'cluster_bootstrap_mae_95_ci':None}
    human=np.array([p['human_mean'] for p in pairs]);judge=np.array([p['judge'] for p in pairs])
    error=judge-human
    grouped=collections.defaultdict(list)
    for p,e in zip(pairs,error):grouped[p['case_id']].append(abs(float(e)))
    ci=None
    if len(grouped)>=2:
        clusters=[np.asarray(v) for v in grouped.values()]
        sums=np.array([v.sum() for v in clusters]);counts=np.array([len(v) for v in clusters])
        indices=np.random.default_rng(seed).integers(len(clusters),size=(draws,len(clusters)))
        boot=sums[indices].sum(axis=1)/counts[indices].sum(axis=1)
        ci=np.quantile(boot,[.025,.975]).tolist()
    hr,jr=rank(human),rank(judge)
    corr=float(np.corrcoef(hr,jr)[0,1]) if len(pairs)>=3 and np.ptp(hr)>0 and np.ptp(jr)>0 else None
    return {'n_videos':len(pairs),'n_tasks':len(grouped),'mae':float(np.abs(error).mean()),
            'mean_judge_minus_human':float(error.mean()),'spearman':corr,
            'cluster_bootstrap_mae_95_ci':ci}


def compare(assignments,responses,mapping,judge_scores,min_raters=2,seed=20261111):
    if min_raters<2:raise ValueError('at least two human raters required for a consensus comparison')
    accepted,rejected,unrated=validated_responses(assignments,responses)
    by_item=collections.defaultdict(list)
    for r in accepted:by_item[r['item_id']].append(r)
    items={m['item_id']:m for m in mapping}
    if len(items)!=len(mapping):raise ValueError('duplicate mapped item')
    if set(judge_scores)-set(items):raise ValueError('unknown item in paired judge scores')
    output={}
    for d,spec in DIMENSIONS.items():
        output[d]={}
        for c in spec['criteria']:
            pairs=[];missing=[]
            for item,m in items.items():
                ratings=[r['dimensions'][d][c]['score'] for r in by_item.get(item,[])]
                usable=[s for s in ratings if s is not None]
                value=criterion_score(judge_scores[item],d,c) if item in judge_scores else None
                if len(usable)<min_raters or value is None:
                    missing.append({'item_id':item,'n_human_scores':len(usable),
                                    'judge_available':value is not None})
                    continue
                pairs.append({'item_id':item,'case_id':m['case_id'],'mode':m['mode'],
                              'human_mean':sum(usable)/len(usable),'n_human_scores':len(usable),'judge':value})
            output[d][c]={**metrics(pairs,seed),'pairs':pairs,'missing':missing}
    matched=sum(bool(v['n_videos']) for dim in output.values() for v in dim.values())
    return {'status':'no_human_ratings' if not accepted else 'paired_ratings_available' if matched else 'no_usable_pairs',
            'n_accepted':len(accepted),'rejected':rejected,'unrated_assignments':unrated,
            'n_judge_matched_videos':len(judge_scores),'n_planned_videos':len(items),
            'min_raters':min_raters,'seed':seed,'criteria':output,
            'scale':'1-5 criterion points; human mean of >=2 valid ratings; audio judge duration weighted',
            'inference':'Descriptive agreement with task-clustered bootstrap; intervals do not measure systematic expert/judge bias or certify validity.'}


def match_scores(study,evaluations):
    mapping=json.loads((study/'coordinator/mapping.json').read_text())
    config=json.loads((study/'run_config.json').read_text())
    expected={m['item_id']:(m['case_id'],m['original_sha256'],config['case_hashes'][m['case_id']],config['rubric_version']) for m in mapping}
    matched={};receipts={};skipped=[]
    for directory in evaluations:
        for p in sorted(directory.glob('*/*/scores.json')):
            score=json.loads(p.read_text())
            identity=(score['case_id'],score['video_sha256'],score['case_hash'],score['rubric_version'])
            items=[item for item,key in expected.items() if identity==key]
            if not items:
                skipped.append({'path':str(p.resolve()),'reason':'no exact case/media/task-hash/rubric match'})
                continue
            for item in items:
                if item in matched:raise ValueError('multiple judge results for one video; select one evaluation per video')
                matched[item]=score;receipts[item]={'score_path':str(p.resolve()),'sha256':file_hash(p)}
    if len({s['judge_model'] for s in matched.values()})>1:raise ValueError('cannot pool different judge models')
    return mapping,matched,receipts,skipped


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--study',type=Path,required=True)
    p.add_argument('--eval',type=Path,nargs='+',required=True)
    p.add_argument('--responses',type=Path,nargs='*',default=[])
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh analysis output file')
    mapping,scores,receipts,skipped=match_scores(args.study,args.eval)
    assignments=read_jsonl(args.study/'coordinator/assignments.jsonl')
    responses=[r for path in args.responses for r in read_jsonl(path)]
    result=compare(assignments,responses,mapping,scores)
    result['judge_score_receipts']=receipts;result['unmatched_scores']=skipped
    result['response_files']=[{'path':str(p.resolve()),'sha256':file_hash(p)} for p in args.responses]
    write_json(args.out,result)
    print({k:result[k] for k in ('status','n_accepted','n_judge_matched_videos','n_planned_videos')})


if __name__=='__main__':main()
