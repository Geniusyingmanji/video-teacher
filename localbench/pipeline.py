"""Small-batch complete lessons from public tasks, with paired slide/code outputs."""
from __future__ import annotations

import argparse
import base64
import mimetypes
import shutil
import concurrent.futures
import hashlib
import json
import math
import re
import subprocess
import time
import wave
from pathlib import Path

import imageio_ffmpeg

from .client import MatrixClient
from .common import ROOT, digest, parse_json, public_case, read_jsonl, write_json
from .layout_geometry import blocking_issues
from .scene import FPS, HEIGHT, PLAN_SYSTEM, VERSION, WIDTH, inspect_layout, render_frame, validate_plan
from .state import assign_state, derive_state
from .timing import normalize_plan_timing, speech_frames
from .source_scene import SYSTEM as SOURCE_SYSTEM, bind_source
from .provenance import file_hash, freeze_run


def run_command(args):
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(f'{Path(args[0]).name} failed: {completed.stderr[-1400:]}')
    return completed


def spoken_text(scene):
    from .math_speech import verbalize_math
    text=verbalize_math(scene['narration'])
    state=scene.get('state_visual',{}).get('state',{})
    if state.get('kind')=='punnett':
        letter=state['parents'][0][0].upper()
        for genotype in sorted({*state['parents'],*state['outcomes']},key=len,reverse=True):
            words=', '.join(('capital '+x if x.isupper() else 'lowercase '+x) for x in genotype)
            text=re.sub(r"(?<![A-Za-z])['\"]?"+re.escape(genotype)+r"['\"]?(?![A-Za-z])",words,text)
        text=text.replace("'"+letter+"'",'capital '+letter).replace("'"+letter.lower()+"'",'lowercase '+letter.lower())
    return text


