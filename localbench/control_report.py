"""Reproducible report of fixed audio controls, without changing existing scores."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from .common import write_json
from .controls import decoded_video_hash
from .provenance import file_hash
from .requirements import checks_from_score_file
from .rubric import DIMENSIONS


def collect(run, evaluation, previous=None, verify_frames=False):
    manifest=json.loads((run/'manifest.json').read_text())
    truth=json.loads((run/'control_truth.json').read_text())
    rows=[]
    for case in manifest['cases']:
        for artifact in case['artifacts']:
            id_,mode=case['id'],artifact['mode']
            video=Path(artifact['video_path'])
            if file_hash(video)!=artifact['sha256']:raise ValueError('control media hash changed')
            p=evaluation/id_/mode/'scores.json'
            if not p.exists():
                rows.append({'case_id':id_,'mode':mode,'status':'missing_evaluation'})
                continue
            s=json.loads(p.read_text())
            if s['video_sha256']!=artifact['sha256'] or s['case_id']!=id_:
                raise ValueError('score does not refer to the specified control media')
            receipt=next(r for r in truth['records'][id_] if r['mode']==mode)
            decoded=None
            if verify_frames:
                decoded,n,_=decoded_video_hash(video)
                if decoded!=artifact['decoded_video_sha256']:raise ValueError('decoded frame hash changed')
            audio=json.loads((p.parent/'actual_audio.json').read_text())
            alignment=s['dimensions']['crossmodal_alignment']
            probes=json.loads((p.parent/'alignment_probes.json').read_text()) if (p.parent/'alignment_probes.json').exists() else []
            by_probe={p['id']:p for p in probes}
            observations=[]
            for obs in alignment.get('observations',[]):
                probe=by_probe.get(obs['probe_id'],{})
                observations.append({**obs,'start_s':probe.get('start_s'),'end_s':probe.get('end_s')})
            prior_path=previous/id_/mode/'scores.json' if previous else None
            prior=json.loads(prior_path.read_text()) if prior_path and prior_path.exists() else None
            if prior and prior['video_sha256']!=artifact['sha256']:raise ValueError('previous evaluation used different media')
            rows.append({'case_id':id_,'mode':mode,'status':'scored','score_path':str(p.resolve()),
                         'rubric_version':s['rubric_version'],'judge_model':s['judge_model'],
                         'video_sha256':artifact['sha256'],
                         'decoded_video_sha256':artifact['decoded_video_sha256'],
                         'decoded_hash_rechecked':decoded is not None,'control_receipt':receipt,
                         'dimensions':{k:v['score'] for k,v in s['dimensions'].items()},
                         'prior_dimensions':{k:v['score'] for k,v in prior['dimensions'].items()} if prior else None,
                         'overall':s['scoring']['overall'],'output_checks':checks_from_score_file(p),
                         'digital_silence_chunks':sum(bool(a.get('digital_silence')) for a in audio),
                         'observed_no_speech_chunks':sum(bool(a.get('digital_silence') or a.get('narration_presence',{}).get('status')=='observed_absent') for a in audio),
                         'n_audio_chunks':len(audio),
                         'transcript_characters':sum(len(a.get('transcript') or '') for a in audio),
                         'alignment_observations':observations,
                         'dimension_reasons':{k:v.get('criteria',{}) for k,v in s['dimensions'].items()}})
    scored=[r for r in rows if r['status']=='scored']
    invariance={}
    for case in manifest['cases']:
        variants=[r for r in scored if r['case_id']==case['id']]
        invariance[case['id']]={
            'n_scored':len(variants),'n_planned':len(case['artifacts']),
            'same_decoded_frames':len({a['decoded_video_sha256'] for a in case['artifacts']})==1 if len(case['artifacts'])>1 else None,
            'all_frame_hashes_rechecked':all(r['decoded_hash_rechecked'] for r in variants) and len(variants)==len(case['artifacts']),
            'presentation_score_invariance':{k:len({r['dimensions'][k] for r in variants})==1 if len(variants)==len(case['artifacts']) else None
                                            for k in ('visual_quality','temporal_consistency')}}
    return {'control_manifest_sha256':file_hash(run/'manifest.json'),
            'evaluation':str(evaluation.resolve()),'previous_evaluation':str(previous.resolve()) if previous else None,
            'n_planned':len(rows),'n_scored':len(scored),'rows':rows,'invariance':invariance,
            'scope':'Fixed development controls used to debug this protocol; not independent validation or human calibration.',
            'score_policy':'Original scores unchanged; no caps or acceptance threshold inferred from this experiment.'}


def markdown(report):
    def fmt(value):return '未验证' if value is None else f'{value:.2f}'
    modes=sorted({r['mode'] for r in report['rows']})
    lines=['# 音频对照实验：最终媒体与评分诊断','',
           '本次版本：`'+', '.join(modes)+'`。clean 为原旁白；muted 为静音；shifted 为循环错位；tones 为无语音的纯音。错位秒数记录在 JSON 控制收据中。',
           '控制标签只用于本报告，未交给评委。实验参与过协议调试，不能当作独立验证集。','',
           '| 题目 | 版本 | 音频质量 | 音画配合 | 旧协议音画配合 | 综合分 | 要求失败 |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    for r in report['rows']:
        if r['status']!='scored':
            lines.append(f"| {r['case_id']} | {r['mode']} | 缺失 | 缺失 | — | 缺失 | 未验证 |")
            continue
        d=r['dimensions'];old=(r['prior_dimensions'] or {}).get('crossmodal_alignment')
        lines.append(f"| {r['case_id']} | {r['mode']} | {fmt(d['audio_quality'])} | {fmt(d['crossmodal_alignment'])} | {fmt(old)} | {fmt(r['overall'])} | {', '.join(r['output_checks']['failed']) or '未检出'} |")
    lines+=['','## 不变量与证据检查','']
    for id_,r in report['invariance'].items():
        lines.append(f"- `{id_}`：评分完成 {r['n_scored']}/{r['n_planned']}；解码后画面相同：{r['same_decoded_frames']}；本次重查全部帧哈希：{r['all_frame_hashes_rechecked']}；两项呈现分保持一致：{all(r['presentation_score_invariance'].values())}。")
    for r in report['rows']:
        if r['status']=='scored' and r['mode'] in ('muted','tones'):
            lines.append(f"- `{r['case_id']}/{r['mode']}`：{r['digital_silence_chunks']}/{r['n_audio_chunks']} 段为已验证数字静音；{r['observed_no_speech_chunks']}/{r['n_audio_chunks']} 段被标记无旁白；转写字符数 {r['transcript_characters']}。")
    lines+=['','## 时间配对观察','',
            '下列是评委对实际 ASR 时间窗与邻近帧的观察；时间戳近似，观察仍可能误判。','']
    for r in report['rows']:
        if r['status']!='scored':continue
        obs=r['alignment_observations']
        if not obs:continue
        counts=dict(collections.Counter(x['verdict'] for x in obs))
        lines+=[f"### {r['case_id']} / {r['mode']}",'',f'观察计数：`{counts}`。','']
        for o in obs:
            if o['verdict']!='misaligned':continue
            lines.append(f"- `{o['probe_id']}` ({o['start_s']:.2f}–{o['end_s']:.2f}s)，证据 {', '.join(o['evidence_ids'])}：{o['reason']}")
        lines.append('')
    lines+=['## 仍需解决的问题','',
            '- 综合分会稀释旁白缺失或音画错位；分数不变，另列要求失败与证据。不得把高均分解读为要求全部达成。',
            '- 当前只验证两道题和较大错位，不能估计微小延迟、自然录音、复杂镜头的检出率，也不能证明其他维度可靠。',
            '- 数字静音检查不覆盖有声信号；dev8 另以实际听音判断和 VAD 交叉核对无语音。检测分歧保留未验证，非空英文 ASR 不能单独证明原始音轨语言正确。',
            '- 需要新控制例和独立人工逐维评分；本报告不导入人工评分。','',
            '## 需要裁定的评分变化','',
            '音频变化可能影响整体教学解释，但不应凭空改变可见对象数量。保留以下评分与具体理由供复核，不自动改分。','']
    by_key={(r['case_id'],r['mode']):r for r in report['rows'] if r['status']=='scored'}
    for (id_,mode),r in by_key.items():
        if mode!='muted' or (id_,'clean') not in by_key:continue
        clean=by_key[id_,'clean']
        for k in ('conceptual_correctness','visual_teaching'):
            if r['dimensions'][k]!=clean['dimensions'][k]:
                lines.append(f"- `{id_}` {DIMENSIONS[k]['name']}：原版 {fmt(clean['dimensions'][k])}，静音 {fmt(r['dimensions'][k])}。")
                for c,v in r['dimension_reasons'][k].items():
                    lines.append(f"  - `{c}`：{v['reason']}")
        if r['dimensions']['task_completeness']==100:
            lines.append(f'- `{id_}/muted`：任务完成满分与共同任务要求中的旁白缺失并存，需明确覆盖维度与交付要求的边界。')
    lines.append('')
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--eval',type=Path,required=True)
    p.add_argument('--previous',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--verify-video-frames',action='store_true')
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh report directory')
    result=collect(args.run,args.eval,args.previous,args.verify_video_frames)
    write_json(args.out/'control_validation.json',result)
    (args.out/'CONTROL-VALIDATION.md').write_text(markdown(result),encoding='utf-8')
    print(args.out/'CONTROL-VALIDATION.md')


if __name__=='__main__':main()
