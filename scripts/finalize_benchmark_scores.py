"""Audit a completed scoring run and export stored results without new judging."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.run_benchmark_v2 import assessment_coverage, read_jsonl, unique_by_id
from scripts.audit_score_evidence import audit
from scripts.export_benchmark_scores import export


def finalize(directory, prompts_path):
    target = directory / 'per_case.jsonl'
    rows = unique_by_id(read_jsonl(target), latest=True)
    prompts = unique_by_id(read_jsonl(prompts_path))
    aggregate = json.loads((directory / 'aggregate.json').read_text())
    coverage = {key: assessment_coverage(row) for key, row in rows.items()}
    valid = sum(row['scoring'].get('valid') is True for row in rows.values())
    if (not prompts or set(rows) != set(prompts)
            or aggregate.get('per_case_sha256') != hashlib.sha256(target.read_bytes()).hexdigest()
            or aggregate.get('n_total') != len(rows)
            or aggregate.get('n_valid') != valid
            or aggregate.get('assessment_coverage') != coverage):
        raise ValueError('complete matching rows and aggregate required before finalization')
    reports = [audit(rows[key]) for key in prompts]
    evidence = {'passed': all(not row['errors'] for row in reports),
                'scope': 'structural_citations_provenance_and_arithmetic_not_independent_semantic_validation',
                'missing_ids': [], 'unexpected_ids': [], 'cases': reports}
    (directory / 'evidence_audit.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
    if not evidence['passed']:
        raise ValueError('evidence audit failed; final score exports withheld')
    ordered = [rows[key] for key in prompts]
    export(ordered, directory / 'all_scores.csv')
    generated = sum('generation_missing_or_failed' not in row.get('errors', []) for row in ordered)
    accepted = sum(row['scoring'].get('valid') is True and row['scoring'].get('strict_pass') is True
                   for row in ordered)
    result = {'execution_completed': True, 'n_total': len(rows), 'n_generated': generated,
              'n_generation_failed': len(rows)-generated, 'n_valid': valid,
              'n_evaluation_invalid': generated-valid, 'n_quality_accepted': accepted,
              'audit_passed': True, 'ranking_publishable': aggregate.get('ranking_publishable') is True,
              'per_case_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'aggregate_sha256': hashlib.sha256((directory/'aggregate.json').read_bytes()).hexdigest()}
    columns = list(dict.fromkeys(name for cells in coverage.values() for name in cells))
    lines = ['# Stored scoring results', '',
             f"Execution completed: {len(rows)} cases; {generated} generated videos; "
             f"{valid} valid totals; {accepted} quality acceptances.", '',
             '— means unavailable or unverified, never an invented zero. All scores are 0–100 '
             'except task_completion, which is a 0–1 requirement coverage ratio. '
             'This is model evaluation with structural auditing, not independent human certification.', '',
             '| case_id | status | '+ ' | '.join(columns)+' |',
             '| --- | --- | '+ ' | '.join('---' for _ in columns)+' |']
    for row in ordered:
        key = row['id']
        status = ('generation_failed' if 'generation_missing_or_failed' in row.get('errors', [])
                  else 'scored' if row['scoring'].get('valid') is True else 'evaluation_invalid')
        cells = ['—' if coverage[key].get(name, {}).get('score') is None else str(coverage[key][name]['score'])
                 for name in columns]
        lines.append('| '+key+' | '+status+' | '+' | '.join(cells)+' |')
    lines += ['', 'Details, criterion findings and citations: [all_scores.csv](all_scores.csv).', '']
    (directory/'scores.md').write_text('\n'.join(lines))
    (directory/'finalization.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, required=True)
    parser.add_argument('--prompts', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.results_dir, args.prompts)))


if __name__ == '__main__':
    main()
