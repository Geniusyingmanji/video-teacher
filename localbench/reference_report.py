"""Compare reference policies on exactly the same media; never pool rubric versions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import write_json
from .requirements import checks_from_score_file


def read_results(directory):
    config=json.loads((directory/'run_config.json').read_text())
    expected={(a['id'],a['mode']):a['video_sha256'] for a in config['inputs']}
    result={}
    for p in sorted(directory.glob('*/*/scores.json')):
        row=json.loads(p.read_text());key=(row['case_id'],p.parent.name)
        if key not in expected or row['video_sha256']!=expected[key] or key in result:
            raise ValueError('unexpected or changed scored media')
        result[key]={'score':row,'diagnostics':checks_from_score_file(p,refresh=True)}
    return expected,result


def compare(legacy, contracted):
    a,rows_a=read_results(legacy);b,rows_b=read_results(contracted)
    if a!=b:raise ValueError('reference-policy comparison requires identical planned media')
    result=[]
    for key in sorted(a):
        row={'case_id':key[0],'mode':key[1],'video_sha256':a[key]}
        for label,rows in [('legacy',rows_a),('contract',rows_b)]:
            r=rows.get(key)
            if not r:row[label]={'status':'score_missing'};continue
            s=r['score']
            row[label]={'status':'scored','rubric_version':s['rubric_version'],
                'overall':s['scoring']['overall'],
                'task_completeness':s['dimensions']['task_completeness']['score'],
                'visual_teaching':s['dimensions']['visual_teaching']['score'],
                'major_findings':s['major_findings'],'requirement_findings':s.get('requirement_findings',[]),
                'diagnostics':r['diagnostics'],'case_hash':s['case_hash'],'judge_model':s['judge_model']}
        if row['legacy']['status']==row['contract']['status']=='scored':
            for field in ('case_hash','judge_model'):
                if row['legacy'][field]!=row['contract'][field]:raise ValueError('comparison changed '+field)
        result.append(row)
    return {'scope':'same-media development protocol comparison, not a generation quality improvement or independent calibration',
            'legacy':str(legacy.resolve()),'contract':str(contracted.resolve()),'rows':result}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--legacy',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh report directory')
    report=compare(args.legacy,args.contract)
    write_json(args.out/'comparison.json',report)
    lines=['# 同一媒体的参考协议对照','',
        '每一行的两个协议使用完全相同的视频、题目和 judge。不同协议不混合排名，不把分数变化解释为生成方法提升。',
        '要求诊断在旁路刷新，未改写原始分数文件。标记为失败的是模型观察结论，仍需人工校准。','',
        '| 题目／视频 | 原协议总分 | 新协议总分 | 新协议要求失败 | 新协议未验证要求 |',
        '| --- | --- | --- | --- | --- |']
    def fmt(v):return '未评分' if v is None else f'{v:.2f}'
    for r in report['rows']:
        a,b=r['legacy'],r['contract'];d=b.get('diagnostics',{})
        lines.append(f"| {r['case_id']}/{r['mode']} | {fmt(a.get('overall'))} | {fmt(b.get('overall'))} | {', '.join(d.get('failed',[])) or '—'} | {', '.join(d.get('unverified',[])) or '—'} |")
    lines+=['','## 逐项证据','']
    for r in report['rows']:
        lines += [f"### {r['case_id']} / {r['mode']}",'']
        for f in r['contract'].get('requirement_findings',[]):
            lines.append(f"- `{f['requirement_id']}` / `{f['verdict']}` / {', '.join(f['evidence_ids'])}: {f['reason']}")
        lines.append('')
    (args.out/'COMPARISON.md').write_text('\n'.join(lines),encoding='utf-8')
    print(args.out/'COMPARISON.md')


if __name__=='__main__':main()
