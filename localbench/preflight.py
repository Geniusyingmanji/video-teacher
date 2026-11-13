"""Read-only batch contract check and reviewable commands for collaborators."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import shlex
import shutil
import sys
from pathlib import Path

import imageio_ffmpeg

from .common import ROOT, digest, public_case, read_jsonl, write_json, write_jsonl
from .provenance import file_hash
from .state import derive_state


def inspect_cases(rows, ids):
    if not ids or len(ids)!=len(set(ids)):raise ValueError('nonempty unique case IDs required')
    by_id={r['id']:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError('duplicate IDs in source dataset')
    if set(ids)-set(by_id):raise ValueError('requested cases missing from dataset')
    records=[]
    for id_ in ids:
        if Path(id_).name!=id_ or id_ in {'.','..'}:raise ValueError('case ID is not a single path component')
        row=by_id[id_];public=public_case(row);errors=[];notes=[]
        for key in ('prompt_text','task_type','pedagogical_target_audience'):
            if not isinstance(public.get(key),str) or not public[key].strip():errors.append('missing '+key)
        target=public.get('target_duration_s')
        if type(target) not in (int,float) or not math.isfinite(target) or not 50<=target<=105:
            errors.append('main task requires finite target duration 50..105s')
        if public.get('task_type') not in {'explanation','problem_solving'}:errors.append('unknown task_type')
        if public.get('audio_narration_required') is not True:errors.append('full lesson requires spoken narration')
        images=[]
        for a in public.get('public_attachments',[]):
            path=Path(a['local_path']) if a.get('local_path') else None
            if path is None or not path.is_file():errors.append('required public source image unavailable')
            else:images.append({'path':str(path),'sha256':file_hash(path)})
        prompt=public.get('prompt_text') if isinstance(public.get('prompt_text'),str) else ''
        if public.get('public_attachments') and 'replace' not in prompt.split('\n')[0].lower():
            notes.append('current local source renderer does not support this input profile; retain as unsupported if attempted')
        try:state=derive_state(public) if prompt else None
        except (ValueError,KeyError,TypeError) as exc:
            state=None;notes.append('state adapter cannot derive this task: '+str(exc))
        if not row.get('local_review',{}).get('expert_content_verified'):
            notes.append('not expert-approved; development use only')
        records.append({'id':id_,'task_hash':digest(row),'public_input_hash':digest(public),
                        'task_type':public.get('task_type'),'target_duration_s':target,
                        'state_adapter':state['kind'] if state else None,
                        'source_images':images,'errors':errors,'review_notes':notes})
    return records


def scoring_protocol(config):
    from .judge import evaluation_version
    semantic=config.get('semantic_outcomes',False)
    if type(semantic) is not bool:raise ValueError('semantic_outcomes must be a boolean')
    version=evaluation_version(config.get('reference_contracts'),semantic)
    if config.get('scoring_protocol',version)!=version:
        raise ValueError('scoring_protocol differs from selected evaluation flags')
    return version


def command_plan(config, data, ids, output_root):
    scoring_protocol(config)
    python=sys.executable
    generation=output_root/'generation';evaluation=output_root/'evaluation'
    generate=[python,'-m','localbench.pipeline','--data',str(data),'--out',str(generation),
              '--ids',*ids,'--model',config.get('model','qwen3.8-flash'),
              '--workers',str(config.get('render_workers',2)),
              '--modes',*config.get('modes',['code','slides']),
              '--max-calls',str(config.get('generation_max_calls',40)),
              '--max-tokens',str(config.get('generation_max_tokens',400000))]
    if config.get('state_backed'):generate.append('--state-backed')
    evaluate=[python,'-m','localbench.judge','--data',str(data),'--run',str(generation),
              '--out',str(evaluation),'--model',config.get('judge_model',config.get('model','qwen3.8-flash')),
              '--workers',str(config.get('api_workers',4)),
              '--max-calls',str(config.get('evaluation_max_calls',100)),
              '--max-tokens',str(config.get('evaluation_max_tokens',1200000))]
    if config.get('reference_contracts'):
        directory=Path(config['reference_contracts']).expanduser()
        if not directory.is_absolute():directory=ROOT/directory
        evaluate.extend(['--reference-contracts',str(directory.resolve())])
    if config.get('semantic_outcomes'):evaluate.append('--semantic-outcomes')
    return {'generation':generate,'evaluation':evaluate,
            'paired_report':[python,'-m','localbench.compare','--eval',str(evaluation)]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--output-root',type=Path,required=True,help='Fresh planned generation/evaluation parent directory; not created or run')
    args=p.parse_args()
    if args.out.exists():p.error('choose a fresh preflight directory')
    config=json.loads(args.config.read_text())
    try:version=scoring_protocol(config)
    except ValueError as exc:p.error(str(exc))
    actual=file_hash(args.data)
    if config.get('dataset_sha256') and config['dataset_sha256']!=actual:p.error('dataset hash differs from the frozen configuration')
    if args.output_root.exists():p.error('planned batch output root already exists')
    for key in ('api_workers','render_workers','generation_max_calls','evaluation_max_calls',
                'generation_max_tokens','evaluation_max_tokens'):
        if key in config and (type(config[key]) is not int or config[key]<1):p.error('invalid positive integer '+key)
    modes=config.get('modes',['code','slides'])
    if not modes or len(set(modes))!=len(modes) or set(modes)-{'code','slides'}:p.error('invalid rendering modes')
    rows=read_jsonl(args.data)
    records=inspect_cases(rows,config['ids'])
    contract_records=[]
    if config.get('reference_contracts'):
        from .reference_contract import load_contract
        directory=Path(config['reference_contracts']).expanduser()
        if not directory.is_absolute():directory=ROOT/directory
        by_id={r['id']:r for r in rows}
        for record in records:
            try:
                contract=load_contract(directory,by_id[record['id']])
                contract_records.append({'id':record['id'],'hash':digest(contract),
                                         'review_status':contract['review_status'],'expert_verified':False})
            except (OSError,ValueError) as exc:
                record['errors'].append('reference contract unavailable, stale or unreviewed: '+str(exc))
    environment={'platform':platform.platform(),'python':platform.python_version(),
                 'tts_say':shutil.which('say'),'ffmpeg':imageio_ffmpeg.get_ffmpeg_exe(),
                 'packages':{name:importlib.metadata.version(name) for name in ('Pillow','numpy','httpx','imageio-ffmpeg','faster-whisper')}}
    blockers=[{'case_id':r['id'],'errors':r['errors']} for r in records if r['errors']]
    if not environment['tts_say']:blockers.append({'environment':'Current synthesis backend requires macOS say; adapt TTS before using this batch on another system.'})
    commands=command_plan(config,args.data.resolve(),config['ids'],args.output_root.resolve())
    report={'status':'blocked_by_input_or_environment' if blockers else 'input_ready_for_development',
            'config_sha256':file_hash(args.config),'dataset_sha256':actual,'case_records':records,
            'environment':environment,'blockers':blockers,'commands':commands,
            'reference_contracts':contract_records,
            'rubric_version':version,
            'source_hashes':{p.name:file_hash(p) for p in (ROOT/'localbench').glob('*.py')},
            'authorization':'Preflight made no model calls, started no generation, and read no API credential contents.',
            'scope':'Input/environment readiness only; not content approval, generation success or evaluation validity.'}
    write_json(args.out/'preflight.json',report)
    selected={r['id']:r for r in rows}
    write_jsonl(args.out/'public_inputs_for_review.jsonl',[public_case(selected[id_]) for id_ in config['ids']])
    write_jsonl(args.out/'task_snapshot_for_evaluation.jsonl',[selected[id_] for id_ in config['ids']])
    lines=['# 小批实验交接与预检','',f"状态：`{report['status']}`；固定题目：`{', '.join(config['ids'])}`。",
           '这里只验证输入和环境，没有调用模型，也没有替代题目审核。',
           '公开输入审计副本与评测题目快照分开保存。生成 CLI 从题目库读取后，由字段白名单隔离参考；不要手工把评测参考加入模型提示。','',
           '## 执行顺序','',f'在项目根目录 `{ROOT}` 执行。以下是新运行命令，不会覆盖已有实验。','']
    for name,command in commands.items():lines += [f'### {name}','','```bash',shlex.join(command),'```','']
    lines+=['生成后检查 manifest 中全部计划题的状态，再评测已完成成片。失败题保留在统计分母；不得只挑成功视频建立比较。',
            f'本交接协议：`{version}`。当前为 dev11 细化协议；--reference-contracts 和 --semantic-outcomes 作为版本后缀记录。历史 dev8/dev9/dev10 结果不与当前协议合并排名。参考仍为开发编辑复核，专家/人工校准未完成。',
            '凭据由执行者在私有配置或环境变量中设置，不写入本交接包。不自动升级昂贵模型。',
            '当前 TTS 仍依赖 macOS；在 Linux 上须先实现并验证同等英文旁白接口，不能跳过音轨。',
            '修改代码、题目、模型或协议后另建运行目录。此预检记录用于对照，具体执行仍会冻结各阶段代码与输入哈希。','']
    (args.out/'HANDOFF.md').write_text('\n'.join(lines),encoding='utf-8')
    print({'status':report['status'],'cases':len(records),'blockers':len(blockers),'report':str(args.out/'HANDOFF.md')})


if __name__=='__main__':main()
