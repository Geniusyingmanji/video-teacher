"""Paired per-task development summaries with explicit missingness and uncertainty."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .common import write_json
from .rubric import DIMENSIONS
from .requirements import checks_from_score_file


def paired_summary(rows, left='code', right='slides', seed=20261111, expected_ids=()):
    by_key = {(r['case_id'],r['mode']):r for r in rows}
    if len(by_key)!=len(rows):
        raise ValueError('duplicate case/mode scores cannot be pooled')
    ids = sorted({r['case_id'] for r in rows}|set(expected_ids))
    rng = np.random.default_rng(seed)
    output = {}
    for name in [*DIMENSIONS,'overall']:
        a,b,paired_ids = [],[],[]
        for id_ in ids:
            l,r = by_key.get((id_,left)),by_key.get((id_,right))
            if l is None or r is None:
                continue
            lv = l['scoring']['overall'] if name=='overall' else l['dimensions'][name].get('score')
            rv = r['scoring']['overall'] if name=='overall' else r['dimensions'][name].get('score')
            if lv is not None and rv is not None:
                a.append(lv);b.append(rv);paired_ids.append(id_)
        diff=np.asarray(a)-np.asarray(b)
        ci=None
        if len(diff)>=2:
            sampled=rng.choice(diff,size=(10000,len(diff)),replace=True).mean(axis=1)
            ci=np.quantile(sampled,[.025,.975]).tolist()
        output[name]={'n_pairs':len(diff),'n_tasks':len(ids),'paired_ids':paired_ids,
                      'missing_ids':sorted(set(ids)-set(paired_ids)),
                      'left_mean':float(np.mean(a)) if a else None,
                      'right_mean':float(np.mean(b)) if b else None,
                      'mean_delta':float(np.mean(diff)) if len(diff) else None,
                      'bootstrap_95_ci':ci}
    return {'left':left,'right':right,'dimensions':output,'seed':seed,
            'inference_scope':'descriptive development sample; bootstrap captures task sampling only, not judge bias or human agreement'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--eval',type=Path,required=True)
    p.add_argument('--left',default='code')
    p.add_argument('--right',default='slides')
    args=p.parse_args()
    rows=[]
    for path in sorted(args.eval.glob('*/*/scores.json')):
        row=json.loads(path.read_text());row['mode']=path.parent.name
        row['output_checks']=checks_from_score_file(path);rows.append(row)
    if not rows:p.error('no per-video scores found')
    if len({(r['rubric_version'],r['judge_model']) for r in rows})!=1:
        p.error('do not mix rubric/model versions')
    config=json.loads((args.eval/'run_config.json').read_text()) if (args.eval/'run_config.json').exists() else {}
    report=paired_summary(rows,args.left,args.right,expected_ids=config.get('planned_cases',[]))
    planned=set(config.get('planned_cases',[]))|{r['case_id'] for r in rows}
    report['requirements_by_mode']={}
    for mode in (args.left,args.right):
        subset=[r for r in rows if r['mode']==mode]
        report['requirements_by_mode'][mode]={
            'n_planned_tasks':len(planned),'n_scored_videos':len(subset),
            'n_complete_overall_scores':sum(r['scoring']['overall'] is not None for r in subset),
            'missing_score_ids':sorted(planned-{r['case_id'] for r in subset}),
            'failed':{r['case_id']:r['output_checks']['failed'] for r in subset if r['output_checks']['failed']},
            'review':{r['case_id']:r['output_checks']['review'] for r in subset if r['output_checks']['review']},
            'unverified':{r['case_id']:r['output_checks']['unverified'] for r in subset if r['output_checks']['unverified']}}
    write_json(args.eval/'paired_summary.json',report)
    def fmt(x):return '未验证' if x is None else f'{x:.2f}'
    lines=['# 同题配对开发结果','',
           '小批量、未人工校准；不能据此宣称学生学习提升或完整方法优于其他模型。',
           '每个维度只使用两侧均有有效分数的同题结果，缺失项保留。置信区间仅反映题目抽样，不包含 judge 偏差。','',
           f'| 维度 | 有效题对 | {args.left} | {args.right} | 差值 | Bootstrap 95% CI |',
           '| --- | --- | --- | --- | --- | --- |']
    for name,item in report['dimensions'].items():
        label=DIMENSIONS[name]['name'] if name in DIMENSIONS else '综合分'
        ci=item['bootstrap_95_ci']
        lines.append(f"| {label} | {item['n_pairs']}/{item['n_tasks']} | {fmt(item['left_mean'])} | {fmt(item['right_mean'])} | {fmt(item['mean_delta'])} | {f'[{ci[0]:.2f}, {ci[1]:.2f}]' if ci else '样本不足'} |")
    errors=list(args.eval.glob('*/*/error.json'))
    lines+=['',f'有评分记录的视频：{len(rows)}；有完整总分：{sum(r["scoring"]["overall"] is not None for r in rows)}；评测失败记录：{len(errors)}。失败视频未作为零分进入均值。','']
    lines+=['## 交付要求与评分覆盖','',
            '均值不代表要求全部达成。下面并列显示失败、待核查与未验证；不改变原始分数，也不筛掉低质量结果。','']
    for mode,r in report['requirements_by_mode'].items():
        lines.append(f"- `{mode}`：{r['n_scored_videos']}/{r['n_planned_tasks']} 题有评分记录，{r['n_complete_overall_scores']} 题有完整总分；要求失败 {len(r['failed'])} 题；待核查 {len(r['review'])} 题；要求证据不全 {len(r['unverified'])} 题。")
        if r['failed']:lines.append('  - 失败明细：`'+json.dumps(r['failed'],ensure_ascii=False)+'`。')
    (args.eval/'COMPARISON.md').write_text('\n'.join(lines),encoding='utf-8')
    print(args.eval/'COMPARISON.md')


if __name__=='__main__':main()
