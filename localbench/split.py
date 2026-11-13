"""Conservative development/reserve inventory from traceable local exposure.

Reserve means eligible for future protocol validation, not never seen, curated,
expert-approved, or a frozen benchmark test set.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from .audit import audit, stem
from .common import ROOT, digest, read_jsonl, write_json, write_jsonl
from .provenance import file_hash, freeze_run


def local_exposure(root, ids):
    evidence=collections.defaultdict(list);receipts={}
    def record(path, case_ids, kind):
        selected=sorted(set(case_ids)&ids)
        if not selected:return
        relative=str(path.relative_to(root))
        receipts[relative]={'sha256':file_hash(path),'kind':kind,'matched_ids':selected}
        for id_ in selected:evidence[id_].append({'kind':kind,'path':relative})
    membership=root/'data/development_membership.json'
    if membership.is_file():
        rows=json.loads(membership.read_text())['cases']
        record(membership,[r['id'] for r in rows],'retained_development_membership')
    # Continuous trials and downloaded Linux runs live below multiple levels.
    # A shallow glob wrongly returned their selected cases to the reserve pool.
    # Read only named experiment inventories, not candidate banks, source caches,
    # or arbitrary JSON that happens to mention an ID.
    for path in sorted(root.glob('results/**/manifest.json')):
        r=json.loads(path.read_text())
        if not isinstance(r,dict):continue
        selected=[c.get('id',c.get('case_id')) for c in r.get('cases',[]) if isinstance(c,dict)]
        if isinstance(r.get('planned_ids'),list):selected+=r['planned_ids']
        record(path,selected,'generation_or_evaluation_development_inventory')
    for folder in ('results',):
        for name in ('tasks.jsonl','evaluation_tasks.jsonl','generation_inputs.jsonl'):
            for path in sorted((root/folder).glob('**/'+name)):
                record(path,[r.get('id',r.get('case_id')) for r in read_jsonl(path)],
                       'designated_experiment_tasks')
    for path in sorted(root.glob('results/**/case.json')):
        r=json.loads(path.read_text())
        if isinstance(r,dict):record(path,[r.get('id',r.get('case_id'))],'single_case_trial_input')
    for path in sorted(root.glob('results/eval_*/*/*/scores.json')):
        r=json.loads(path.read_text());record(path,[r['case_id']],'local_video_evaluation')
    return dict(evidence),receipts


def assign(rows, exposure, near_pairs):
    ids={r['id'] for r in rows}
    if len(ids)!=len(rows):raise ValueError('duplicate case IDs')
    parents={id_:id_ for id_ in ids}
    def find(id_):
        while parents[id_]!=id_:
            parents[id_]=parents[parents[id_]];id_=parents[id_]
        return id_
    edges=[]
    def union(a,b,kind):
        if a not in ids or b not in ids:raise ValueError('relation references unknown case')
        aa,bb=find(a),find(b)
        if aa!=bb:parents[max(aa,bb)]=min(aa,bb)
        edges.append({'left':a,'right':b,'kind':kind})
    buckets=collections.defaultdict(list)
    for row in rows:
        source=row.get('source',{})
        if source.get('dataset') and source.get('source_id'):
            buckets[('source_record',source['dataset'],str(source['source_id']))].append(row['id'])
        if source.get('dataset') and source.get('source_image_path'):
            buckets[('source_image',source['dataset'],source['source_image_path'])].append(row['id'])
        core=stem(row)
        if core:buckets[('same_core_prompt',core)].append(row['id'])
    for key,values in sorted(buckets.items()):
        for id_ in sorted(values)[1:]:union(min(values),id_,key[0])
    for a,b in sorted(near_pairs):union(a,b,'near_duplicate_candidate_not_confirmed')
    groups=collections.defaultdict(list)
    for id_ in sorted(ids):groups[find(id_)].append(id_)
    records=[]
    for group in sorted(groups.values()):
        used=sorted(set(group)&set(exposure))
        group_id='g_'+digest(group)[:16]
        for id_ in group:
            records.append({'id':id_,'group_id':group_id,
                            'partition':'development' if used else 'reserved_candidate',
                            'reason':('retained_development_membership' if id_ in exposure and exposure[id_] and all(e.get('kind')=='retained_development_membership' for e in exposure[id_]) else 'direct_local_evidence' if id_ in exposure else 'related_to_development' if used else 'no_matching_local_exposure_evidence'),
                            'direct_exposure':exposure.get(id_,[]),'development_group_members':used})
    return sorted(records,key=lambda r:r['id']),edges


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh output directory')
    rows=read_jsonl(args.data)
    exposure,receipts=local_exposure(ROOT,{r['id'] for r in rows})
    near_pairs=[(r['id'],p['id']) for r in audit(rows) for p in r['near_duplicate_candidates']]
    assignment,edges=assign(rows,exposure,near_pairs)
    config={'entrypoint':'development_reserve_inventory','dataset_sha256':file_hash(args.data),
            'exposure_receipts':receipts,'near_duplicate_rule':'existing audit core-prompt ratio >= 0.87 within raw discipline',
            'policy':'Conservative connected components; no score-based selection; reserve is not an unseen/test claim.'}
    freeze_run(args.out,config)
    write_jsonl(args.out/'assignment.jsonl',assignment)
    write_json(args.out/'relations.json',edges)
    by_id={r['id']:r for r in rows}
    summary={'n':len(rows),'partition':dict(collections.Counter(r['partition'] for r in assignment)),
             'reasons':dict(collections.Counter(r['reason'] for r in assignment)),
             'n_groups':len({r['group_id'] for r in assignment}),'n_exposure_files':len(receipts),
             'n_near_duplicate_candidate_edges':len(near_pairs),
             'expert_approved':sum(bool(r.get('local_review',{}).get('expert_content_verified')) for r in rows),
             'held_out_claim':False,
             'coverage':{},'scope':'Local evidence inventory; external/remote exposure may be missing.'}
    for partition in ('development','reserved_candidate'):
        selected=[by_id[r['id']] for r in assignment if r['partition']==partition]
        write_jsonl(args.out/(partition+'.jsonl'),selected)
        summary['coverage'][partition]={
            'task':dict(collections.Counter(r['task_type'] for r in selected)),
            'scope':dict(collections.Counter(r['benchmark_scope'] for r in selected)),
            'discipline_task':dict(sorted(collections.Counter(r['discipline_canonical']+'/'+r['task_type'] for r in selected).items()))}
    write_json(args.out/'summary.json',summary)
    lines=['# 开发／后续验证候选清单','',
           '按本地可追溯的生成、评分、模型审查和明确开发题单划分，不读取分数做筛选。',
           '同源记录、同源图、相同核心题面和近重复候选组成连通分组；有开发证据的整组归入开发。',
           '保留候选不是从未见过的测试集；来源构建、编辑和全量结构检查已涉及整个题库，远端运行历史还可能缺失。','',
           f"题目数：{summary['n']}；分配：`{summary['partition']}`；原因：`{summary['reasons']}`。",
           f"分组：{summary['n_groups']}；证据文件：{len(receipts)}；近重复候选边：{len(near_pairs)}；专家批准：{summary['expert_approved']}。",'',
           '| 学科 / 任务 | 开发 | 后续验证候选 |','| --- | --- | --- |']
    keys=sorted({k for c in summary['coverage'].values() for k in c['discipline_task']})
    for k in keys:lines.append(f"| {k} | {summary['coverage']['development']['discipline_task'].get(k,0)} | {summary['coverage']['reserved_candidate']['discipline_task'].get(k,0)} |")
    lines+=['','`assignment.jsonl` 给出逐题原因；`relations.json` 给出分组边；`run_config.json` 冻结来源哈希与代码。',
            '下一步先审查候选的质量和覆盖缺口。未来使用任何保留题调试后，应更新开发成员清单，避免之后重新进入预留候选。',
            '正式冻结需补齐远端曝光历史、题目裁定、独立难度及人工校准；当前清单不能替代这些步骤。','']
    (args.out/'SPLIT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='coverage'},ensure_ascii=False))


if __name__=='__main__':main()
