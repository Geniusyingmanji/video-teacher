"""Audit all current tasks and source assets without changing task requirements."""
import json
import argparse
from pathlib import Path
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generation.source_geometry import resolve_source
from generation.strict_video_contract import make_contract
from generation.lesson_spec import duration_spec


def audit(prompts=None):
    cases = [json.loads(line) for line in (prompts or ROOT/'data/prompts/candidate_400_lessons_v3.jsonl').read_text().splitlines() if line.strip()]
    ids = Counter(case['id'] for case in cases)
    rows = []
    for case in cases:
        errors = []
        if ids[case['id']] != 1:
            errors.append('duplicate_id')
        if not str(case.get('prompt_text') or '').strip():
            errors.append('missing_current_task')
        source = None
        try:
            duration_spec(case)
            source = resolve_source(case, ROOT/'data/sources/grade/selected_assets/before')
            contract = make_contract(case, source)
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
            contract = {}
        rows.append({'id': case['id'], 'source_image': str(source) if source else None,
                     'source_size_pixels': contract.get('source_size_pixels'),
                     'duration_seconds':contract.get('duration_seconds'),
                     'contract_version':contract.get('version'),
                     'task_type': case.get('task_type'), 'errors': errors})
    return {'scope': 'structural preflight only; no semantic or video quality claim',
            'total': len(rows), 'valid': sum(not row['errors'] for row in rows),
            'source_tasks': sum(row['source_image'] is not None for row in rows),
            'rows': rows}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompts',type=Path,default=ROOT/'data/prompts/candidate_400_lessons_v3.jsonl')
    parser.add_argument('--out',type=Path,default=ROOT/'results/reports/lessons_v2/preflight400.json')
    args=parser.parse_args();out=args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    report = audit(args.prompts)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}))
    raise SystemExit(0 if report['total'] == report['valid'] == 400 else 1)
