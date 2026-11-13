"""Optional third evaluation block, also runnable against existing final videos."""
from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

from .common import digest, public_case, write_json, write_jsonl
from .delivery import build_report
from .provenance import file_hash, freeze_run
from .services import ServicePool, service_from
from .student import VERSION, evaluate, validate_profiles, protocol_version


def settings_from(config, judge, base):
    cfg = config.get('student_evaluation')
    if cfg in (None, False):
        return None
    if not isinstance(cfg, dict) or set(cfg)-{'student', 'reviewer', 'profiles', 'protocol'}:
        raise ValueError('student_evaluation accepts student, reviewer, profiles, protocol')
    if not cfg.get('student') or not cfg.get('profiles'):
        raise ValueError('student_evaluation requires explicit student service and profiles JSON')
    path = Path(cfg['profiles'])
    path = path if path.is_absolute() else Path(base)/path
    profiles = json.loads(path.read_text())
    if not isinstance(profiles, dict):
        raise ValueError('profiles JSON must map case IDs to lists of learner profiles')
    for value in profiles.values():
        validate_profiles(value)
    student = service_from(cfg['student'], fallback=judge)
    reviewer = service_from(cfg.get('reviewer'), fallback=judge)
    if student.model == reviewer.model and student.url == reviewer.url:
        raise ValueError('choose a separate reviewer model for student diagnostics')
    return {'student': student, 'reviewer': reviewer, 'profiles': profiles,'protocol':protocol_version(cfg.get('protocol'))}


def public_settings(settings, cases):
    missing = [r['id'] for r in cases if r['id'] not in settings['profiles']]
    if missing:
        raise ValueError('missing frozen student profiles: '+', '.join(missing))
    return {'version': protocol_version(settings.get('protocol')), 'student': settings['student'].public(),
            'reviewer': settings['reviewer'].public(),
            'profiles': {r['id']: settings['profiles'][r['id']] for r in cases},
            'total_weight': 0, 'purpose': 'separate diagnostic block; no learning-gain measurement'}


def source_hash(directory):
    if directory is None:
        return None
    directory = Path(directory)
    return {name: file_hash(directory/name) if (directory/name).is_file() else None
            for name in ('actual_audio.json', 'evidence/packet.json')}


def run_stage(out, cases, generated, pool, settings, *, evaluation_dirs=None, resume=False, workers=2):
    out = Path(out)
    public_settings(settings, cases)
    student, reviewer = pool.client(settings['student']), pool.client(settings['reviewer'])
    inventory = {r['id']: r for r in generated}
    evaluation_dirs = evaluation_dirs or {r['id']: out/'evaluation'/r['id'] for r in cases}
    def one(case):
        id_ = case['id']
        profiles = settings['profiles'][id_]
        artifacts = [a for a in inventory.get(id_, {}).get('artifacts', []) if a.get('complete')]
        directory = out/'student'/id_
        result = {'case_id': id_, 'status': 'no_video', 'metrics': {'score': None,
                  'planned_profiles': len(profiles), 'complete_profiles': 0, 'profile_coverage': 0}}
        if len(artifacts) != 1:
            result['error'] = 'exactly one complete video is required'
            write_json(directory/'student.json', result)
            return result
        artifact = artifacts[0]
        try:
            actual = file_hash(artifact['video_path'])
            if actual != artifact['sha256']:
                raise ValueError('student input media hash mismatch')
            expected = {'version': protocol_version(settings.get('protocol')), 'video_sha256': actual,
                        'public_case_hash': digest(public_case(case)), 'profiles_hash': digest(profiles),
                        'student_model': student.model, 'reviewer_model': reviewer.model,
                        'transcript_source_hashes': source_hash(evaluation_dirs.get(id_))}
            result.update(expected)
            saved = directory/'student.json'
            if resume and saved.exists():
                prior = json.loads(saved.read_text())
                if any(prior.get(k) != v for k, v in expected.items()):
                    raise ValueError('saved student inputs changed; use a fresh output directory')
                # Partial results are retained; no selective resampling of failures.
                return prior
            result = evaluate(artifact['video_path'], case, directory, student, reviewer, profiles,
                              evaluation_dir=evaluation_dirs.get(id_), workers=2,protocol=expected['version'])
            result['transcript_source_hashes'] = expected['transcript_source_hashes']
        except Exception as exc:
            result.update(status='student_evaluation_error', error=str(exc)[:500])
            # Never overwrite a prior result on a failed resume verification.
            if resume and (directory/'student.json').exists():
                write_json(directory/'resume_error.json', result)
                return result
        write_json(directory/'student.json', result)
        print(id_, 'student', result['status'], flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(one, cases))
    write_json(out/'students.json', results)
    return results


