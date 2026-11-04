"""Offline structural audit of benchmark evidence and score arithmetic, without judge calls.

This verifies provenance, citations and arithmetic, not the truth of VLM observations.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval import benchmark_scoring, benchmark_video_rubric, rubric_6x6, instructional_video, narration
from eval.run_benchmark_v2 import assessment_coverage, read_jsonl, unique_by_id


def audit(row):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    if 'generation_missing_or_failed' in row.get('errors', []):
        check(row['scoring'].get('score') is None, 'missing video has a fabricated score')
        check(all(c['score'] is None for c in assessment_coverage(row).values()), 'missing video has scored cells')
        return {'id': row['id'], 'status': 'unavailable_video', 'errors': errors}
    path = Path(row.get('video_path') or '')
    check(path.is_file(), 'source video missing')
    if path.is_file():
        check(hashlib.sha256(path.read_bytes()).hexdigest() == row.get('video_sha256'), 'video hash mismatch')
    count = row.get('sampled_frame_count', 0)
    check(count > 0, 'no inspected overview frames')
    axes = row.get('axes', {})
    for name in benchmark_scoring.VIDEO_AXES + benchmark_scoring.TEACHING_AXES:
        axis = axes.get(name, {})
        if axis.get('error') or axis.get('score') is None:
            check(row['scoring'].get('valid') is not True, name + ': missing axis accepted in total')
            continue
        try:
            if name in benchmark_video_rubric.RUBRIC:
                raw = benchmark_video_rubric.validate_result(name, axis, count)['score']
            else:
                raw = (rubric_6x6.validate_result(name, axis, count)['score'] - 1) * 25
            check(axis['score'] <= raw + .002, name + ': final score exceeds rubric evidence')
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(name + ': ' + str(exc))
    presentation = row.get('instructional_presentation', {})
    windows = {w['id']: w for w in presentation.get('segments', [])}
    if presentation.get('valid') is True:
        try:
            recomputed = instructional_video.score_review(presentation, presentation['events'], presentation['still_comparisons'])
            check(recomputed['valid'] is True and recomputed['score'] == presentation.get('score'),
                  'presentation: rubric arithmetic or validity mismatch')
            check(len(presentation['criteria']) == len(instructional_video.CRITERIA)
                  and {c['id'] for c in presentation['criteria']} == set(instructional_video.CRITERIA),
                  'presentation: missing or duplicate criteria')
        except (ValueError, TypeError, KeyError) as exc:
            errors.append('presentation: ' + str(exc))
    for index, window in windows.items():
        if window.get('error'):
            check(presentation.get('valid') is not True, f'window {index}: failed window accepted')
            continue
        try:
            instructional_video.validate(window['review'], len(window['timestamps_s']))
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f'window {index}: {exc}')
    for criterion in presentation.get('criteria', []):
        scope = windows.get(criterion.get('segment_id')) if criterion.get('evidence_scope') == 'segment_local_frames' else None
        n = len(scope['timestamps_s']) if scope else len(presentation.get('overview_timestamps_s', []))
        check(bool(criterion.get('evidence_frames')) and all(type(i) is int and 1 <= i <= n for i in criterion.get('evidence_frames', [])),
              'presentation: out-of-range or absent evidence')
    speech = row.get('speech_transcript', {}).get('segments', [])
    speech_ids = {s['id'] for s in speech}
    ledger = {w['id']: w for w in presentation.get('segment_evidence', [])}
    for criterion in row.get('narration_review', {}).get('criteria', []):
        check(bool(criterion.get('speech_ids')) and set(criterion.get('speech_ids', [])) <= speech_ids,
              'spoken teaching: invalid speech citation')
        check(bool(criterion.get('window_ids')) and set(criterion.get('window_ids', [])) <= set(ledger),
              'spoken teaching: invalid window citation')
    spoken = row.get('narration_review', {})
    if spoken.get('valid') is True and 'wrong_spoken_language' not in spoken.get('failures', []):
        ratings = spoken.get('criteria', [])
        check(len(ratings) == 4 and {r['id'] for r in ratings} == set(narration.CRITERIA),
              'spoken teaching: missing or duplicate criteria')
        if ratings:
            check((min(r['score'] for r in ratings)-1)*25 == spoken.get('score'),
                  'spoken teaching: rubric arithmetic mismatch')
    for requirement in row.get('task_completion', {}).get('requirements', []):
        for citation in requirement.get('segment_citations', []):
            window = ledger.get(citation['segment_id'])
            check(window is not None, 'completion: unknown segment')
            if window:
                evidence = next((e for e in window.get('requirement_evidence', []) if e['id'] == requirement['id']), {})
                check(set(citation['frames']) <= set(evidence.get('evidence_frames', [])), 'completion: unrecorded citation')
    score = row['scoring']
    consistency = row.get('consistency_review', {})
    if consistency.get('version') == 'statement-grounded-consistency-v1':
        from eval.verified_consistency import validate as validate_consistency
        try:
            verified = validate_consistency(consistency, axes, count)
            for key in ('valid', 'conflicting_axes', 'uncertain_axes', 'source_statement_sha256'):
                check(consistency.get(key) == verified[key], 'consistency: statement or validity mismatch')
        except (ValueError, KeyError, TypeError) as exc:
            errors.append('consistency: ' + str(exc))
    if score.get('valid') is True:
        check(consistency.get('valid') is True, 'accepted total lacks verified report consistency')
        check(row.get('task_completion', {}).get('valid') is True, 'accepted total lacks verified task completion')
        flat = {k: v.get('score') for k, v in axes.items()}
        expected = benchmark_scoring.score_case(flat, narration_required=row.get('narration_required', False),
                    narration_detected=row.get('narration', {}).get('detected'), defects=row.get('defects', []))
        expected = instructional_video.apply(expected, presentation)
        if row.get('narration_required'):
            expected = narration.apply(expected, row.get('narration_review', {}))
        check(expected.get('valid') is True, 'total accepted without required evidence')
        check(benchmark_scoring.valid_score(score.get('score')), 'invalid total number')
        check(expected.get('score') is not None and math.isclose(expected['score'], score['score'], abs_tol=.0001), 'total arithmetic mismatch')
    else:
        check(score.get('score') is None, 'invalid evaluation has numeric total')
    return {'id': row['id'], 'status': 'scored' if score.get('valid') else 'evaluation_failed', 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--prompts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = unique_by_id(read_jsonl(args.results), latest=True)
    wanted = unique_by_id(read_jsonl(args.prompts))
    reports = [audit(row) for row in rows.values()]
    passed = set(rows) == set(wanted) and all(not r['errors'] for r in reports)
    result = {'passed': passed, 'scope': 'structural_citations_provenance_and_arithmetic_not_independent_semantic_validation',
              'missing_ids': sorted(set(wanted)-set(rows)), 'unexpected_ids': sorted(set(rows)-set(wanted)), 'cases': reports}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