def synthesize(plan, directory, tts=None):
    from .tts import resolve_tts, synthesize_speech
    tts = resolve_tts(tts)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = plan['scenes']
    authored = [s.get('authored_duration_s', s['duration_s']) for s in scenes]
    target = sum(s['duration_s'] for s in scenes)
    rate = 155
    measurement_history=[]
    history_path=directory/'timing_attempts.json'
    if history_path.exists():measurement_history=json.loads(history_path.read_text())
    for attempt in range(5):
        measurements = []
        for i, scene in enumerate(scenes):
            scene_dir = directory/f'scene_{i:02d}'
            scene_dir.mkdir(parents=True, exist_ok=True)
            text_path, aiff, speech = scene_dir/'narration.txt', scene_dir/'speech.aiff', scene_dir/'speech.wav'
            text = spoken_text(scene)
            key_input = {'text': text, 'tts': tts, 'rate': rate, 'sample_rate': 24000}
            if scene.get('spoken_units'):
                from .spoken_units import validate as validate_units
                key_input['spoken_units'] = validate_units(scene)
            key = digest(key_input)
            receipt = scene_dir/'speech_receipt.json'
            cached = json.loads(receipt.read_text()) if receipt.exists() else {}
            text_path.write_text(text, encoding='utf-8')
            if not speech.exists() or cached.get('input_hash') != key or cached.get('sha256') != hashlib.sha256(speech.read_bytes()).hexdigest():
                unit_timing = None
                if scene.get('spoken_units'):
                    from .spoken_units import synthesize as synthesize_units
                    unit_timing = synthesize_units(scene,scene_dir,rate,tts,speech)
                else:
                    synthesize_speech(text_path, speech, rate, tts)
                cached = {'input_hash':key,'sha256':hashlib.sha256(speech.read_bytes()).hexdigest()}
                if unit_timing is not None:cached['spoken_unit_timing']=unit_timing
                write_json(receipt, cached)
            if scene.get('spoken_units'):
                scene['spoken_unit_timing'] = cached.get('spoken_unit_timing')
            with wave.open(str(speech)) as f:
                measurements.append(f.getnframes()/f.getframerate())
        measurement_history.append({'attempt':len(measurement_history),'rate':rate,'target_s':target,
            'spoken_seconds':measurements,'text_hashes':[digest(spoken_text(s)) for s in scenes]})
        write_json(history_path,measurement_history)
        try:
            counts = speech_frames(plan, measurements)
            break
        except ValueError:
            if rate == 195 or attempt == 4:
                index = max(range(len(scenes)), key=lambda i: measurements[i])
                available = min(23.5, max(2, measurements[index] - max(0, sum(measurements) + len(scenes)*.3 - target)))
                error = ValueError(f'scene {index}: narration needs shortening after measured whole-video scheduling at {rate} wpm')
                error.max_words = max(6, math.floor(len(scenes[index]['narration'].split()) * available/measurements[index] * .85))
                write_json(directory/'timing_failure.json', {'rate':rate, 'spoken_seconds':measurements,
                           'target_s':target, 'scene_to_shorten':index, 'max_words':error.max_words})
                raise error
            ratio = max((sum(measurements)+len(scenes)*.3)/target, max(measurements)/23.5)
            rate = min(195, max(rate+5, math.ceil(rate*ratio)+3))
    audio_records = []
    previous = 0
    for i, (scene, frames, spoken) in enumerate(zip(scenes, counts, measurements)):
        duration = frames/FPS
        scene['duration_s'] = duration
        if scene.get('spoken_units'):
            from .spoken_units import validate_timing
            validate_timing(scene)
            if any(p.get('type')=='piano_walk' for p in scene.get('primitives',[])):
                from .keyboard_bridge import bind_timing
                bind_timing(scene)
        scene_dir = directory/f'scene_{i:02d}'
        speech, padded = scene_dir/'speech.wav', scene_dir/'slot.wav'
        run_command([ffmpeg,'-y','-loglevel','error','-i',str(speech),'-af',f'apad,atrim=0:{duration}',str(padded)])
        audio_records.append({'scene':i,'start_s':previous/FPS,'end_s':(previous+frames)/FPS,
                              'authored_duration_s':authored[i], 'compiled_duration_s':duration,
                              'spoken_seconds':spoken,'words_per_minute':rate,
                              'tts':tts,
                              'silence_tail_s':duration-spoken,'path':str(padded.resolve())})
        previous += frames
    plan['timing_compilation'] = {'version':'measured-speech-v1','target_frames':previous,
                                 'common_speech_rate':rate,'speech_seconds':sum(measurements),
                                 'silence_seconds':target-sum(measurements),'minimum_tail_s':.25,
                                 'speech_fraction':sum(measurements)/target,
                                 'max_scene_silence_tail_s':max(r['silence_tail_s'] for r in audio_records),
                                 'review_long_holds':[{'scene':r['scene'],'tail_s':r['silence_tail_s']}
                                                     for r in audio_records if r['silence_tail_s']>4],
                                 'review_note':'Long tails may support reading or inspection; inspect actual media before calling them filler. No automatic score penalty.'}
    concat = directory/'audio_concat.txt'
    concat.write_text(''.join("file '"+r['path'].replace("'", "'\\''")+"'\n" for r in audio_records))
    final = directory/'narration.wav'
    run_command([ffmpeg,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c:a','pcm_s16le',str(final)])
    write_json(directory/'audio_generation.json',audio_records)
    return final, audio_records


def resolve_source_plan(root, case_id):
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f'plans-from directory does not exist: {root}')
    directories = [root/case_id]
    manifest = root/'manifest.json'
    if manifest.exists():
        data = json.loads(manifest.read_text())
        for case in data.get('cases', []):
            if case['id'] == case_id:
                directories.extend(Path(a['video_path']).parent for a in case.get('artifacts', []))
    for directory in directories:
        path = directory/'plan.json'
        if path.is_file():
            return path
        attempts = sorted(directory.glob('plan_attempt_*.json'))
        if attempts:
            return attempts[-1]
    raise ValueError(f'no previous plan available for {case_id} in {root}')


def encode(plan, directory, audio_path, *, mode, copy_audio=False):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    width,height = plan.get('canvas_size',(WIDTH,HEIGHT))
    raw_video = directory/f'{mode}_silent.mp4'
    output = directory/f'{mode}.mp4'
    log_path = directory/f'{mode}_render.log'
    started = time.monotonic()
    command = [ffmpeg,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo',
               '-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(FPS),'-i','-',
               '-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','23',
               '-pix_fmt','yuv420p',str(raw_video)]
    frames = 0
    boundary = 0
    with log_path.open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        try:
            for i, scene in enumerate(plan['scenes']):
                boundary += scene['duration_s']
                end = round(boundary*FPS)
                count = end-frames
                for j in range(count):
                    frame,_ = render_frame(scene,j/max(1,count-1),index=i,total=len(plan['scenes']),mode=mode)
                    process.stdin.write(frame.tobytes())
                    frames += 1
            process.stdin.close()
            if process.wait(timeout=120):
                raise RuntimeError(log_path.read_text()[-1500:])
        except BaseException:
            process.kill()
            process.wait()
            raise
    audio_options=['-c:a','copy'] if copy_audio else ['-c:a','aac','-b:a','96k']
    run_command([ffmpeg,'-y','-loglevel','error','-i',str(raw_video),'-i',str(audio_path),
                 '-map','0:v:0','-map','1:a:0','-c:v','copy',*audio_options,
                 '-movflags','+faststart',str(output)])
    # Verify final encoded data by actually decoding every frame.
    reader = imageio_ffmpeg.read_frames(str(output),pix_fmt='rgb24')
    metadata = next(reader)
    actual_frames = sum(1 for _ in reader)
    if actual_frames != frames:
        raise ValueError(f'encoded frame mismatch {actual_frames} != {frames}')
    if abs(metadata['duration']-frames/FPS)>.15:
        raise ValueError('encoded duration mismatch')
    raw_video.unlink()
    from .scene import renderer_fingerprint
    return {'mode':mode,'video_path':str(output.resolve()),'plan_sha256':digest(plan),
            'scene_version':VERSION,'renderer_sha256':renderer_fingerprint(),'duration_s':metadata['duration'],
            'fps':metadata['fps'],'frame_count':actual_frames,'size':metadata['size'],
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'render_seconds':round(time.monotonic()-started,3),'complete':True}


def generate_one(case, out, client, modes, use_state=False, plans_from=None, review_content=False, source_regions=False, plain_json_plans=False, source_graphs=False, tts=None, source_overlays=False, layout_policy='repair', spatial_graphs=False, spatial_contracts=False):
    from .scientific_audit import validate_public
    validate_public(public_case(case))
    if layout_policy not in {'repair','report','repair_then_report'}:raise ValueError('invalid layout policy')
    if spatial_graphs and spatial_contracts:raise ValueError('choose optional spatial primitives or task-first spatial contracts, not both')
    last_renderable=None
    directory = out/case['id']
    directory.mkdir(parents=True, exist_ok=True)
    public = public_case(case)
    state=derive_state(public) if use_state else None
    if use_state and state is None:
        print(case['id'],'no executable state adapter; using general primitives',flush=True)
    from .scientific_audit import audit_case
    write_json(directory/'public_scientific_audit.json',audit_case(public,public_only=True))
    write_json(directory/'public_input.json', public)
    status = {'id':case['id'],'run_directory':str(directory.resolve()),'public_input_hash':digest(public),'scene_version':VERSION,
              'method':'declarative_code_scene_pilot','is_code2video_reproduction':False,
              'private_reference_used_for_generation':False,'attempts':[],'artifacts':[]}
    attachment = None
    if public.get('public_attachments'):
        candidate = public['public_attachments'][0]
        first_line=public['prompt_text'].split('\n')[0].lower()
        supported=source_overlays or (('shortest path' in first_line and 'red' in first_line) if source_graphs else ('shade' in first_line) if source_regions else ('replace' in first_line))
        if not candidate.get('local_path') or not supported:
            status.update(status='unsupported_input_profile',
                          error='Requested source backend does not support this public task: select text replacement, source-region shading, or shortest-path recoloring explicitly.')
            write_json(directory/'manifest.json',status)
            return status
        path = Path(candidate['local_path'])
        frozen = directory/('source_input'+path.suffix)
        shutil.copyfile(path,frozen)
        attachment = {**candidate,'local_path':str(frozen.resolve())}
        status['source_image']={'path':str(frozen.resolve()),'sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
                                'role':'public_source_only'}
        status['method']='source_preserving_code_overlay_pilot'
    state_prompt=''
    if state:
        write_json(directory/'derived_state.json',state)
        state_prompt='''\nA trusted code adapter derived the following state from the PUBLIC task.
Create EXACTLY SIX scenes following the listed phases in order. Narration and captions must
describe these phases and facts faithfully. Diagrams will be drawn by the adapter; provide only
one harmless placeholder text primitive per scene (it will not be shown). You still author
the title, narration, caption, and slide_text. About 2.0 spoken words/sec; total duration exact.
Do not invent states, comparisons or measured values inconsistent with the adapter.
Return no arithmetic_checks: actual numeric states are computed in code.\n'''+json.dumps(state,ensure_ascii=False)
    user_content = json.dumps(public,ensure_ascii=False)
    if attachment:
        path=Path(attachment['local_path'])
        user_content=[{'type':'text','text':user_content},
                      {'type':'image_url','image_url':{'url':'data:'+(mimetypes.guess_type(str(path))[0] or 'image/png')+';base64,'+base64.b64encode(path.read_bytes()).decode()}}]
    region_spec=None;computed_region=None;graph_spec=None;computed_graph=None
    region_system=None
    if source_regions:
        if not attachment:
            status.update(status='unsupported_input_profile',error='source-region mode requires a public source image')
            write_json(directory/'manifest.json',status);return status
        from PIL import Image
        from .source_region import EXTRACT_SYSTEM,PLAN_SYSTEM as REGION_SYSTEM,check_curve_fit,region_facts,refine_mapping
        extraction=[{'role':'system','content':EXTRACT_SYSTEM},{'role':'user','content':user_content}]
        for attempt in range(3):
            try:
                if plans_from and attempt==0:
                    saved=json.loads(resolve_source_plan(plans_from,case['id']).read_text())
                    region_spec=next(e['spec'] for e in saved['source_edits'] if e['kind']=='fill_between')
                else:
                    region_spec=client.chat(extraction,purpose='source_region_extract:'+case['id'],max_tokens=1300)
                write_json(directory/f'region_spec_{attempt}.json',region_spec)
                source_image=Image.open(attachment['local_path'])
                fit=check_curve_fit(source_image,region_spec)
                write_json(directory/f'region_fit_{attempt}.json',fit)
                if not fit['passed']:
                    region_spec,calibration=refine_mapping(source_image,region_spec)
                    write_json(directory/f'region_calibration_{attempt}.json',calibration)
                    write_json(directory/f'region_spec_refined_{attempt}.json',region_spec)
                computed_region=region_facts(region_spec,source_image.size)
                write_json(directory/'region_computation.json',computed_region)
                break
            except Exception as exc:
                status['attempts'].append({'stage':'region_extraction','attempt':attempt,'error':str(exc)[:1800]})
                if attempt==2:
                    status.update(status='source_region_extraction_failed',error=str(exc)[:1800])
                    write_json(directory/'manifest.json',status);return status
                extraction=extraction[:2]+[{'role':'assistant','content':json.dumps(region_spec)},
                    {'role':'user','content':'Return the corrected complete extraction object. Recheck original ticks and curves. '+str(exc)[:1800]}]
        planning_facts={k:v for k,v in computed_region.items() if k not in ('sampled_solution_intervals','x_resolution')}
        region_system=REGION_SYSTEM+'\nCODE-COMPUTED FACTS:\n'+json.dumps(planning_facts,ensure_ascii=False)
        status['method']='source_preserving_computed_region_pilot'
    if source_graphs:
        if not attachment:
            status.update(status='unsupported_input_profile',error='source-graph mode requires a public source image')
            write_json(directory/'manifest.json',status);return status
        from PIL import Image
        from .source_graph import EXTRACT_SYSTEM,PLAN_SYSTEM as GRAPH_SYSTEM,prepare_graph
        extraction=[{'role':'system','content':EXTRACT_SYSTEM},{'role':'user','content':user_content}]
        for attempt in range(3):
            try:
                if plans_from and attempt==0:
                    saved=json.loads(resolve_source_plan(plans_from,case['id']).read_text())
                    graph_spec=next(e['spec'] for e in saved['source_edits'] if e['kind']=='highlight_path')
                else:
                    graph_spec=client.chat(extraction,purpose='source_graph_extract:'+case['id'],max_tokens=2500)
                write_json(directory/f'graph_spec_{attempt}.json',graph_spec)
                graph_spec,computed_graph,geometry=prepare_graph(Image.open(attachment['local_path']),graph_spec)
                write_json(directory/f'graph_geometry_{attempt}.json',geometry)
                write_json(directory/'graph_spec_refined.json',graph_spec)
                write_json(directory/'graph_computation.json',computed_graph)
                break
            except Exception as exc:
                status['attempts'].append({'stage':'graph_extraction','attempt':attempt,'error':str(exc)[:1800]})
                if attempt==2:
                    status.update(status='source_graph_extraction_failed',error=str(exc)[:1800])
                    write_json(directory/'manifest.json',status);return status
                extraction=extraction[:2]+[{'role':'assistant','content':json.dumps(graph_spec)},
                    {'role':'user','content':'Return the corrected complete extraction object. Recheck every node border and edge against original pixels. '+str(exc)[:1800]}]
        region_system=GRAPH_SYSTEM+'\nCODE-COMPUTED FACTS:\n'+json.dumps(computed_graph,ensure_ascii=False)
        status['method']='source_preserving_computed_graph_pilot'
    from .source_scene import OVERLAY_SYSTEM
    from .spatial_plan import SYSTEM as SPATIAL_SYSTEM, compile_plan as compile_spatial_plan
    from .spatial_contract import propose as propose_spatial_contract, planner_prompt, bind_plan as bind_spatial_contract
    spatial_contract = None
    if spatial_contracts:
        if state is None and not attachment:
            try:
                spatial_contract = propose_spatial_contract(client, public, directory/'spatial_contract')
                status['spatial_contract'] = {k: spatial_contract.get(k) for k in ('version','status','contract_id','semantic_binding_status')}
                status['spatial_contract']['path'] = str((directory/'spatial_contract/contract.json').resolve())
            except Exception as exc:
                status['spatial_contract'] = {'status':'proposal_failed','error':str(exc)[:1600]}
                write_json(directory/'spatial_contract/failure.json',status['spatial_contract'])
        else:
            status['spatial_contract'] = {'status':'protected_backend_not_proposed'}
    spatial_prompt = SPATIAL_SYSTEM if spatial_graphs and state is None and not attachment else ''
    if spatial_contract is not None:
        spatial_prompt = planner_prompt(spatial_contract)
    messages = [{'role':'system','content':region_system or ((OVERLAY_SYSTEM if source_overlays else SOURCE_SYSTEM) if attachment else PLAN_SYSTEM+spatial_prompt+state_prompt)},
                {'role':'user','content':user_content}]
    plan = None
    for attempt in range(3):
        try:
            if plans_from and attempt==0:
                source=resolve_source_plan(plans_from,case['id'])
                plan=json.loads(source.read_text())
                status['source_plan']={'path':str(source.resolve()),'sha256':digest(plan)}
            else:
                response = client.chat(messages,purpose=f'plan:{case["id"]}:{attempt}',max_tokens=10000,json_mode=not plain_json_plans)
                if plain_json_plans:
                    (directory/f'plan_response_{attempt}.txt').write_text(response)
                    plan=parse_json(response)
                else:plan=response
            write_json(directory/f'plan_raw_{attempt}.json',plan)
            if not isinstance(plan,dict):raise ValueError('plan must be a JSON object')
            # Model text cannot choose local paths or inject a supposedly trusted state.
            plan.pop('canvas_size',None)
            for scene in plan.get('scenes',[]):
                scene.pop('state_visual',None);scene.pop('source_visual',None)
                scene.pop('teaching_cues',None)
            plan=assign_state(plan,state)
            if attachment:
                if source_graphs:
                    from .source_graph import bind_graph
                    plan=bind_graph(plan,attachment,graph_spec)
                elif source_regions:
                    from .source_region import bind_region
                    plan=bind_region(plan,attachment,region_spec)
                else:plan=bind_source(plan,attachment,allow_overlays=source_overlays)
            plan=normalize_plan_timing(plan,case['target_duration_s'])
            if spatial_contract is not None:
                plan,binding=bind_spatial_contract(plan,spatial_contract)
                write_json(directory/f'spatial_contract_binding_{attempt}.json',binding)
            if spatial_graphs:
                plan,construction=compile_spatial_plan(plan,public)
                write_json(directory/f'spatial_constructions_{attempt}.json',construction)
            write_json(directory/f'plan_attempt_{attempt}.json',plan)
            validate_plan(plan,case)
            if review_content:
                from .content_review import review_and_repair
                plan=review_and_repair(client,case,plan,directory/f'content_attempt_{attempt}')
                if spatial_contract is not None:
                    plan,binding=bind_spatial_contract(plan,spatial_contract,allow_compiled=True)
                    write_json(directory/f'spatial_contract_content_binding_{attempt}.json',binding)
                if spatial_graphs:
                    plan,construction=compile_spatial_plan(plan,public)
                    write_json(directory/f'spatial_content_constructions_{attempt}.json',construction)
                validate_plan(plan,case)
            issues = inspect_layout(plan,include_warnings=True)
            status['attempts'].append({'attempt':attempt,'layout_issues':issues,'schema_valid':True,'layout_policy':layout_policy})
            import copy
            last_renderable=copy.deepcopy(plan)
            if blocking_issues(issues) and layout_policy!='report' and not (layout_policy=='repair_then_report' and attempt==2):
                raise ValueError('Fix these visible layout defects: '+json.dumps(blocking_issues(issues)[:12],ensure_ascii=False))
            break
        except Exception as exc:
            status['attempts'].append({'attempt':attempt,'error':str(exc)[:1800]})
            if attempt == 2:
                if last_renderable is not None and layout_policy=='repair_then_report':
                    plan=last_renderable
                    status['layout_repair_exhausted']=True
                    break
                status.update(status='planning_failed',error=str(exc)[:1800])
                write_json(directory/'manifest.json',status)
                print(case['id'],'planning_failed',str(exc)[:180],flush=True)
                return status
            messages = [messages[0],messages[1]] + ([{'role':'assistant','content':json.dumps(plan,ensure_ascii=False)}] if plan is not None else []) + [
                {'role':'user','content':f'Repair attempt {attempt+1}: return the entire corrected JSON OBJECT plan with case_id and scenes, preserving the public task and target duration. Do not return an empty array. '+str(exc)[:2200]}]
    write_json(directory/'plan.json',plan)
    try:
        max_audio_repairs=2*len(plan['scenes'])
        for audio_attempt in range(max_audio_repairs+1):
            try:
                audio,audio_records=synthesize(plan,directory,tts=tts)
                break
            except ValueError as exc:
                match=re.search(r'scene (\d+): (?:narration needs|speech exceeds)',str(exc))
                if not match or audio_attempt==max_audio_repairs:raise
                index=int(match.group(1));scene=plan['scenes'][index]
                before=scene['narration'];limit=getattr(exc,'max_words',max(6,int(scene['duration_s']*1.6)))
                repaired=client.chat([{'role':'system','content':'Rewrite only English spoken narration, preserving the task facts and teaching purpose. Return JSON {narration:"..."}. Do not change givens or add new claims. Spell numbers as spoken words, never digits. Count the spoken words. For a short recap, summarize the ordering/result without repeating every date/value already explained. Letter case must be spoken explicitly when meaningful.'},
                    {'role':'user','content':json.dumps({'public_task':public,'state_facts':state.get('facts') if state else computed_graph or computed_region,
                         'scene_title':scene['title'],'caption':scene['caption'],'original_narration':before,
                         'earlier_coverage':[{'title':s['title'],'narration':s['narration']} for s in plan['scenes'][:index]],
                         'max_words':limit,'problem':'Measured narration does not fit the whole-video schedule. Shorten this scene to the word limit.'},ensure_ascii=False)}],
                    purpose=f'narration_repair:{case["id"]}:{index}',max_tokens=500)
                if not isinstance(repaired,dict) or not isinstance(repaired.get('narration'),str) or not 5<=len(repaired['narration'].split())<=90:
                    raise ValueError('narration repair did not return a valid bounded English narration')
                if len(repaired['narration'].split())>limit or len(repaired['narration'].split())>=len(before.split()):
                    raise ValueError('narration repair failed the measured word reduction bound')
                if repaired['narration']==before:
                    raise ValueError('narration repair made no change to overflowing speech')
                scene['narration']=repaired['narration']
                write_json(directory/f'audio_repair_{audio_attempt}.json',{'scene':index,'before':before,'after':scene['narration'],'reason':str(exc)})
                if review_content:
                    plan=review_and_repair(client,case,plan,directory/f'content_audio_repair_{audio_attempt}')
                    if spatial_contract is not None:
                        plan,binding=bind_spatial_contract(plan,spatial_contract,allow_compiled=True)
                        write_json(directory/f'spatial_contract_audio_binding_{audio_attempt}.json',binding)
                validate_plan(plan,case)
                issues=inspect_layout(plan)
                if issues and layout_policy=='repair':raise ValueError('layout failed after narration/content repair: '+json.dumps(issues[:6]))
                write_json(directory/'plan.json',plan)
        validate_plan(plan,case)
        write_json(directory/'plan.json',plan)
        from .chart import plan_chart_receipts
        write_json(directory/'chart_computation.json',plan_chart_receipts(plan))
        from .linear_algebra import receipts as algebra_receipts
        write_json(directory/'linear_algebra_computation.json',algebra_receipts(plan))
        from .flow import plan_flow_receipts
        write_json(directory/'flow_computation.json',plan_flow_receipts(plan))
        for mode in modes:
            status['artifacts'].append(encode(plan,directory,audio,mode=mode))
            print(case['id'],mode,'rendered',flush=True)
        status.update(status='rendered',audio_generation=audio_records,
                      generation_content_review='model_review_passed_not_certified' if review_content else 'not_requested',
                      layout_checks='code_at_5_progress_points_per_scene_and_static_baseline',
                      layout_policy=layout_policy,layout_findings=inspect_layout(plan,include_warnings=True),
                      knowledge_correctness='requires_independent_video_evaluation')
    except Exception as exc:
        status.update(status='render_failed',error=str(exc)[:2000])
        print(case['id'],'render_failed',str(exc)[:180],flush=True)
    write_json(directory/'manifest.json',status)
    return status


def resumable_case(out, case_id, public_hash, modes):
    paths=sorted((p for p in out.rglob('manifest.json') if p.parent.name==case_id),
                 key=lambda p:p.stat().st_mtime_ns)
    if not paths:return None,out
    previous=json.loads(paths[-1].read_text())
    if previous.get('public_input_hash')!=public_hash:
        raise ValueError('saved generation input differs from current public task')
    if previous.get('status')=='rendered':
        artifacts=previous.get('artifacts',[])
        if {a['mode'] for a in artifacts}!=set(modes):raise ValueError('saved generation modes differ')
        if any(not a.get('complete') or file_hash(a['video_path'])!=a['sha256'] for a in artifacts):
            raise ValueError('saved generation media missing or changed')
        return previous,out
    # A fresh retry directory preserves every failed/partial attempt verbatim.
    return None,out/'retries'/f'attempt_{len(paths):03d}'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'data/tasks.jsonl')
    parser.add_argument('--ids',nargs='+',default=['math_exp_02','cs_exp_01','chem_exp_01'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--model',default='qwen3.8-flash')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--modes',nargs='+',choices=['code','slides'],default=['code','slides'])
    parser.add_argument('--state-backed',action='store_true')
    parser.add_argument('--plans-from',type=Path)
    parser.add_argument('--review-content',action='store_true')
    source_modes=parser.add_mutually_exclusive_group()
    source_modes.add_argument('--source-regions',action='store_true',help='Experimental computed shading between source-plot curves')
    source_modes.add_argument('--source-graphs',action='store_true',help='Experimental source-pixel graph recovery, BFS and path recoloring')
    parser.add_argument('--cache-from',type=Path,nargs='*',default=[])
    parser.add_argument('--plain-json-plans',action='store_true',help='Experimental plan transport without response_format; strict JSON validation still required')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--max-calls',type=int,default=40)
    parser.add_argument('--max-tokens',type=int,default=220000)
    args=parser.parse_args()
    if not 1<=args.workers<=2:parser.error('local render workers must be 1 or 2')
    rows={r['id']:r for r in read_jsonl(args.data)}
    if len(args.ids)!=len(set(args.ids)) or any(Path(x).name!=x or x in {'.','..'} for x in args.ids):
        parser.error('case IDs must be unique single path components')
    unknown=set(args.ids)-set(rows)
    if unknown:parser.error(f'unknown case ids: {unknown}')
    if args.plans_from:
        try:
            for id_ in args.ids:resolve_source_plan(args.plans_from,id_)
        except (ValueError,OSError) as exc:parser.error(str(exc))
    if (args.out/'run_config.json').exists() and not args.resume:
        parser.error('output contains a run; use --resume with unchanged inputs or a new directory')
    plan_hashes={id_:file_hash(resolve_source_plan(args.plans_from,id_)) for id_ in args.ids} if args.plans_from else {}
    source_hashes={id_:[file_hash(a['local_path']) for a in public_case(rows[id_]).get('public_attachments',[]) if a.get('local_path')] for id_ in args.ids}
    freeze_run(args.out,{'entrypoint':'pipeline','model':args.model,'ids':args.ids,'modes':args.modes,
               'plans_from':str(args.plans_from) if args.plans_from else None,
               'source_plan_hashes':plan_hashes,'public_source_hashes':source_hashes,
               'dataset_hash':digest([rows[k] for k in args.ids]),
               'max_calls':args.max_calls,'max_tokens':args.max_tokens,
               'state_backed':args.state_backed,'review_content':args.review_content,'source_regions':args.source_regions,
               'source_graphs':args.source_graphs,
               'cache_sources':[str(p.resolve()) for p in args.cache_from],
               'plain_json_plans':args.plain_json_plans,
               'render_workers':args.workers,'fps':FPS})
    client=MatrixClient(args.out,model=args.model,concurrency=4,max_calls=args.max_calls,max_tokens_total=args.max_tokens,cache_sources=args.cache_from)
    def work(id_):
        previous,destination=resumable_case(args.out,id_,digest(public_case(rows[id_])),args.modes) if args.resume else (None,args.out)
        if previous:
            print(id_,'resumed verified completed media',flush=True)
            return previous
        return generate_one(rows[id_],destination,client,args.modes,args.state_backed,args.plans_from,args.review_content,args.source_regions,args.plain_json_plans,args.source_graphs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(work,args.ids))
    write_json(args.out/'manifest.json',{'model':args.model,'cases':results,'dataset_hash':digest([rows[k] for k in args.ids])})
    print(json.dumps({'rendered':sum(r['status']=='rendered' for r in results),'total':len(results)}),flush=True)


if __name__=='__main__':
    main()
