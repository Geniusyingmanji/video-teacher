"""Check literal judge statements, separately from the quality of the video."""
import hashlib

from eval import benchmark_scoring
from eval.evidence_prompt import prompt_json
from eval.frame_extractor import frames_as_multimodal_content
from eval.instructional_video import _ask
from eval.judges.structured_json import response_format, obj, frame_indices

VERSION = 'statement-grounded-consistency-v1'
STATUSES = ('agrees', 'non_material', 'conflict', 'uncertain')


def source_statements(axes):
    statements = {}
    for name in benchmark_scoring.VIDEO_AXES + benchmark_scoring.TEACHING_AXES:
        axis = axes.get(name, {})
        rows = {}
        if isinstance(axis.get('summary'), str) and axis['summary'].strip():
            rows['summary'] = axis['summary']
        for criterion in axis.get('criteria', []):
            key = criterion['id']
            if key in rows or not isinstance(criterion.get('finding'), str) or not criterion['finding'].strip():
                raise ValueError('missing or duplicate report statement')
            rows[key] = criterion['finding']
        if not rows or axis.get('error'):
            raise ValueError('cannot verify missing axis report: ' + name)
        statements[name] = rows
    return statements


def validate(raw, axes, count):
    statements = source_statements(axes)
    checked = raw.get('axes')
    if not isinstance(checked, dict) or set(checked) != set(statements):
        raise ValueError('every axis report must be checked')
    results = {}; conflicts = []; uncertain = []
    for axis, records in statements.items():
        if not isinstance(checked[axis], dict) or set(checked[axis]) != set(records):
            raise ValueError('every literal report statement must be checked')
        results[axis] = {}
        for key, statement in records.items():
            row = checked[axis][key]
            if row.get('status') not in STATUSES:
                raise ValueError('invalid statement consistency status')
            if row.get('report_statement', statement) != statement:
                raise ValueError('report statement was changed')
            if not isinstance(row.get('observed'), str) or not row['observed'].strip():
                raise ValueError('actual observation or materiality finding required')
            refs = row.get('evidence_frames')
            if (not isinstance(refs, list) or any(type(i) is not int or not 1 <= i <= count for i in refs)
                    or row['status'] in ('agrees', 'conflict') and not refs):
                raise ValueError('conclusive factual checks require actual frame references')
            results[axis][key] = {**row, 'report_statement': statement}
        statuses = {r['status'] for r in results[axis].values()}
        if 'conflict' in statuses: conflicts.append(axis)
        if 'uncertain' in statuses: uncertain.append(axis)
    return {'version': VERSION, 'valid': not conflicts and not uncertain,
            'conflicting_axes': conflicts, 'uncertain_axes': uncertain, 'axes': results,
            'source_statement_sha256': hashlib.sha256(prompt_json(statements).encode()).hexdigest(),
            'finding': 'Report factual consistency checked against actual frames; video quality is assessed separately.'}


def review(case, axes, frames, observations):
    statements = source_statements(axes)
    item = obj({'status': {'type': 'string', 'enum': list(STATUSES)},
                'observed': {'type': 'string', 'minLength': 1, 'maxLength': 240},
                'evidence_frames': frame_indices(len(frames))})
    schema = response_format('literal_report_consistency', {
        'axes': obj({axis: obj({key: item for key in rows}) for axis, rows in statements.items()})})
    prompt = ('Check EVERY supplied REPORT STATEMENT against the actual images. This is a check of '
        'judge reports, NOT whether the video is correct or good. Reports can accurately describe a '
        'bad video. If a report correctly says the array is broken or the answer is wrong, that report '
        'AGREES with the faulty video. A contradiction inside the VIDEO (caption says sorted while '
        'array is broken) is NOT a contradiction between judge reports and frames when reports '
        'explicitly describe that defect. Never flag an accurate negative report because the video '
        'fails its task. Do not compare the reports to an ideal successful video. '
        'agrees: material factual statement matches actual frames; conflict: statement makes a '
        'material false factual assertion about the answer, object identity/location or action; '
        'uncertain: those facts cannot be verified; non_material: quality opinion, subjective '
        'judgment or a minor wording issue that does not change the factual task/answer assessment. '
        'Material wrong answers, missing objects or false completion claims cannot be non_material. '
        'Cite actual overview image indices for agrees/conflict. Explain the actual visible state '
        'concisely (at most 20 words), referencing the exact keyed report statement. Numerical '
        'scores are withheld and must not be generated or targeted. Shared observations are '
        'fallible; the actual images are the authority. Actual-track ASR supplies fallible speech '
        'text evidence, not direct listening or pronunciation certification.\n' + prompt_json({
            'task': case.get('prompt_text'), 'report_statements': statements,
            'shared_observations': observations.get('observations', []),
            'actual_spoken_segments': case.get('actual_spoken_segments', [])}))
    return _ask([{'role': 'user', 'content': frames_as_multimodal_content(frames, prompt)}],
                schema, lambda raw: validate(raw, axes, len(frames)), tokens=6000)
