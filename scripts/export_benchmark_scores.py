"""Export stored scores and evidence without generating or replacing any ratings."""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.run_benchmark_v2 import assessment_coverage, read_jsonl, unique_by_id


def export(rows, destination):
    fields = ['case_id', 'section', 'criterion', 'status', 'score', 'scale',
              'start_s', 'end_s', 'finding', 'evidence']
    with destination.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        def emit(case_id, section, criterion, item, *, start=None, end=None, scale='1..5'):
            score = item.get('score')
            evidence = {k: item[k] for k in ('evidence_frames', 'speech_ids', 'window_ids',
                        'segment_id', 'evidence_scope', 'evidence_timestamps_s', 'segment_citations',
                        'observed', 'expected', 'evidence_constraints') if k in item}
            writer.writerow({'case_id': case_id, 'section': section, 'criterion': criterion,
                'status': item.get('status') or ('not_applicable' if item.get('applicable') is False else 'scored' if score is not None else 'evaluation_failed'),
                'score': score, 'scale': scale, 'start_s': start, 'end_s': end,
                'finding': item.get('finding') or item.get('reason') or item.get('error'),
                'evidence': json.dumps(evidence, ensure_ascii=False)})
        for row in rows:
            case_id = row['id']
            for name, cell in assessment_coverage(row).items():
                emit(case_id, 'summary', name, cell, scale=cell['scale'])
            scoring = row.get('scoring', {})
            for group, value in (scoring.get('groups') or {}).items():
                emit(case_id, 'groups', group, {'score':value}, scale='0..100')
            for axis, value in scoring.get('axis_scores_after_caps', {}).items():
                emit(case_id, 'axis_scores_after_caps', axis, {'score':value}, scale='0..100')
            for name in ('eight_axis_diagnostic_score', 'presentation_score', 'pre_audio_score', 'spoken_teaching_score'):
                if name in scoring:
                    emit(case_id, 'stored_diagnostics', name, {'score':scoring[name]}, scale='0..100')
            for name, axis in row.get('axes', {}).items():
                for criterion in axis.get('criteria', []):
                    emit(case_id, name, criterion['id'], criterion)
            for section in ('instructional_presentation', 'narration_review'):
                for criterion in row.get(section, {}).get('criteria', []):
                    emit(case_id, section, criterion['id'], criterion)
            for criterion in row.get('supplementary', {}).get('teaching_engagement', {}).get('criteria', []):
                emit(case_id, 'teaching_engagement', criterion['id'], criterion)
            for window in row.get('instructional_presentation', {}).get('segments', []):
                for criterion in window.get('review', {}).get('criteria', []):
                    emit(case_id, f"window_{window['id']}", criterion['id'],
                         {**criterion, 'segment_id':window['id'], 'evidence_scope':'segment_local_frames'},
                         start=window['start_s'], end=window['end_s'])
            for requirement in row.get('task_completion', {}).get('requirements', []):
                emit(case_id, 'task_completion_requirements', requirement['id'], requirement, scale='categorical_observed_status')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = list(unique_by_id(read_jsonl(args.results), latest=True).values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export(rows, args.out)
    print(json.dumps({'cases':len(rows),'out':str(args.out)}))


if __name__ == '__main__':
    main()
