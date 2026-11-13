"""Collaborator CLI: configure services once, generate, evaluate, and resume."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys

from .common import ROOT, digest, public_case, read_jsonl, write_json, write_jsonl
from .delivery import build_report
from .pipeline import generate_one
from .provenance import file_hash, freeze_run
from .services import JudgeClient, ServicePool, service_from
from .tts import resolve_tts

DEFAULT_IDS = ['math_exp_02', 'cs_exp_01', 'chem_exp_01']


def select_cases(data, ids=None, suite=None, *, num=None, offset=0):
    """Select a stable slice; an explicit count defaults to the full bank."""
    if num is not None and (type(num) is not int or num < 1):
        raise ValueError('--num must be a positive integer')
    if type(offset) is not int or offset < 0:
        raise ValueError('--offset must be a nonnegative integer')
    if offset and num is None:
        raise ValueError('--offset requires --num')
    if suite is None:
        suite = 'all' if num is not None else 'smoke'
    if suite not in {'smoke', 'core', 'all'}:
        raise ValueError('unknown suite')
    rows = read_jsonl(data)
    all_ids = [r['id'] for r in rows]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError('dataset has duplicate case IDs')
    if ids:
        if len(ids) != len(set(ids)) or set(ids)-set(all_ids):
            raise ValueError('case IDs must be unique and present in the dataset')
        lookup = {r['id']: r for r in rows}; rows = [lookup[id_] for id_ in ids]
    elif suite == 'smoke':
        rows = [r for r in rows if r['id'] in DEFAULT_IDS]
    if not rows:
        raise ValueError('no selected cases')
    if num is not None:
        if offset + num > len(rows):
            raise ValueError(f'requested --offset {offset} --num {num}, but only {len(rows)} cases are available')
        rows = rows[offset:offset + num]
    for r in rows:
        if Path(r['id']).name != r['id'] or r['id'] in {'', '.', '..'}:
            raise ValueError('unsafe case ID')
    return rows


def resolve_services(args, config):
    gen = dict(config.get('generator', {}))
    if args.model: gen['model'] = args.model
    if args.url: gen['url'] = args.url
    if args.api_key_env: gen['api_key_env'] = args.api_key_env
    gen.setdefault('model', os.environ.get('VIDEO_TEACHER_MODEL', ''))
    gen.setdefault('url', os.environ.get('VIDEO_TEACHER_BASE_URL', ''))
    generator = service_from(gen)
    judge = service_from(config.get('judge'), fallback=generator)
    audio_config = config.get('audio_judge')
    if audio_config is False:
        audio = None
    elif audio_config is not None:
        audio = service_from(audio_config, fallback=judge)
    elif 'omni' in judge.model.lower():
        audio = judge
    elif judge.model.startswith('qwen'):
        audio = service_from({'model': 'qwen3.5-omni-flash'}, fallback=judge)
    else:
        audio = None
    return generator, judge, audio


def improve(case, result, directory, client, *, tts=None, piano_bridge=False, layer_order=False, direction_guard=False):
    from .visual_agent import evidence, review, run_variant
    artifact = next(a for a in result['artifacts'] if a['mode'] == 'code')
    plan = json.loads((Path(artifact['video_path']).parent/'plan.json').read_text())
    if any(p.get('type')=='spatial_graph' for s in plan['scenes'] for p in s.get('primitives',[])):
        return {**result,'visual_repair':{'status':'protected_spatial_graph_backend',
                 'reason':'Preserve checked graph relations; the ordinary primitive editor does not preserve this representation.'}}
    if any(s.get('bond_cashflows') for s in plan['scenes']):
        return {**result,'visual_repair':{'status':'protected_bond_cashflows_backend',
                 'reason':'Keep computed cash flows, associated explanation and independent check together.'}}
    if any(s.get('nephron_path') for s in plan['scenes']):
        return {**result,'visual_repair':{'status':'protected_nephron_path_backend',
                 'reason':'Keep the verified connected filtrate path and separate blood route.'}}
    if any(s.get('contact_pair') for s in plan['scenes']):
        return {**result,'visual_repair':{'status':'protected_contact_pair_backend',
                 'reason':'Keep the compiled contact and distinct force recipients.'}}
    if any(p.get('type')=='piano_walk' for s in plan['scenes'] for p in s.get('primitives',[])):
        return {**result,'visual_repair':{'status':'protected_spoken_action_backend',
                 'reason':'Measured speech-cued key movements require their compiled narration/timing.'}}
    if any(s.get('source_visual') or s.get('state_visual') for s in plan['scenes']):
        return {**result, 'visual_repair': {'status': 'protected_state_or_source_backend',
                'reason': 'Computed/source visuals are retained; this repair operator edits general primitives only.'}}
    directory.mkdir(parents=True, exist_ok=True)
    from .triangle import bind as bind_triangle
    from .voice import bind as bind_voice
    voice_plan, voice_receipt = bind_triangle(plan, case)
    compilation = 'triangle_cut'
    if voice_receipt['status'] != 'compiled':
        voice_plan, voice_receipt = bind_voice(plan, case)
        compilation = 'voice_correspondence'
    if voice_receipt['status'] != 'compiled':
        if piano_bridge:
            from .keyboard_bridge import bind as bind_keyboard
            compilation = 'piano_key_moves'
        else:
            from .keyboard import bind as bind_keyboard
            compilation = 'piano_intervals'
        voice_plan, voice_receipt = bind_keyboard(plan, case)
    if voice_receipt['status'] != 'compiled':
        from .contact_pair import bind as bind_contact
        voice_plan, voice_receipt = bind_contact(plan, case)
        compilation = 'contact_force_pair'
    if voice_receipt['status'] != 'compiled':
        from .nephron import bind as bind_nephron
        voice_plan, voice_receipt = bind_nephron(plan, case)
        compilation = 'nephron_route'
    if voice_receipt['status'] != 'compiled':
        from .bond import bind as bind_bond
        voice_plan, voice_receipt = bind_bond(plan, case)
        compilation = 'bond_cashflows'
    if voice_receipt['status'] == 'compiled':
        from .pipeline import encode, synthesize
        from .scene import validate_plan, inspect_layout
        from .rerender import decoded_audio_hash
        candidate_dir = directory/compilation
        validate_plan(voice_plan, case)
        speech_changed = bool(voice_receipt.get('changed_narration_scenes'))
        audio_path = artifact['video_path']
        if speech_changed:
            audio_path, _ = synthesize(voice_plan,candidate_dir,tts=tts)
            validate_plan(voice_plan,case)
        write_json(candidate_dir/'plan.json', voice_plan)
        write_json(candidate_dir/'correspondence.json', voice_receipt)
        findings = inspect_layout(voice_plan, include_warnings=True)
        write_json(candidate_dir/'layout_findings.json', findings)
        repaired_artifact = encode(voice_plan, candidate_dir, audio_path, mode='code', copy_audio=not speech_changed)
        identical = decoded_audio_hash(artifact['video_path']) == decoded_audio_hash(repaired_artifact['video_path'])
        write_json(candidate_dir/'audio_receipt.json', {'decoded_audio_identical': identical})
        if not speech_changed and not identical: raise ValueError('compiled diagram repair changed the source audio')
        return {**result, 'original_artifacts': result['artifacts'], 'artifacts': [repaired_artifact],
                'visual_repair': {'status': 'compiled_'+compilation, 'receipt': voice_receipt,
                                 'layout_findings': findings, 'decoded_audio_identical': identical,
                                 'narration_recompiled': speech_changed}}
    # Repair bounded presentation defects before asking a visual model about
    # content. Retain the latest rendered stage if a later stage fails.
    from .label_repair import repair as repair_labels
    from .stroke_visibility import repair as repair_strokes
    retained_stage = None
    stages = [('label_repair', repair_labels), ('stroke_visibility_repair', repair_strokes)]
    if layer_order:
        def repair_layers(current):
            from .layer_order import inspect_plan, propose
            targets = list(range(len(current['scenes'])))
            inventory = inspect_plan(current, targets)
            selected = {r['scene'] for r in inventory}
            records = evidence(current, directory/'layer_order_repair'/'before_frames',
                               video=artifact['video_path']) if inventory else []
            records = [r for r in records if r['scene'] in selected]
            return propose(client, current, case, targets, records,
                           directory/'layer_order_repair'/'proposal')
        stages.append(('layer_order_repair', repair_layers))
    for stage, repair in stages:
        try:
            stage_plan, receipt = repair(plan)
            if receipt['status'] != 'changed':
                continue
            from .pipeline import encode
            from .scene import validate_plan
            from .rerender import decoded_audio_hash, diagram_only_plan
            stage_dir = directory/stage
            validate_plan(stage_plan, case)
            diagram_only_plan(plan, stage_plan)
            write_json(stage_dir/'plan.json', stage_plan)
            write_json(stage_dir/'receipt.json', receipt)
            stage_artifact = encode(stage_plan, stage_dir, artifact['video_path'], mode='code', copy_audio=True)
            if decoded_audio_hash(artifact['video_path']) != decoded_audio_hash(stage_artifact['video_path']):
                raise ValueError(stage+' changed original audio')
            result = {**result, 'original_artifacts': result.get('original_artifacts', result['artifacts']),
                      'artifacts': [stage_artifact], stage: {
                          'receipt': receipt, 'artifact': stage_artifact, 'decoded_audio_identical': True}}
            plan, artifact = stage_plan, stage_artifact
            retained_stage = stage
        except Exception as exc:
            failure = {'stage':stage,'status':'failed_current_artifact_retained',
                       'error':f'{type(exc).__name__}: {str(exc)[:1800]}'}
            write_json(directory/stage/'failure.json', failure)
            result = {**result,'preflight_repair_failures':result.get('preflight_repair_failures',[])+[failure]}
    frames = evidence(plan, directory/'before_frames', video=artifact['video_path'])
    direction_contract = None
    if direction_guard:
        from .arrow_direction_guard import propose as propose_direction
        try:
            # Freeze bindings from source evidence before either the critic or
            # patch call. Model binding is still fallible and not benchmark truth.
            direction_contract = propose_direction(client, plan, case, frames, directory/'direction_binding')
            result = {**result, 'direction_binding': direction_contract}
        except Exception as exc:
            failure = {'status': 'direction_binding_failed_previous_retained',
                       'error': f'{type(exc).__name__}: {str(exc)[:1800]}'}
            write_json(directory/'direction_binding/failure.json', failure)
            return {**result, 'visual_repair': failure}
    try:
        feedback = review(client, case, plan, frames, directory/'before_feedback.json', 'method_critic:'+case['id'])
    except Exception as exc:
        if retained_stage is None and not result.get('preflight_repair_failures'):
            raise
        return {**result, 'visual_repair': {'status': 'review_failed',
                'error': f'{type(exc).__name__}: {str(exc)[:1800]}',
                'retained_stage': 'rendered_'+(retained_stage or 'input')+'; no semantic-review acceptance'}}
    if not any(i['visual_edit_sufficient'] for i in feedback['issues']):
        return {**result, 'visual_repair': {'status': 'no_visual_edit_requested', 'feedback': feedback}}
    options = {'direction_contract': direction_contract} if direction_guard else {}
    repaired = run_variant(client, case, plan, artifact, feedback, frames, {'rules': []}, directory/'candidate', 'method_repair', **options)
    output = {**result, 'visual_repair': repaired,
              'original_artifacts': result.get('original_artifacts', result['artifacts'])}
    if repaired.get('artifact'):
        output['artifacts'] = [repaired['artifact']]
    return output


def execute(args):
    if args.command == 'student':
        from .student_run import execute as execute_student
        return execute_student(args)
    config = json.loads(args.config.read_text()) if args.config else {}
    piano_bridge = config.get('method_piano_bridge',False)
    if type(piano_bridge) is not bool:
        raise ValueError('method_piano_bridge must be a boolean')
    layer_order = config.get('method_layer_order', False)
    if type(layer_order) is not bool:
        raise ValueError('method_layer_order must be a boolean')
    direction_guard = config.get('method_direction_guard', False)
    if type(direction_guard) is not bool:
        raise ValueError('method_direction_guard must be a boolean')
    object_connections = config.get('method_object_connections', False)
    if type(object_connections) is not bool:
        raise ValueError('method_object_connections must be a boolean')
    apparent_size = config.get('method_apparent_size', False)
    if type(apparent_size) is not bool:
        raise ValueError('method_apparent_size must be a boolean')
    transcript_guard = config.get('evaluation_transcript_guard', False)
    if type(transcript_guard) is not bool:
        raise ValueError('evaluation_transcript_guard must be a boolean')
    spatial_graphs = config.get('method_spatial_graphs', False)
    if type(spatial_graphs) is not bool:
        raise ValueError('method_spatial_graphs must be a boolean')
    spatial_contracts = config.get('method_spatial_contracts', False)
    if type(spatial_contracts) is not bool:
        raise ValueError('method_spatial_contracts must be a boolean')
    if spatial_graphs and spatial_contracts:
        raise ValueError('choose method_spatial_graphs or method_spatial_contracts, not both')
    generator, judge, audio = resolve_services(args, config)
    manifest = None
    ids = args.ids
    if args.command == 'evaluate':
        if not args.manifest:
            raise ValueError('evaluate requires --manifest from generation or imported media')
        manifest = json.loads(args.manifest.read_text())
        manifest_ids = [r['id'] for r in manifest['cases']]
        if len(set(manifest_ids)) != len(manifest_ids):
            raise ValueError('duplicate case IDs in input manifest')
        if not ids and args.suite in (None, 'smoke'):
            ids = manifest.get('planned_ids') or manifest_ids
    rows = select_cases(args.data, ids, args.suite,
                        num=getattr(args, 'num', None), offset=getattr(args, 'offset', 0))
    from .student_run import settings_from, public_settings, run_stage
    student_settings = settings_from(config, judge, args.config.parent if args.config else ROOT)
    tts = resolve_tts(config.get('tts')) if args.command != 'evaluate' else None
    missing = [r['id'] for r in rows if any(not a.get('local_path') for a in public_case(r).get('public_attachments', []))]
    if missing:
        from .assets import fetch
        lookup = {r['id']: r for r in rows}
        if args.command == 'doctor':
            raise ValueError('public images missing; run generation to download: '+', '.join(missing[:8]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            assets = list(pool.map(fetch, [lookup[x] for x in missing]))
        if any(a['status'] == 'error' for a in assets):
            raise ValueError('some public source images could not be downloaded')
    video_service = None
    applicability = {}
    if config.get('evaluation_applicability'):
        from .applicability import load_annotations
        annotation_path = Path(config['evaluation_applicability'])
        if not annotation_path.is_absolute():
            annotation_path = (args.config.parent if args.config else ROOT)/annotation_path
        applicability = load_annotations(annotation_path, rows)
    if args.backend == 'video' and args.command != 'evaluate':
        if args.command == 'method':
            raise ValueError('method uses the code backend; use bench --backend video for the native API baseline')
        from .video_api import video_service_from
        video_service = video_service_from(config.get('video'))
    public_config = {'entrypoint': 'one_command_v2', 'command': args.command,
                     'generator': generator.public(), 'judge': judge.public(),
                     'audio_judge': audio.public() if audio else None, 'tts': tts,
                     'backend': args.backend, 'ids': [r['id'] for r in rows],
                     'dataset_hash': digest(rows), 'public_input_hashes': {r['id']: digest(public_case(r)) for r in rows},
                     'source_hashes_public': {r['id']: [file_hash(a['local_path']) for a in public_case(r).get('public_attachments', [])] for r in rows},
                     'api_workers': args.api_workers, 'render_workers': args.render_workers,
                     'eval_workers': args.eval_workers, 'max_calls': args.max_calls, 'max_tokens': args.max_tokens,
                     'repair': args.command == 'method' and not args.no_repair,
                     'layout_policy':'report' if args.command=='bench' else 'repair_then_report',
                     'video_service': video_service.public() if video_service else None,
                     'max_video_seconds': getattr(args, 'max_video_seconds', 120),
                     'artifact_mode': getattr(args, 'mode', None)}
    if student_settings:
        public_config['student_evaluation'] = public_settings(student_settings, rows)
    if piano_bridge:
        public_config['method_piano_bridge'] = True
    if layer_order:
        public_config['method_layer_order'] = True
    if direction_guard:
        public_config['method_direction_guard'] = True
    if object_connections:
        public_config['method_object_connections'] = True
    if apparent_size:
        public_config['method_apparent_size'] = True
    if transcript_guard:
        public_config['evaluation_transcript_guard'] = True
    if spatial_graphs:
        public_config['method_spatial_graphs'] = True
    if spatial_contracts:
        public_config['method_spatial_contracts'] = True
    if applicability:
        public_config['evaluation_applicability'] = applicability
    if args.command == 'doctor':
        print(json.dumps({'status': 'configuration_ready', 'selected_cases': len(rows),
                          'services': {k: public_config[k] for k in ('generator', 'judge', 'audio_judge')},
                          'tts': tts, 'audio_warning': None if audio else 'No audio judge; audio dimensions cannot be fully scored.',
                          'network_probed': False}, ensure_ascii=False, indent=2))
        return 0
    out = args.out.resolve()
    if (out/'run_config.json').exists() and not args.resume:
        raise ValueError('run exists; use --resume or a fresh output directory')
    if args.command == 'evaluate':
        if not args.manifest:
            raise ValueError('evaluate requires --manifest from generation or imported media')
        public_config['input_manifest_hash'] = file_hash(args.manifest)
    freeze_run(out, public_config)
    write_jsonl(out/'evaluation_tasks.jsonl', rows)
    write_jsonl(out/'generation_inputs.jsonl', [public_case(r) for r in rows])
    pool = ServicePool(out/'api', concurrency=args.api_workers, max_calls=args.max_calls, max_tokens=args.max_tokens)
    gen_client = pool.client(generator)
    eval_client = JudgeClient(pool.client(judge), pool.client(audio) if audio else None)
    native_api = None
    if video_service:
        from .video_api import VideoAPI
        native_api = VideoAPI(video_service, gen_client, max_seconds=public_config['max_video_seconds'])
    generated = [{'id': r['id'], 'status': 'not_started', 'artifacts': []} for r in rows]
    evaluated = []
    write_json(out/'manifest.json', {'cases': generated, 'planned_ids': [r['id'] for r in rows]})
    def generate(case):
        id_ = case['id']; saved = out/'generation'/id_/'delivery.json'
        if args.resume and saved.exists():
            previous = json.loads(saved.read_text())
            if previous.get('status') == 'rendered':
                if previous['public_input_hash'] != digest(public_case(case)) or any(file_hash(a['video_path']) != a['sha256'] for a in previous['artifacts']):
                    raise ValueError('completed generation changed; refusing to reuse')
                print(id_, 'reused verified video', flush=True)
                return previous
        base = out/'generation'
        if saved.exists() and not native_api:
            attempts = list((base/id_/'attempts').glob('attempt_*'))
            base = base/id_/'attempts'/f'attempt_{len(attempts)+1:03d}'
        try:
            if native_api:
                from .native_pipeline import generate_native
                result = generate_native(case, base, gen_client, native_api, tts)
                write_json(saved, result)
                return result
            first = case['prompt_text'].split('\n')[0].lower()
            has_source = bool(public_case(case).get('public_attachments'))
            regions = args.command == 'method' and has_source and 'shade' in first
            graphs = args.command == 'method' and has_source and 'shortest path' in first and 'red' in first
            overlays = has_source and not regions and not graphs and 'replace' not in first
            result = generate_one(case, base, gen_client, ['code'], use_state=args.command == 'method',
                                  source_regions=regions, source_graphs=graphs, source_overlays=overlays, tts=tts,
                                  layout_policy='report' if args.command=='bench' else 'repair_then_report',
                                  spatial_graphs=spatial_graphs and args.command=='method',
                                  spatial_contracts=spatial_contracts and args.command=='method')
            if has_source and result['status'] != 'rendered' and not overlays:
                specialized = result
                result = generate_one(case, base/id_/'annotation_fallback', gen_client, ['code'],
                                      source_overlays=True, tts=tts,
                                      layout_policy='report' if args.command=='bench' else 'repair_then_report')
                result['specialized_backend_attempt'] = specialized
            if result['status'] == 'rendered' and args.command == 'method' and not args.no_repair:
                try:
                    result = improve(case, result, base/id_/'visual_repair', gen_client,
                                     tts=tts,piano_bridge=piano_bridge,layer_order=layer_order,direction_guard=direction_guard)
                except Exception as exc:
                    result['visual_repair'] = {'status': 'diagnostic_failed_original_retained', 'error': str(exc)[:600]}
                if apparent_size:
                    from .apparent_size import repair as order_sizes
                    result = order_sizes(case, result, base/id_/'apparent_size', gen_client)
                if object_connections:
                    from .object_connections import repair as connect_objects
                    result = connect_objects(case, result, base/id_/'object_connections', gen_client)
        except Exception as exc:
            result = {'id': id_, 'status': 'generation_error', 'error': str(exc)[:600], 'artifacts': [],
                      'public_input_hash': digest(public_case(case))}
        write_json(saved, result)
        return result
    try:
        if args.command == 'evaluate':
            inventory = {r['id']: r for r in manifest['cases']}
            generated = [inventory.get(r['id'], {'id': r['id'], 'status': 'missing_from_manifest', 'artifacts': []}) for r in rows]
            for record in generated:
                artifacts = [a for a in record.get('artifacts', []) if a.get('complete')]
                mode = getattr(args, 'mode', None)
                if mode:
                    artifacts = [a for a in artifacts if a.get('mode') == mode]
                if len(artifacts) > 1:
                    raise ValueError('manifest has multiple artifact modes; explicitly select --mode')
                for a in artifacts:
                    p = Path(a['video_path'])
                    a['video_path'] = str((args.manifest.parent/p).resolve()) if not p.is_absolute() else str(p)
                record['artifacts'] = artifacts
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.render_workers) as workers:
                futures = {workers.submit(generate, r): r['id'] for r in rows}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    generated = [result if r['id'] == result['id'] else r for r in generated]
                    write_json(out/'manifest.json', {'cases': generated, 'planned_ids': [r['id'] for r in rows]})
                    build_report(out, rows, generated, evaluated)
        write_json(out/'manifest.json', {'cases': generated, 'planned_ids': [r['id'] for r in rows]})
        lookup = {r['id']: r for r in rows}
        def evaluate(record):
            from .judge import evaluate as judge_video
            id_ = record['id']; case = lookup[id_]
            artifact = next(a for a in record.get('artifacts', []) if a.get('complete'))
            directory = out/'evaluation'/id_
            if file_hash(artifact['video_path']) != artifact['sha256']:
                raise ValueError('generation media hash mismatch')
            scores = directory/'scores.json'
            if args.resume and scores.exists():
                previous = json.loads(scores.read_text())
                if previous['video_sha256'] != artifact['sha256'] or previous['case_hash'] != digest(case):
                    raise ValueError('saved evaluation differs from media/task')
                if previous.get('scoring', {}).get('overall') is not None or not getattr(args, 'retry_incomplete', False):
                    print(id_, 'reused saved evaluation', flush=True)
                    return previous
            if directory.exists():
                attempts = directory/'previous_attempts'; attempts.mkdir(exist_ok=True)
                destination = attempts/f'attempt_{len(list(attempts.iterdir()))+1:03d}'; destination.mkdir()
                for item in list(directory.iterdir()):
                    if item != attempts:
                        item.rename(destination/item.name)
            try:
                return judge_video(artifact['video_path'], case, directory, eval_client,
                                   **({'transcript_guard': True} if transcript_guard else {}),
                                   **({'applicability': applicability[id_]} if applicability else {}))
            except Exception as exc:
                error = {'case_id': id_, 'status': 'evaluation_error', 'error': str(exc)[:600]}
                write_json(directory/'error.json', error)
                print(id_, 'evaluation_error', error['error'], flush=True)
                return error
        jobs = [r for r in generated if any(a.get('complete') for a in r.get('artifacts', []))]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.eval_workers) as workers:
            futures = [workers.submit(evaluate, r) for r in jobs]
            for future in concurrent.futures.as_completed(futures):
                evaluated.append(future.result())
                write_json(out/'evaluations.json', evaluated)
                build_report(out, rows, generated, evaluated)
        students = run_stage(out, rows, generated, pool, student_settings,
                             resume=args.resume, workers=args.eval_workers) if student_settings else None
        summary = build_report(out, rows, generated, evaluated, students=students)
        from .api_usage import summarize
        write_json(out/'api_usage.json', summarize(out/'api'))
        print(json.dumps({k: v for k, v in summary.items() if k != 'cases'}, ensure_ascii=False, indent=2))
        print('Report:', out/'REPORT.md', flush=True)
        student_complete = students is None or all(r['status'] == 'complete' for r in students)
        return 0 if summary['delivered_cases'] == len(rows) and summary['scored_cases'] == len(rows) and student_complete else 2
    finally:
        if native_api: native_api.close()
        pool.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bench', 'method', 'evaluate', 'student', 'doctor'])
    parser.add_argument('--config', type=Path, help='JSON service configuration; keep real credentials outside repo')
    parser.add_argument('--model')
    parser.add_argument('--url')
    parser.add_argument('--api-key-env', help='environment variable containing the key (default VIDEO_TEACHER_API_KEY)')
    parser.add_argument('--data', type=Path, default=ROOT/'data/tasks.jsonl')
    parser.add_argument('--suite', choices=['smoke', 'core', 'all'],
                        help='default: three smoke cases; with --num: full bank; evaluate/student: input manifest')
    parser.add_argument('--ids', nargs='+')
    parser.add_argument('--num', type=int, help='run exactly N cases in stable input order (defaults to full bank)')
    parser.add_argument('--offset', type=int, default=0, help='skip N cases before --num; default 0')
    parser.add_argument('--backend', choices=['code', 'video'], default='code')
    parser.add_argument('--out', type=Path, default=ROOT/'results/localbench/collaborator_run')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--mode', help='explicit artifact mode when importing a multi-mode manifest')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--retry-incomplete', action='store_true', help='with --resume, retry null/partial evaluations and retain previous evidence')
    parser.add_argument('--no-repair', action='store_true', help='method ablation: skip visual feedback repair')
    parser.add_argument('--api-workers', type=int, default=8)
    parser.add_argument('--render-workers', type=int, default=2)
    parser.add_argument('--eval-workers', type=int, default=4)
    parser.add_argument('--max-calls', type=int, default=8000)
    parser.add_argument('--max-tokens', type=int, default=80_000_000)
    parser.add_argument('--max-video-seconds', type=int, default=120, help='native API submitted output seconds cap, including rounding')
    args = parser.parse_args()
    if not 1 <= args.api_workers <= 64 or not 1 <= args.render_workers <= 2 or not 1 <= args.eval_workers <= 16:
        parser.error('API workers 1..64, render workers 1..2, evaluation workers 1..16 required')
    if args.max_calls < 1 or args.max_tokens < 1:
        parser.error('positive call/token budgets required')
    if args.num is not None and args.num < 1:
        parser.error('--num must be positive')
    if args.offset < 0 or (args.offset and args.num is None):
        parser.error('--offset must be nonnegative and requires --num')
    try:
        return execute(args)
    except (ValueError, OSError) as exc:
        print(f'Configuration/run error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
