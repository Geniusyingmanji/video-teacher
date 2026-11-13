"""Visual feedback, bounded program edits, and cross-task advice memory.

Generation feedback uses public tasks and rendered evidence. The final comparison
is separate, sees only encoded videos, and never supplies private answer keys.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import copy
import json
import math
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from .client import MatrixClient
from .common import ROOT, digest, parse_json, public_case, read_jsonl, write_json
from .pipeline import encode
from .provenance import file_hash, freeze_run
from .refine import apply_diagrams
from .rerender import decoded_audio_hash, diagram_only_plan
from .scene import FPS, PLAN_SYSTEM, inspect_layout, render_frame, validate_plan

VERSION = 'localbench-visual-agent-visibility-guard-v5'
GROUPS = {'content', 'organization', 'expression', 'video'}
CRITIC_SYSTEM = '''Review an educational-video VISUAL PROGRAM using its public task,
authored narration, and timestamped rendered evidence. The authored narration is an
intended script, not a transcription. Do not evaluate actual audio quality from it.
Separate content (incorrect/missing visual knowledge), organization (sequence),
expression (instructional diagrams and visual/text correspondence), and video
(readability/layout). Inspect object relationships, not just titles or captions.
Return JSON {issues:[{id,group,scene,evidence_ids,observation,requested_change,
visual_edit_sufficient}],summary}. At most 8 issues. scene is a zero-based index.
Only use evidence IDs actually supplied. visual_edit_sufficient is a boolean:
false when narration, timing or captions must change. Preserve correct content.
Distinguish an incorrect drawn relationship from an intentional schematic.
Never demand decoration, photorealism, or animation absent from the public task.
For a numeric plot infer the represented quantity before judging trend or axes;
a title about summation does not require every plot to show a cumulative sum.
Optional generated_stroke_hints identify intersections predicted by the code at
the supplied frame's progress. They are fallible locations to inspect, not pixel
truth or mandatory defects. Confirm the actual supplied image and cite its ID;
ignore intentional or invisible crossings. Do not infer absent issues from an
empty hints list. A glyph crossing is a layout issue, not a conceptual error.
Return no issues if the evidence does not establish a concrete defect.
Even when there are no issues, return the OBJECT {"issues":[],"summary":"No concrete defect established"}.
Never return a bare array, null, or omit the issues field.
This is generation feedback, not a certified benchmark score.'''

MEMORY_SYSTEM = '''Distill reusable visual-program repair advice from ONE observed
development episode. You see public task, grounded before/after observations and
validated program edits. Return JSON {rules:[{id,group,trigger,action,evidence_issue_ids}]}.
At most 4 rules, each trigger <=160 characters and action <=450 characters.
Use group content/organization/expression/video. Include only issue IDs supported
by the source review. Generalize the operation; omit task-specific numbers, answers,
case IDs and final-video scores. Preserve uncertainty: a critique is fallible.
Rules guide later tasks when their trigger applies. Do not invent new tools or
claim performance improvements. No executable code or filesystem paths.
An empty rules list is permitted when no transferable lesson is supported.'''

BLIND_SYSTEM = '''Compare two anonymized final encoded educational videos, A and B.
You receive the public task and actual frames at matched times. Judge visual
knowledge correctness, coverage of requested visual demonstrations, explanatory
usefulness, and readability. Return JSON {winner:"A"|"B"|"tie"|"uncertain",
dimensions:{visual_correctness:{A:1..5,B:1..5,evidence_ids:[...],reason},
visual_coverage:{A:1..5,B:1..5,evidence_ids:[...],reason},
visual_explanation:{A:1..5,B:1..5,evidence_ids:[...],reason},
readability:{A:1..5,B:1..5,evidence_ids:[...],reason}},remaining_issues:[...] }.
Ground every dimension in supplied image IDs from both videos. Do not infer actual
speech, smooth motion, or student learning from sparse frames. Diagram simplicity
is not a defect; inspect relationships against the public task. Both videos have
identical decoded audio and timing; no claim about audio improvement is possible.
Do not prefer color count, visual density or a particular rendering medium.
This is a fallible visual-only pilot comparison, not the full benchmark protocol.'''


def images_content(records):
    parts = []
    for r in records:
        parts.extend([{'type': 'text', 'text': f"{r['id']} scene {r['scene']} at {r['time_s']:.3f}s"},
                      {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,'+
                       base64.b64encode(Path(r['path']).read_bytes()).decode()}}])
    return parts


def times_for(plan):
    start = 0.
    records = []
    for i, scene in enumerate(plan['scenes']):
        for f in (.25, .85):
            records.append({'scene': i, 'progress': f, 'time_s': start+f*scene['duration_s']})
        start += scene['duration_s']
    return records


def evidence(plan, out, *, video=None, prefix='F'):
    out.mkdir(parents=True, exist_ok=True)
    records = times_for(plan)
    if video:
        reader = imageio_ffmpeg.read_frames(str(video), pix_fmt='rgb24')
        metadata = next(reader)
        indices = {round(r['time_s']*metadata['fps']): i for i, r in enumerate(records)}
        found = {}
        for frame_id, raw in enumerate(reader):
            if frame_id in indices:
                found[indices[frame_id]] = Image.frombytes('RGB', metadata['size'], raw)
        if len(found) != len(records):
            raise ValueError('not all requested final-video frames decoded')
    for j, r in enumerate(records):
        im = found[j] if video else render_frame(plan['scenes'][r['scene']], r['progress'],
                      index=r['scene'], total=len(plan['scenes']), mode='code')[0]
        path = out/f'{prefix}{j:02d}.jpg'
        im.save(path, quality=90)
        r.update(id=f'{prefix}{j:02d}', path=str(path.resolve()), sha256=file_hash(path),
                 source='final_encoded_video' if video else 'generation_preview')
    write_json(out/'frames.json', records)
    return records


def validate_feedback(raw, records, scene_count):
    raw = copy.deepcopy(raw)
    if not isinstance(raw, dict) or not isinstance(raw.get('issues'), list) or len(raw['issues']) > 8:
        raise ValueError('bounded issue list required')
    valid_ids = {r['id'] for r in records}
    ids = set()
    for issue in raw['issues']:
        if not isinstance(issue, dict) or issue.get('group') not in GROUPS:
            raise ValueError('invalid feedback group')
        # JSON models sometimes return integer IDs; preserve their identity as strings.
        if type(issue.get('id')) is int:
            issue['id'] = str(issue['id'])
        if not isinstance(issue.get('id'), str) or not issue['id'] or issue['id'] in ids:
            raise ValueError('unique issue ID required')
        ids.add(issue['id'])
        if type(issue.get('scene')) is not int or not 0 <= issue['scene'] < scene_count:
            raise ValueError('feedback scene outside lesson')
        refs = issue.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(x not in valid_ids for x in refs):
            raise ValueError('feedback lacks existing evidence IDs')
        if type(issue.get('visual_edit_sufficient')) is not bool:
            raise ValueError('feedback must separate visual and nonvisual changes')
        if any(not isinstance(issue.get(k), str) or not issue[k].strip() for k in ('observation', 'requested_change')):
            raise ValueError('concrete observations and requested changes required')
    return raw


def stroke_hints(plan, records):
    from .stroke_preflight import inspect_strokes
    hints = []
    for record in records:
        for finding in inspect_strokes(plan['scenes'][record['scene']], record['progress']):
            hints.append({'scene': record['scene'], 'progress': record['progress'],
                          'candidate_evidence_id': record['id'], **finding})
    return hints


def review(client, case, plan, records, out, purpose, *, include_stroke_hints=True):
    text = {'public_task': public_case(case), 'authored_scenes': [
        {k: s[k] for k in ('title', 'caption', 'narration', 'duration_s')} for s in plan['scenes']]}
    if include_stroke_hints:
        text['generated_stroke_hints'] = stroke_hints(plan, records)
    messages = [{'role': 'system', 'content': CRITIC_SYSTEM},
                {'role': 'user', 'content': [{'type': 'text', 'text': json.dumps(text)}]+images_content(records)}]
    for attempt in range(2):
        result = client.chat(messages, purpose=purpose, max_tokens=3500)
        write_json(out.with_name(out.stem+f'_raw_{attempt}.json'), result)
        try:
            validated = validate_feedback(result, records, len(plan['scenes']))
            write_json(out, validated)
            return validated
        except (ValueError, TypeError, KeyError) as exc:
            if attempt == 1:
                raise
            messages += [{'role': 'assistant', 'content': json.dumps(result)},
                         {'role': 'user', 'content': 'Correct this schema/evidence error: '+str(exc)+
                          '. Return an object with issues and summary. If no concrete issues were found, use '
                          '{"issues":[],"summary":"No concrete defect established"}; do not invent an issue to satisfy the format.'}]


def validate_memory(raw, feedback):
    if not isinstance(raw, dict) or set(raw) != {'rules'} or not isinstance(raw['rules'], list) or len(raw['rules']) > 4:
        raise ValueError('bounded advice memory required')
    source_ids = {x['id'] for x in feedback['issues']}
    seen = set()
    for rule in raw['rules']:
        if set(rule) != {'id', 'group', 'trigger', 'action', 'evidence_issue_ids'} or rule['group'] not in GROUPS:
            raise ValueError('invalid memory schema')
        if not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in seen:
            raise ValueError('memory rule IDs must be unique')
        seen.add(rule['id'])
        for key, limit in [('trigger', 160), ('action', 450)]:
            if not isinstance(rule[key], str) or not 1 <= len(rule[key]) <= limit:
                raise ValueError('memory rule text exceeds bounds')
        if not isinstance(rule['evidence_issue_ids'], list) or not rule['evidence_issue_ids'] or any(x not in source_ids for x in rule['evidence_issue_ids']):
            raise ValueError('memory rules must cite source episode issues')
    return raw


def distill_memory(client, body, feedback, out):
    body = {**body, 'allowed_evidence_issue_ids': [x['id'] for x in feedback['issues']]}
    messages = [{'role': 'system', 'content': MEMORY_SYSTEM + '\nOnly cite allowed_evidence_issue_ids from the BEFORE review. After-review opinions are diagnostic context, not additional source issues.'},
                {'role': 'user', 'content': json.dumps(body, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'visual_agent_memory_distillation:{attempt}', max_tokens=2200)
        write_json(out/f'memory_raw_{attempt}.json', raw)
        try:
            return validate_memory(raw, feedback)
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out/f'memory_error_{attempt}.json', {'error': str(exc)})
            if attempt == 1:
                raise
            messages += [{'role': 'assistant', 'content': json.dumps(raw)},
                         {'role': 'user', 'content': 'Correct this validation failure without inventing or remapping evidence: '+str(exc)}]


def patch(client, case, original, feedback, memory, records, out, purpose, *, program_guard=True, visibility_guard=True, direction_contract=None):
    system = PLAN_SYSTEM+'''
For THIS call return ONLY JSON {replacements:[{scene,primitives}]}.
Repair visible knowledge relationships or teaching diagrams identified by the
grounded feedback. Change only primitives in selected scenes; preserve all titles,
narration, captions, durations, and all other fields. Inspect actual supplied images
against the public task. Feedback and remembered advice may be wrong: verify them.
Use chart for numeric data relationships, flow_path for qualitative directed spirals,
and ordinary documented primitives for other diagrams. Their documented schemas
remain exact. Do not insert source_visual, state_visual, local paths or Python code.
Keep already-correct scenes. A label claiming a relation does not depict it.
Do not impose cumulative-sum axes on a plot illustrating individual discounted terms.
Apply memory rules only when their trigger matches the current task. They are advice,
not extra task requirements or answers. When narration is wrong, report that through
the reviewer; visual-only changes cannot silently fix it. Return an empty replacements
list when no safe visual change is warranted.
Apply replacements to current_plan. On retries, retain its earlier repairs and
address the remaining schema/layout error, including a newly identified scene
when necessary. The supplied frames describe current_plan; retry frames are
generation previews, not a newly encoded video. A valid layout does not certify
scientific correctness. Do not change a correct relationship to satisfy a mistaken
critique; always check the public task and actual representation.'''
    attempts = []
    current = copy.deepcopy(original)
    current_records = records
    previous_error = None
    for attempt in range(3):
        body = {'public_task': public_case(case), 'original_plan': original,
                'current_plan': current, 'generation_feedback': feedback,
                'advice_memory': memory,
                'frame_source': 'current_candidate_preview' if current != original else 'original_evidence'}
        if previous_error:
            body['previous_schema_or_layout_error'] = previous_error
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': [
            {'type': 'text', 'text': json.dumps(body, ensure_ascii=False)}]+images_content(current_records)}]
        response = client.chat(messages, purpose=f'{purpose}:{attempt}', max_tokens=6500, json_mode=False)
        (out/f'patch_response_{attempt}.txt').write_text(response, encoding='utf-8')
        try:
            raw = parse_json(response)
            write_json(out/f'patch_{attempt}.json', raw)
            if raw == {'replacements': []} and current == original:
                return copy.deepcopy(original), attempts
            proposed = copy.deepcopy(current) if raw == {'replacements': []} else apply_diagrams(current, raw, allow_noop=True)
            if proposed == original:
                # Re-emitting identical valid primitives is the same abstention
                # as an empty patch, not a demand to invent a change on retry.
                write_json(out/'no_change.json', {'attempt': attempt,
                    'status': 'original_retained', 'reason': 'valid replacement leaves the input diagram unchanged',
                    'quality_acceptance': False, 'feedback_issues_resolved': False})
                return proposed, attempts
            diagram_only_plan(original, proposed)
            validate_plan(proposed, case)
            if direction_contract is not None:
                from .arrow_direction_guard import check as check_direction
                direction = check_direction(direction_contract, original, proposed)
                write_json(out/f'direction_check_{attempt}.json', direction)
                if direction['status'] == 'reject_reversal':
                    # Keep the rejected proposal, but do not ask the model for
                    # another mutation to evade the guard or silently render it.
                    write_json(out/f'direction_rejected_plan_{attempt}.json', proposed)
                    write_json(out/'direction_rejection.json', {'attempt': attempt,
                        'status': 'original_retained', 'receipt': direction,
                        'quality_acceptance': False, 'feedback_issues_resolved': False})
                    return copy.deepcopy(original), attempts
            if program_guard:
                from .program_consistency import inspect_plan as inspect_program, validate as validate_program
                write_json(out/f'program_consistency_{attempt}.json', inspect_program(proposed))
                validate_program(proposed, reference=original)
            if visibility_guard:
                from .stroke_visibility import regression_report,validate_no_regression
                visibility=regression_report(current,proposed)
                write_json(out/f'stroke_visibility_{attempt}.json',visibility)
                validate_no_regression(visibility)
            issues = inspect_layout(proposed)
            if issues:
                # Preserve schema-valid intermediate changes across layout retries.
                # Do not promote a malformed plan, relax the gate, or select by score.
                current = proposed
                write_json(out/f'working_plan_{attempt}.json', current)
                if attempt < 2:
                    current_records = evidence(current, out/f'retry_preview_{attempt}')
                raise ValueError('visible layout defects: '+json.dumps(issues[:10]))
            return proposed, attempts
        except (ValueError, KeyError, TypeError) as exc:
            attempts.append({'attempt': attempt, 'error': str(exc)[:1800]})
            write_json(out/'patch_errors.json', attempts)
            if attempt == 2:
                raise
            previous_error = str(exc)[:1800]


def load_case_source(case, run):
    manifest = json.loads((run/'manifest.json').read_text())
    record = next(r for r in manifest['cases'] if r['id'] == case['id'])
    artifact = next(a for a in record['artifacts'] if a['mode'] == 'code' and a['complete'])
    if file_hash(artifact['video_path']) != artifact['sha256'] or record['public_input_hash'] != digest(public_case(case)):
        raise ValueError('source video/public task identity mismatch')
    plan = json.loads((Path(artifact['video_path']).parent/'plan.json').read_text())
    if any(s.get('state_visual') or s.get('source_visual') for s in plan['scenes']):
        raise ValueError('this pilot edits general visual programs only')
    return plan, artifact


def run_variant(client, case, original, artifact, feedback, records, memory, out, label, *, program_guard=True, visibility_guard=True, direction_contract=None):
    out.mkdir(parents=True, exist_ok=True)
    result = {'id': case['id'], 'variant': label, 'memory': memory,
              'private_reference_used': False, 'artifact': None}
    try:
        proposed, attempts = patch(client, case, original, feedback, memory, records, out,
                                   f'visual_agent_patch:{case["id"]}:{label}', program_guard=program_guard,
                                   visibility_guard=visibility_guard, direction_contract=direction_contract)
        if (out/'direction_rejection.json').exists():
            result['direction_guard'] = json.loads((out/'direction_rejection.json').read_text())
        write_json(out/'plan.json', proposed)
        preview = evidence(proposed, out/'preview')
        # This review is diagnostic. Its response-format failure must not select
        # which otherwise valid candidate gets rendered.
        try:
            after = review(client, case, proposed, preview, out/'feedback_after.json',
                           f'visual_agent_recheck:{case["id"]}:{label}')
        except Exception as exc:
            after = None
            result['feedback_after_error'] = f'{type(exc).__name__}: {str(exc)[:1800]}'
        result['feedback_after'] = after
        result['patch_errors'] = attempts
        if proposed == original:
            result.update(status='no_change', artifact=artifact, changed_scenes=[])
        else:
            _, changed = diagram_only_plan(original, proposed)
            new_artifact = encode(proposed, out, artifact['video_path'], mode='code', copy_audio=True)
            before_audio, after_audio = decoded_audio_hash(artifact['video_path']), decoded_audio_hash(new_artifact['video_path'])
            if before_audio != after_audio:
                raise ValueError('decoded audio changed')
            result.update(status='rendered', artifact=new_artifact, changed_scenes=changed,
                          decoded_audio_identical=True, source_audio_hash=before_audio,
                          output_audio_hash=after_audio,
                          generation_feedback_status='diagnostic_only; all renderable candidates retained without score-based selection')
        result['frames'] = evidence(proposed, out/'final_frames', video=result['artifact']['video_path'])
    except Exception as exc:
        result.update(status='failed', error=f'{type(exc).__name__}: {str(exc)[:1800]}')
    write_json(out/'result.json', result)
    print(case['id'], label, result['status'], flush=True)
    return result


def validate_blind(raw, refs):
    if not isinstance(raw, dict) or raw.get('winner') not in {'A', 'B', 'tie', 'uncertain'}:
        raise ValueError('invalid blind comparison')
    dims = raw.get('dimensions')
    required = {'visual_correctness', 'visual_coverage', 'visual_explanation', 'readability'}
    if not isinstance(dims, dict) or set(dims) != required:
        raise ValueError('blind comparison dimensions mismatch')
    for value in dims.values():
        if any(type(value.get(k)) is not int or not 1 <= value[k] <= 5 for k in ('A', 'B')):
            raise ValueError('invalid blind dimension score')
        cited = value.get('evidence_ids')
        if not isinstance(cited, list) or any(x not in refs for x in cited) or not any(x.startswith('A') for x in cited) or not any(x.startswith('B') for x in cited):
            raise ValueError('blind comparison needs real evidence from both videos')
        if not isinstance(value.get('reason'), str) or not value['reason'].strip():
            raise ValueError('blind comparison reason required')
    return raw


def compare(client, case, original, left, right, out, label):
    out.mkdir(parents=True, exist_ok=True)
    # Deterministic label swapping, hidden from judge. No generator metadata passed.
    swap = int(digest({'id': case['id'], 'comparison': label})[:2], 16) % 2 == 1
    ordered = [right, left] if swap else [left, right]
    records = []
    for slot, art in zip(('A', 'B'), ordered):
        records += evidence(original, out/slot, video=art['video_path'], prefix=slot)
    messages = [{'role': 'system', 'content': BLIND_SYSTEM}, {'role': 'user', 'content': [
        {'type': 'text', 'text': json.dumps(public_case(case), ensure_ascii=False)}]+images_content(records)}]
    for attempt in range(2):
        result = client.chat(messages, purpose=f'visual_agent_blind:{case["id"]}:{label}:{attempt}', max_tokens=3500)
        write_json(out/f'raw_{attempt}.json', result)
        try:
            validate_blind(result, {r['id'] for r in records})
            break
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out/f'validation_error_{attempt}.json', {'error': str(exc)})
            if attempt == 1:
                raise
            messages += [{'role': 'assistant', 'content': json.dumps(result)},
                         {'role': 'user', 'content': 'Correct the evidence/schema failure. Reinspect the supplied images; do not invent citations. '+str(exc)}]
    winner = result['winner']
    result.update(label=label, swap=swap, left_sha256=left['sha256'], right_sha256=right['sha256'],
                  interpreted_winner=('right' if (winner == 'A') == swap else 'left') if winner in {'A', 'B'} else winner)
    write_json(out/'comparison.json', result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error('use a fresh output directory')
    config = json.loads(args.config.read_text())
    rows = {r['id']: r for r in read_jsonl(ROOT/'data/tasks.jsonl')}
    selections = [config['seed'], *config['transfer']]
    if len({x['id'] for x in selections}) != len(selections):
        p.error('seed and transfer case IDs must be disjoint')
    sources = {x['id']: load_case_source(rows[x['id']], ROOT/x['source_run']) for x in selections}
    freeze_run(args.out, {**config, 'version': VERSION, 'entrypoint': 'visual_agent',
                          'inputs': {k: {'public_hash': digest(public_case(rows[k])), 'video_hash': v[1]['sha256'],
                                         'plan_hash': digest(v[0])} for k, v in sources.items()}})
    client = MatrixClient(args.out, model=config['model'], concurrency=4,
                          max_calls=config['max_calls'], max_tokens_total=config['max_tokens'],
                          cache_sources=[ROOT/x for x in config.get('cache_sources', [])])
    summary = {'version': VERSION, 'scope': config['scope'], 'seed': None, 'transfer': [], 'comparisons': []}
    def initial(id_):
        case = rows[id_];plan, artifact = sources[id_]
        out = args.out/id_;out.mkdir(parents=True)
        write_json(out/'public_input.json', public_case(case))
        write_json(out/'original_plan.json', plan)
        records = evidence(plan, out/'original_frames', video=artifact['video_path'])
        feedback = review(client, case, plan, records, out/'feedback_before.json', f'visual_agent_critic:{id_}')
        return case, plan, artifact, records, feedback, out
    seed = config['seed']['id']
    case, plan, artifact, records, feedback, out = initial(seed)
    result = run_variant(client, case, plan, artifact, feedback, records, {'rules': []}, out/'feedback_only', 'feedback_only')
    summary['seed'] = result
    memory = {'rules': []}
    if result['status'] == 'rendered':
        body = {'public_task': public_case(case), 'before_feedback': feedback,
                'after_feedback': result['feedback_after'], 'original_plan': plan,
                'revised_plan': json.loads((out/'feedback_only/plan.json').read_text())}
        memory = distill_memory(client, body, feedback, args.out)
    write_json(args.out/'memory.json', {'source_case': seed, 'rules': memory['rules'],
                                      'status': 'candidate_advice; transfer outcomes pending',
                                      'no_weight_updates': True, 'harness_code_evolved': False})
    write_json(args.out/'summary.json', summary)
    def transfer(selection):
        id_ = selection['id']
        case, plan, artifact, records, feedback, out = initial(id_)
        variants = []
        for label, advice in [('feedback_only', {'rules': []}), ('feedback_memory', memory)]:
            variants.append(run_variant(client, case, plan, artifact, feedback, records, advice, out/label, label))
        return {'id': id_, 'variants': variants}
    # Two case workers cap simultaneous local renders at two; one shared API semaphore.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(transfer, x): x['id'] for x in config['transfer']}
        for future in concurrent.futures.as_completed(futures):
            try:
                summary['transfer'].append(future.result())
            except Exception as exc:
                summary['transfer'].append({'id': futures[future], 'status': 'failed', 'error': str(exc)[:1800]})
            write_json(args.out/'summary.json', summary)
    comparisons = []
    if result.get('artifact'):
        comparisons.append((seed, 'original_vs_feedback', artifact, result['artifact']))
    for item in summary['transfer']:
        variants = item.get('variants', [])
        valid = {v['variant']: v['artifact'] for v in variants if v.get('artifact')}
        for label, art in valid.items():
            comparisons.append((item['id'], 'original_vs_'+label, sources[item['id']][1], art))
        if len(valid) == 2:
            comparisons.append((item['id'], 'feedback_vs_memory', valid['feedback_only'], valid['feedback_memory']))
    for id_, label, left, right in comparisons:
        try:
            r = compare(client, rows[id_], sources[id_][0], left, right, args.out/id_/'comparisons'/label, label)
            summary['comparisons'].append({'id': id_, **r})
        except Exception as exc:
            summary['comparisons'].append({'id': id_, 'label': label, 'status': 'failed', 'error': str(exc)[:1800]})
        write_json(args.out/'summary.json', summary)
    print('visual-agent pilot complete', flush=True)


if __name__ == '__main__':
    main()
