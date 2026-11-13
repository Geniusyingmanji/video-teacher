"""Anonymous per-video human calibration packets for the current criterion schema."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import imageio_ffmpeg

from .common import ROOT, digest, public_case, read_jsonl, write_json, write_jsonl
from .provenance import evaluation_inventory, file_hash, freeze_run
from .rubric import DIMENSIONS, VERSION
from .strict_anchors import OPTIONAL_CRITERIA


def rating_task(case, item_id, rater_id, study_id, source_image=None):
    """No model name, source path, automated score or control label is exported."""
    return {'assignment_id':study_id+'-'+rater_id+'-'+item_id,'item_id':item_id,'rater_id':rater_id,
            'video':'media/'+item_id+'.mp4','source_image':source_image,
            'discipline':case.get('discipline_canonical',case.get('discipline')),
            'task_type':case.get('task_type'),'audience':case.get('pedagogical_target_audience'),
            'target_duration_s':case.get('target_duration_s'),'prompt_text':case['prompt_text'],
            'reference':{k:case.get(k) for k in ('expected_concepts','expected_visual_elements',
                                               'expected_narrative_order','discipline_specific_rubric')},
            'rubric_version':VERSION}


def validate_rating(row, assignment):
    if not isinstance(row,dict):raise ValueError('response must be an object')
    for key in ('assignment_id','item_id','rater_id'):
        if row.get(key)!=assignment[key]:raise ValueError(f'{key} mismatch')
    if row.get('rubric_version')!=assignment['rubric_version']:raise ValueError('rubric version mismatch')
    dimensions=row.get('dimensions')
    if not isinstance(dimensions,dict) or set(dimensions)!=set(DIMENSIONS):raise ValueError('incorrect dimensions')
    for name,dim in DIMENSIONS.items():
        criteria=dimensions[name]
        if not isinstance(criteria,dict) or set(criteria)!=set(dim['criteria']):raise ValueError(f'{name}: incorrect criteria')
        for key,item in criteria.items():
            if not isinstance(item,dict):raise ValueError(f'{name}.{key}: invalid criterion')
            score=item.get('score')
            if score is not None and (type(score) not in (int,float) or not 1<=score<=5 or score!=round(score)):raise ValueError('score must be an integer level 1..5 or null')
            if item.get('status')=='not_applicable' and (name+'.'+key not in OPTIONAL_CRITERIA or score is not None):
                raise ValueError('not_applicable is limited to explicitly optional public requirements')
            if score is None or score<=2 or score==5:
                if not isinstance(item.get('note'),str) or not item['note'].strip():raise ValueError('low/unverified/high score requires a concrete note')
    return row


def validated_responses(assignments, responses):
    index={r['assignment_id']:r for r in assignments}
    if len(index)!=len(assignments):raise ValueError('duplicate assignment id')
    accepted=[];rejected=[];seen=set()
    for i,row in enumerate(responses):
        try:
            if row.get('assignment_id') not in index:raise ValueError('unknown assignment')
            if row['assignment_id'] in seen:raise ValueError('duplicate response')
            validate_rating(row,index[row['assignment_id']])
            seen.add(row['assignment_id']);accepted.append(row)
        except (ValueError,AttributeError) as exc:
            rejected.append({'row_index':i,'reason':str(exc)})
    return accepted,rejected,sorted(set(index)-seen)


def summarize(assignments, responses):
    from .human_statistics import krippendorff_alpha_ordinal, json_number
    accepted,rejected,unrated=validated_responses(assignments,responses)
    output={}
    for name,dim in DIMENSIONS.items():
        output[name]={}
        for criterion in dim['criteria']:
            units=defaultdict(list)
            for row in accepted:
                units[row['item_id']].append(row['dimensions'][name][criterion]['score'])
            values=[s for scores in units.values() for s in scores if s is not None]
            output[name][criterion]={'n_ratings':len(values),'n_videos':len(units),
                'n_videos_with_2_ratings':sum(sum(v is not None for v in scores)>=2 for scores in units.values()),
                'mean':sum(values)/len(values) if values else None,
                'ordinal_alpha':json_number(krippendorff_alpha_ordinal(list(units.values()))) if units else None}
    return {'status':'no_human_ratings' if not accepted else 'human_ratings_available',
            'n_assignments':len(assignments),'n_accepted':len(accepted),'rejected':rejected,
            'n_raters':len({r['rater_id'] for r in accepted}),
            'unrated_assignments':unrated,'criteria':output,
            'inference':'reliability only; no judge-human validity claim without paired score analysis'}


def export(run_path, data_path, out, n_raters=3, seed=20261111):
    if out.exists():raise ValueError('choose a fresh human-study directory')
    if n_raters<2:raise ValueError('at least two raters required for reliability')
    cases={r['id']:r for r in read_jsonl(data_path)}
    run=json.loads((run_path/'manifest.json').read_text())
    jobs=evaluation_inventory(run,cases)
    case_hashes={id_:digest(cases[id_]) for id_ in sorted({id_ for id_,a in jobs})}
    freeze_run(out,{'entrypoint':'human_export','source_manifest_hash':digest(run),'seed':seed,
                    'case_hashes':case_hashes,'n_raters':n_raters,'rubric_version':VERSION})
    study_id='study-'+digest({'manifest':digest(run),'seed':seed,'case_hashes':case_hashes,'rubric':VERSION})[:10]
    coordinator=out/'coordinator';coordinator.mkdir()
    media=coordinator/'anonymous_media';media.mkdir()
    mapping=[];source_files={}
    for id_,artifact in jobs:
        item_id='v'+digest({'seed':seed,'case':id_,'mode':artifact['mode'],'video':artifact['sha256']})[:12]
        video=media/(item_id+'.mp4')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',artifact['video_path'],
                        '-map','0:v:0','-map','0:a?','-map_metadata','-1','-c','copy',str(video)],check=True)
        source_image=None
        attachments=public_case(cases[id_]).get('public_attachments',[])
        if attachments:
            original=attachments[0].get('local_path')
            if not original:raise ValueError('required source image missing from human packet')
            source_image='media/'+item_id+Path(original).suffix.lower()
            shutil.copyfile(original,media/Path(source_image).name)
            source_files[item_id]=source_image
        mapping.append({'item_id':item_id,'case_id':id_,'mode':artifact['mode'],
                        'original_video':artifact['video_path'],'original_sha256':artifact['sha256'],
                        'delivered_sha256':file_hash(video)})
    write_json(coordinator/'mapping.json',mapping)
    assignments=[]
    for i in range(1,n_raters+1):
        rater_id=f'rater_{i:02d}'
        directory=out/'raters'/rater_id;directory.mkdir(parents=True)
        shutil.copytree(media,directory/'media')
        order=list(mapping);random.Random(seed+i).shuffle(order)
        tasks=[rating_task(cases[row['case_id']],row['item_id'],rater_id,study_id,source_files.get(row['item_id'])) for row in order]
        assignments.extend(tasks)
        write_json(directory/'tasks.json',tasks)
        (directory/'index.html').write_text(render_form(tasks,study_id,rater_id),encoding='utf-8')
    write_jsonl(coordinator/'assignments.jsonl',assignments)
    write_json(out/'study_manifest.json',{'study_id':study_id,'n_videos':len(jobs),'n_raters':n_raters,
              'n_assignments':len(assignments),'rubric_version':VERSION,'human_responses_collected':0,
              'blinding':'Only share an individual raters/<id> directory. Coordinator mapping and model scores are excluded; visual styles cannot be hidden.',
              'source_selection':'all completed media in the specified manifest; no filtering by automated scores'})
    (out/'README.md').write_text('# 人工校准包\n\n每位评分者只接收自己的 `raters/rater_XX/` 文件夹，打开 `index.html`。不要分发 `coordinator/`，不要提供自动评分。\n\n评分前观看完整视频和实际音轨，核对原题、受众及原图。参考可能有误，可在备注中指出。缺乏证据选择未验证；实际缺少要求内容应低分。保存后下载 JSONL，交由协调者汇总。本工具不会上传或发送任何数据。\n\n目前尚无真实人工评分，不能据此声称完成校准。\n',encoding='utf-8')
    return {'videos':len(jobs),'assignments':len(assignments),'path':str(out)}


def render_form(tasks, study_id, rater_id):
    payload=json.dumps({'tasks':tasks,'rubric':DIMENSIONS,'study':study_id,'rater':rater_id},ensure_ascii=False).replace('</','<\\/')
    return FORM.replace('__PAYLOAD__',payload)


FORM='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>教学视频人工评分</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:0 20px;color:#14283e;background:#f6f8fb}video{width:100%;max-height:520px;background:#111}section,details{background:white;border:1px solid #dce4ed;border-radius:8px;padding:16px;margin:12px 0}pre{white-space:pre-wrap;font:inherit}label{display:block;margin:10px 0}select,button,textarea{font:inherit;padding:8px}textarea{width:95%;min-height:48px}button{cursor:pointer;margin:5px}small{color:#526b80}.row{border-top:1px solid #e5e9ef;padding:12px 0}#status{font-weight:600}img{max-width:100%;max-height:450px}</style>
<h1>教学视频人工评分</h1><p>请观看完整视频并听音轨，按每项定义独立评分。每项仅选整数 1–5：1 严重失败，2 严重缺陷，3 基本可用但有局限，4 较强（仍有轻微问题，或未达到本项明确的优秀条件），5 满足本项优秀条件且有具体证据。实际遗漏应低分，无法观察才选“未验证”。</p>
<p id="status"></p><button id="prev">上一条</button><button id="save">保存并下一条</button><button id="download">下载已保存评分</button>
<h2 id="item"></h2><video id="video" controls preload="metadata"></video><section><p id="audience"></p><pre id="prompt"></pre><img id="source" hidden></section>
<details><summary>独立参考（如有错误请在备注指出）</summary><pre id="reference"></pre></details><form id="ratings"></form><section><label>整体备注／时间点／参考问题<textarea id="notes"></textarea></label></section>
<script>const P=__PAYLOAD__;let index=0;const storageKey=P.study+':'+P.rater;let saved={};try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch(e){};
const el=id=>document.getElementById(id);function show(){const t=P.tasks[index];el('item').textContent='视频 '+(index+1)+' / '+P.tasks.length+' · '+t.item_id;el('status').textContent='已保存 '+Object.keys(saved).length+' / '+P.tasks.length;el('video').src=t.video;el('audience').textContent='受众：'+t.audience+'；目标时长：'+t.target_duration_s+' 秒';el('prompt').textContent=t.prompt_text;el('reference').textContent=JSON.stringify(t.reference,null,2);el('source').hidden=!t.source_image;if(t.source_image)el('source').src=t.source_image;el('ratings').replaceChildren();const old=saved[t.assignment_id];for(const [dim,def] of Object.entries(P.rubric)){const box=document.createElement('section');const title=document.createElement('h3');title.textContent=def.name;box.append(title);for(const [key,text] of Object.entries(def.criteria)){const row=document.createElement('div');row.className='row';const label=document.createElement('label');label.textContent=text;const select=document.createElement('select');select.id=dim+'__'+key;for(const [value,caption] of [['','请选择'],['1','1 严重失败'],['2','2 严重缺陷'],['3','3 基本可用'],['4','4 较强'],['5','5 出色且有证据'],['U','未验证'],...(def.optional_criteria?.includes(key)?[['NA','不适用（题目未要求）']]:[])]){const option=document.createElement('option');option.value=value;option.textContent=caption;select.append(option)}const note=document.createElement('textarea');note.id=select.id+'__note';note.placeholder='低分、未验证或 5 分时需具体依据，可注明对象、关系和时间点';if(old){const r=old.dimensions[dim][key];select.value=r.status==='not_applicable'?'NA':r.score===null?'U':String(r.score);note.value=r.note||''}row.append(label);const guide=def.criterion_details?.[key];if(guide){const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='查看 1–5 分标准、所需证据与评分边界';details.append(summary);for(const [level,description] of Object.entries(guide.levels)){const line=document.createElement('p');line.textContent=level+'：'+description;details.append(line)}for(const [heading,field] of [['所需证据','evidence'],['评分边界','boundary']]){const line=document.createElement('p');line.textContent=heading+'：'+guide[field];details.append(line)}row.append(details)}row.append(select,note);box.append(row)}el('ratings').append(box)}el('notes').value=old?.notes||''}
function save(){const t=P.tasks[index],dimensions={};for(const [dim,def] of Object.entries(P.rubric)){dimensions[dim]={};for(const key of Object.keys(def.criteria)){const id=dim+'__'+key,value=el(id).value,note=el(id+'__note').value.trim();if(!value){alert('还有未评分项目');el(id).focus();return false}const score=(value==='U'||value==='NA')?null:Number(value);if((score===null||score<=2||score==5)&&!note){alert('低分、未验证、不适用及高分项目需要具体说明');el(id+'__note').focus();return false}dimensions[dim][key]={score,note,status:value==='NA'?'not_applicable':value==='U'?'unverified':'observed'}}}saved[t.assignment_id]={assignment_id:t.assignment_id,item_id:t.item_id,rater_id:t.rater_id,rubric_version:t.rubric_version,dimensions,notes:el('notes').value,saved_at:new Date().toISOString()};localStorage.setItem(storageKey,JSON.stringify(saved));return true}
el('save').onclick=()=>{if(save()){index=Math.min(index+1,P.tasks.length-1);show()}};el('prev').onclick=()=>{if(index>0){index--;show()}};el('download').onclick=()=>{const text=Object.values(saved).map(x=>JSON.stringify(x)).join('\\n');const blob=new Blob([text+(text?'\\n':'')],{type:'application/x-ndjson'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=P.study+'-'+P.rater+'.jsonl';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};show();</script></html>'''


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    exp=sub.add_parser('export');exp.add_argument('--run',type=Path,required=True);exp.add_argument('--out',type=Path,required=True)
    exp.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl');exp.add_argument('--raters',type=int,default=3);exp.add_argument('--seed',type=int,default=20261111)
    ana=sub.add_parser('analyse');ana.add_argument('--study',type=Path,required=True);ana.add_argument('--responses',nargs='*',type=Path,default=[]);ana.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.command=='export':print(export(args.run,args.data,args.out,args.raters,args.seed))
    else:
        assignments=read_jsonl(args.study/'coordinator/assignments.jsonl')
        rows=[r for path in args.responses for r in read_jsonl(path)]
        result=summarize(assignments,rows);write_json(args.out,result);print({'status':result['status'],'accepted':result['n_accepted'],'rejected':len(result['rejected'])})


if __name__=='__main__':main()
