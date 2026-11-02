"""Export compact, hash-linked evidence for a completed fixed-ten resume run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.strict_manim import inspect_exact
from generation.quality_gate import assess
from eval.run_benchmark_v2 import report


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.source, args.run, args.out = args.source.resolve(), args.run.resolve(), args.out.resolve()
    completion = json.loads((args.run / 'completion.json').read_text())
    assert completion['execution_finished'] is True
    entries = json.loads((args.run / 'generation_summary.json').read_text())
    cases = [json.loads(s) for s in (args.source / 'prompts.jsonl').read_text().splitlines()]
    ids = [c['id'] for c in cases]
    assert len(entries) == len(set(ids)) == len(ids) == 10
    assert [e['id'] for e in entries] == ids
    evaluations = {e['id']: e for e in map(json.loads, (args.run / 'video-teacher-2x8-v4/per_case.jsonl').read_text().splitlines())}
    assert set(evaluations) == set(ids)
    args.out.mkdir(parents=True, exist_ok=True)
    evidence = []
    attempts = []
    for entry in entries:
        cid = entry['id']
        generation = entry['generation']
        evaluation = evaluations[cid]
        assert assess(generation, evaluation) == generation['quality_gate']
        gate = generation['quality_gate']
        assert entry['quality_passed'] == gate['passed']
        timing = None
        video_sha = None
        if entry['status'] == 'ok':
            video = Path(entry['video_path'])
            timing = inspect_exact(video)
            assert timing['valid']
            video_sha = digest(video)
            assert video_sha == evaluation['video_sha256']
        evidence.append(dict(id=cid, status=entry['status'], quality_passed=gate['passed'],
            timing=timing, video_path=entry['video_path'], video_sha256=video_sha,
            contract_version=generation.get('contract_version'),
            contract_sha256=generation.get('contract_sha256'),
            source_required=generation.get('source_required'),
            source_edit_regions=generation.get('source_edit_regions'),
            generation_error=generation.get('error'),
            quality_checks=gate['checks'], quality_failures=gate['failures']))
        for attempt in range(3):
            candidates = [root / f'attempt_{attempt}' / f'model_result_{cid}.json'
                          for root in (args.source, args.run)]
            available = [p for p in candidates if p.exists()]
            assert available, (cid, attempt)
            path = available[-1]
            data = json.loads(path.read_text())
            evpath = path.with_name(f'{cid}_evaluation.json')
            assert evpath.exists(), evpath
            diag = data.get('strict_diagnostics', {})
            preservation = diag.get('source_preservation', {})
            pre = preservation.get('pre_encoding', {})
            attempts.append(dict(id=cid, attempt=attempt, result_path=str(path.relative_to(ROOT)),
                result_sha256=digest(path), evaluation_sha256=digest(evpath),
                complete=data.get('complete'), error=data.get('error'),
                quality_failures=data.get('quality_gate', {}).get('failures'),
                timing=data.get('timing'), diagnostic_timing=diag.get('timing'),
                source_preservation={k: v for k, v in preservation.items()
                    if k not in ('pre_encoding', 'unexpected_change_boxes_pixels')},
                pre_encoding={k: v for k, v in pre.items() if not isinstance(v, list)}))
    assert len(attempts) == 30
    assert completion['generated'] == sum(e['status'] == 'ok' for e in evidence)
    assert completion['quality_passed'] == sum(e['quality_passed'] for e in evidence)
    aggregate = report([evaluations[cid] for cid in ids], {c['id']: c for c in cases})
    assert aggregate == json.loads((args.run / 'video-teacher-2x8-v4/aggregate.json').read_text())
    write(args.out / 'completion.json', completion)
    write(args.out / 'cases.json', evidence)
    write(args.out / 'attempts.json', attempts)
    write(args.out / 'aggregate.json', aggregate)
    (args.out / 'per_case.jsonl').write_text(''.join(json.dumps(evaluations[cid], ensure_ascii=False) + '\n' for cid in ids))
    write(args.out / 'provenance.json', dict(source_run=str(args.source.relative_to(ROOT)),
        resumed_run=str(args.run.relative_to(ROOT)),
        source_run_config=json.loads((args.source / 'run_config.json').read_text()),
        resumed_run_config=json.loads((args.run / 'run_config.json').read_text()),
        prompt_sha256=digest(args.source / 'prompts.jsonl'),
        verification='Ten IDs, thirty completed attempts, seven redecoded video timings and hashes, all gates and aggregate recomputed without model calls.'))
    (args.out / 'prompts.jsonl').write_bytes((args.source / 'prompts.jsonl').read_bytes())
    print(json.dumps(dict(verified_cases=10, completed_attempts=len(attempts), generated=completion['generated'], quality_passed=completion['quality_passed'])))


if __name__ == '__main__':
    main()