def execute(args):
    from .run import resolve_services, select_cases
    from .api_usage import summarize
    if not args.config or not args.manifest:
        raise ValueError('student requires --config and --manifest')
    config = json.loads(args.config.read_text())
    _, judge, _ = resolve_services(args, config)
    settings = settings_from(config, judge, args.config.parent)
    if settings is None:
        raise ValueError('student command needs student_evaluation configuration')
    manifest = json.loads(args.manifest.read_text())
    inventory = manifest['cases']
    ids = [r['id'] for r in inventory]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate student manifest IDs')
    selected = args.ids or (manifest.get('planned_ids') or ids if args.suite in (None, 'smoke') else None)
    cases = select_cases(args.data, selected, args.suite,
                         num=getattr(args, 'num', None), offset=getattr(args, 'offset', 0))
    planned = public_settings(settings, cases)
    by_id = {r['id']: r for r in inventory}
    generated, evaluated, directories = [], [], {}
    def resolve_path(value):
        p = Path(value)
        return p.resolve() if p.is_absolute() else (args.manifest.parent/p).resolve()
    for case in cases:
        record = by_id.get(case['id'], {'id': case['id'], 'status': 'missing_from_manifest', 'artifacts': []})
        artifacts = [a for a in record.get('artifacts', []) if a.get('complete') and (not args.mode or a.get('mode') == args.mode)]
        if len(artifacts) > 1:
            raise ValueError('student manifest has multiple videos; choose --mode')
        for artifact in artifacts:
            artifact['video_path'] = str(resolve_path(artifact['video_path']))
            if file_hash(artifact['video_path']) != artifact['sha256']:
                raise ValueError('student manifest video hash mismatch')
        record['artifacts'] = artifacts
        generated.append(record)
        directory = resolve_path(record['evaluation_dir']) if record.get('evaluation_dir') else None
        directories[case['id']] = directory
        if directory and (directory/'scores.json').is_file() and artifacts:
            score = json.loads((directory/'scores.json').read_text())
            if score.get('case_id') != case['id'] or score.get('case_hash') != digest(case) or score.get('video_sha256') != artifacts[0]['sha256']:
                raise ValueError('imported expert evaluation does not match task/media')
            evaluated.append(score)
    out = args.out.resolve()
    if (out/'run_config.json').exists() and not args.resume:
        raise ValueError('student run exists; use --resume or fresh output directory')
    freeze_run(out, {'command': 'student', 'dataset_hash': digest(cases),
                    'manifest_hash': file_hash(args.manifest), 'student_evaluation': planned,
                    'source_evaluations': {k: source_hash(v) for k, v in directories.items()},
                    'max_calls': args.max_calls, 'max_tokens': args.max_tokens,
                    'api_workers': args.api_workers, 'eval_workers': args.eval_workers})
    write_jsonl(out/'evaluation_tasks.jsonl', cases)
    write_json(out/'manifest.json', {'cases': generated, 'planned_ids': [c['id'] for c in cases]})
    write_json(out/'evaluations.json', evaluated)
    pool = ServicePool(out/'api', concurrency=args.api_workers, max_calls=args.max_calls, max_tokens=args.max_tokens)
    try:
        results = run_stage(out, cases, generated, pool, settings, evaluation_dirs=directories,
                            resume=args.resume, workers=args.eval_workers)
        summary = build_report(out, cases, generated, evaluated, students=results)
        write_json(out/'api_usage.json', summarize(out/'api'))
        print(json.dumps(summary['student_evaluation'], ensure_ascii=False, indent=2))
        print('Report:', out/'REPORT.md', flush=True)
        return 0 if all(r['status'] == 'complete' for r in results) else 2
    finally:
        pool.close()
