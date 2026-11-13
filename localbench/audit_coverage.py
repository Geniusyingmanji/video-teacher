"""Read-only review coverage with input-version and public-source evidence checks."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from .audit import review_material
from .common import ROOT,digest,read_jsonl,write_json,write_jsonl


def coverage_record(row,reviews,development_ids):
    material=review_material(row)[2]
    source_required=bool(row.get('source',{}).get('source_image_path'))
    evidence=[]
    for review,path in reviews:
        if review.get('id')!=row['id'] or review.get('decision') not in {'usable','revise','reject','needs_expert'}:continue
        same_row=review.get('input_hash')==digest(row)
        bound=bool(review.get('review_input_hash')) and review['review_input_hash']==material['review_input_hash']
        if bound and (not source_required or material['public_source_sha256']):status='bound_current_input'
        elif same_row and not source_required:status='legacy_exact_text_input'
        elif same_row:status='legacy_source_bytes_unverified'
        else:status='current_input_match_unproven'
        evidence.append({'path':str(path),'decision':review['decision'],'input_evidence':status,
                         'whole_row_hash_matches':same_row,'reviewer_model':review.get('reviewer_model')})
    current=any(r['input_evidence'] in {'bound_current_input','legacy_exact_text_input'} for r in evidence)
    return {'id':row['id'],'discipline':row.get('discipline_canonical',row['discipline']),
            'task_type':row['task_type'],'input_type':'source_image' if source_required else 'text',
            'partition':'development' if row['id'] in development_ids else 'reserved_candidate',
            'reviewed_any_version':bool(evidence),'current_review_input_supported':current,
            'whole_row_hash_matches':any(r['whole_row_hash_matches'] for r in evidence),
            'reviews':evidence,'current_material':material,'expert_approved':False}


def summarize(records):
    matrix=[]
    for key in sorted({(r['discipline'],r['task_type'],r['input_type']) for r in records}):
        group=[r for r in records if (r['discipline'],r['task_type'],r['input_type'])==key]
        matrix.append({'discipline':key[0],'task_type':key[1],'input_type':key[2],
            'total':len(group),'development':sum(r['partition']=='development' for r in group),
            'reviewed_any_version':sum(r['reviewed_any_version'] for r in group),
            'current_review_input_supported':sum(r['current_review_input_supported'] for r in group)})
    return {'n':len(records),'reviewed_any_version':sum(r['reviewed_any_version'] for r in records),
            'whole_row_hash_matches':sum(r['whole_row_hash_matches'] for r in records),
            'current_review_input_supported':sum(r['current_review_input_supported'] for r in records),
            'expert_approved':0,'matrix':matrix,
            'scope':'Model-review evidence coverage only. A matching review may reject the question; it is not approval. Legacy source reviews without byte hashes cannot certify the currently present image.'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--runs',type=Path,default=ROOT/'results/localbench')
    p.add_argument('--development',type=Path,default=ROOT/'results/localbench/data_partition_v1/development.jsonl')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh coverage output directory')
    rows=read_jsonl(args.data);dev={r['id'] for r in read_jsonl(args.development)}
    reviews=collections.defaultdict(list)
    for path in sorted(args.runs.glob('audit_*/semantic/*.json')):
        r=json.loads(path.read_text());reviews[r['id']].append((r,path.resolve()))
    records=[coverage_record(r,reviews[r['id']],dev) for r in rows]
    summary=summarize(records)
    summary.update(dataset_hash=digest(rows),development_inventory_hash=digest(sorted(dev)))
    write_json(args.out/'summary.json',summary);write_jsonl(args.out/'cases.jsonl',records)
    lines=['# 题库模型审核覆盖','',
        f"共 {summary['n']} 题；历史任一版本有审核 {summary['reviewed_any_version']} 题；整行哈希与当前一致 {summary['whole_row_hash_matches']} 题；有证据支持审核对应当前输入 {summary['current_review_input_supported']} 题。专家批准 0。",
        '匹配审核也可能要求修改或拒绝题目，不能把“审过”当作可用。整行哈希差异可能只来自编辑元数据，不能直接断言题目内容已改变。旧原图审核未绑定图片字节时，当前原图是否相同记未证明。',
        '开发／保留划分沿用已有库存，只是本地使用记录，不证明保留题未被外部使用。','',
        '| 学科 | 任务 | 输入 | 总题数 | 开发集 | 历史审过 | 当前输入有依据 |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for r in summary['matrix']:
        lines.append('| '+' | '.join(str(r[k]) for k in ('discipline','task_type','input_type','total','development','reviewed_any_version','current_review_input_supported'))+' |')
    (args.out/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print({k:v for k,v in summary.items() if k not in {'matrix','scope'}})


if __name__=='__main__':main()
