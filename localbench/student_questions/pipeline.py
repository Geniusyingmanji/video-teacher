"""Prefix-only questioning, frozen eligibility/pool, then full-media assessment."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from localbench.common import digest, write_json
from localbench.student import prefix, validate_profiles
from . import VERSION
from .protocol import (question_messages, gate_messages, pool_messages, assess_messages,
                       validate_questions, validate_gate, validate_pool, validate_assessment,
                       reference_map, call, pool_audit_messages, validate_pool_audit)


def saved_input(destination, name, messages):
    # Media pixels are retained in the shared evidence directory; store the exact
    # text envelope, IDs and timestamps without duplicating base64 media.
    write_json(destination/f'{name}_input.json', json.loads(messages[1]['content'][0]['text']))


def run_profile(profile, evidence, references, out, student, reviewer, fractions, *, track_answers=False):
    out = Path(out)
    previous, records = [], []
    own_questions, own_answers, trajectory = {}, {}, []
    if track_answers:
        from .trajectory import answer_at
    for i, fraction in enumerate(fractions):
        observation = prefix(evidence, evidence['duration_s'] * fraction)
        destination = out/f'prefix_{i:02d}'
        record = {'fraction': fraction, 'cutoff_s': observation['cutoff_s'], 'status': 'student_error'}
        try:
            if track_answers and own_questions:
                update = answer_at(student, profile, observation, own_questions, own_answers,
                                   destination/'answers')
                trajectory.append(update)
                # Failed updates stay absent. Older accepted state remains explicitly historical.
                own_answers.update(update['answers'])
            request = question_messages(profile, observation, previous,
                                        own_answers=own_answers if track_answers else None)
            saved_input(destination, 'student', request)
            response = call(student, request, lambda r: validate_questions(r, observation),
                            destination, 'student', preserve=True, max_tokens=2400)
            questions = {f'{profile["id"]}.P{i}.Q{j}': {**q, 'profile_id': profile['id'],
                         'fraction': fraction, 'cutoff_s': observation['cutoff_s']}
                         for j, q in enumerate(response['questions'])}
            record.update(status='eligibility_error', questions=questions)
            # Only the student's own questions can feed the next prefix.
            previous.extend(response['questions'])
            own_questions.update(questions)
            if questions:
                request = gate_messages(questions, profile, observation, references)
                saved_input(destination, 'eligibility', request)
                gate = call(reviewer, request, lambda r: validate_gate(r, questions, observation, profile),
                            destination, 'eligibility', max_tokens=3000)
            else:
                gate = {'items': {}}
            record.update(status='complete', eligibility=gate['items'])
        except Exception as exc:
            record['error'] = str(exc)[:700]
        records.append(record)
        write_json(destination/'result.json', record)
        if record['status'] == 'student_error':
            break  # no fabricated learner-state continuation after a failure
    result = {'profile_id': profile['id'], 'planned_prefixes': len(fractions), 'prefixes': records,
              'status': 'complete' if len(records) == len(fractions) and all(r['status'] == 'complete' for r in records) else 'incomplete'}
    if track_answers:
        final = answer_at(student, profile, prefix(evidence, evidence['duration_s']),
                          own_questions, own_answers, out/'final_answers')
        trajectory.append(final)
        result.update(trajectory=trajectory,
                      trajectory_complete=result['status'] == 'complete' and all(r['status'] == 'complete' for r in trajectory))
    write_json(out/'session.json', result)
    return result


def assessment_summary(assessment, pool, sessions):
    rows = assessment.get('groups', {}) if assessment else {}
    scored = [r['score'] for r in rows.values() if r['status'] == 'scored']
    complete_profiles = sum(s['status'] == 'complete' for s in sessions)
    all_valid = bool(pool) and len(scored) == len(pool) and complete_profiles == len(sessions)
    conditional = (sum(scored)/len(scored)-1)*25 if scored else None
    return {'planned_profiles': len(sessions), 'complete_profiles': complete_profiles,
            'planned_prefixes': sum(s['planned_prefixes'] for s in sessions),
            'complete_prefixes': sum(r['status'] == 'complete' for s in sessions for r in s['prefixes']),
            'question_groups': len(pool), 'scored_groups': len(scored),
            'unscored_groups': len(pool) - len(scored),
            'specific_score': conditional if all_valid else None,
            'mean_among_scored_groups': conditional,
            'score_coverage': len(scored)/len(pool) if pool else None,
            'questioning_complete': complete_profiles == len(sessions),
            'scope': 'Draft model assessment of video answers to prefix-generated questions; not learner performance or learning gain. Conditional mean is not a full score.'}


def assess_frozen(pool, questions, observation, references, out, reviewer, *, batch_size=4):
    """Score every independent batch; retain errors without aborting later groups."""
    result, errors = {'groups': {}}, []
    from .protocol import unverified_group
    for key, group in pool.items():
        if group['reference_status'] == 'insufficient':
            result['groups'][key] = unverified_group(group, 'Frozen reference targets are insufficient; no model score requested.')
    keys = [k for k in pool if k not in result['groups']]
    for i in range(0, len(keys), batch_size):
        subset = {k: pool[k] for k in keys[i:i+batch_size]}
        destination = Path(out)/f'batch_{i//batch_size:02d}'
        request = assess_messages(subset, questions, observation, references)
        saved_input(destination, 'assessment', request)
        try:
            rows = call(reviewer, request, lambda r: validate_assessment(r, subset, observation),
                        destination, 'assessment', max_tokens=6500)
            result['groups'].update(rows['groups'])
        except Exception as exc:
            failure = {'group_ids': list(subset), 'error': str(exc)[:700]}
            errors.append(failure)
            write_json(destination/'failure.json', failure)
    write_json(Path(out)/'result.json', {'assessment': result, 'batch_errors': errors})
    return result, errors


def run(case, profiles, knowledge_pack, evidence, out, student, reviewer, *, fractions=(.25, .5, .75), track_answers=False):
    profiles = validate_profiles(profiles)
    if not fractions or any(type(f) not in (int, float) or not 0 < f < 1 for f in fractions) or sorted(set(fractions)) != list(fractions):
        raise ValueError('distinct increasing prefix fractions within0..1 required')
    out = Path(out)
    references = reference_map(case, knowledge_pack)
    binding = {'version': VERSION, 'case_id': case['id'], 'video_sha256': evidence['video_sha256'],
               'case_hash': digest(case), 'profiles_hash': digest(profiles),
               'references_hash': digest(references), 'fractions': list(fractions)}
    if track_answers:
        from . import trajectory
        binding['trajectory_version'] = trajectory.VERSION
    write_json(out/'protocol_binding.json', binding)
    with ThreadPoolExecutor(max_workers=2) as executor:
        sessions = list(executor.map(lambda p: run_profile(p, evidence, references, out/'profiles'/p['id'], student, reviewer, fractions,
                                                         track_answers=track_answers), profiles))
    questions = {qid: q for s in sessions for p in s['prefixes'] for qid, q in p.get('questions', {}).items()}
    eligibility = {qid: e for s in sessions for p in s['prefixes'] for qid, e in p.get('eligibility', {}).items()}
    profile_map = {p['id']: p for p in profiles}
    eligible = {k: {**q, 'profile': profile_map[q['profile_id']], 'eligibility': eligibility[k]}
                for k, q in questions.items() if eligibility.get(k, {}).get('status') == 'eligible'}
    # Freeze all original questions and eligibility BEFORE full-video assessment.
    write_json(out/'eligibility_frozen.json', {'at': datetime.now(timezone.utc).isoformat(),
        'questions': questions, 'eligibility': eligibility, 'eligible_ids': list(eligible),
        'questioning_statuses': {s['profile_id']: s['status'] for s in sessions}})
    pool, assessment, error, pool_errors = {}, None, None, []
    if eligible:
        try:
            # Bounded batches avoid response truncation as original questions grow.
            keys = list(eligible)
            for i in range(0, len(keys), 6):
                subset = {k: eligible[k] for k in keys[i:i+6]}
                destination = out/'pool'/f'batch_{i//6:02d}'
                request = pool_messages(subset, references)
                saved_input(destination, 'pool', request)
                try:
                    groups = call(reviewer, request, lambda r: validate_pool(r, subset, references), destination, 'pool', max_tokens=6500)
                except Exception as exc:
                    from .pool_recovery import recover_batch
                    records = sorted(destination.glob('pool_normalization_*.json'))
                    saved = json.loads(records[-1].read_text())['normalized_response'] if records else None
                    groups, receipt = recover_batch(saved, subset, references)
                    failure = {'question_ids': list(subset), 'error': str(exc)[:700]}
                    pool_errors.append(failure)
                    write_json(destination/'recovery.json', {'failure': failure, 'groups': groups, 'receipt': receipt})
                for group in groups.values():
                    pool[f'S{len(pool)+1:02d}'] = group
            write_json(out/'question_pool_draft.json', pool)
            request = pool_audit_messages(pool, eligible, references)
            saved_input(out/'pool_audit', 'audit', request)
            audit = call(reviewer, request, lambda r: validate_pool_audit(r, pool), out/'pool_audit', 'audit', max_tokens=6500)
            for k, verdict in audit['groups'].items():
                pool[k]['semantic_audit'] = verdict
                if verdict['status'] != 'approved':
                    pool[k]['reference_status'] = 'insufficient'
            write_json(out/'question_pool_frozen.json', {'at': datetime.now(timezone.utc).isoformat(),
                       'groups': pool, 'references': references, 'pool_hash': digest(pool)})
            observation = prefix(evidence, evidence['duration_s'])
            assessment, errors = assess_frozen(pool, eligible, observation, references, out/'assessment', reviewer)
            if errors:
                error = json.dumps(errors, ensure_ascii=False)
        except Exception as exc:
            error = str(exc)[:700]
    summary = assessment_summary(assessment, pool, sessions)
    summary.update(original_questions=len(questions), eligible_questions=len(eligible),
                   eligibility_counts=dict(Counter(e['status'] for e in eligibility.values())))
    result = {**binding, 'status': 'complete' if summary['specific_score'] is not None else 'incomplete',
              'sessions': sessions, 'question_pool': pool, 'assessment': assessment,
              'summary': summary, 'error': error, 'pool_errors': pool_errors}
    if track_answers:
        # Only score against a successfully frozen pool, never a partial builder output.
        frozen_pool = pool if (out/'question_pool_frozen.json').exists() else {}
        result['student_answers'] = trajectory.assess(frozen_pool, eligible, prefix(evidence, evidence['duration_s']),
                                                      references, sessions, out/'student_answers', reviewer)
        if result['student_answers']['summary']['supported_answer_score'] is None:
            result['status'] = 'incomplete'
    write_json(out/'result.json', result)
    render_report(out, result, questions, eligibility)
    return result


def render_report(out, result, questions, eligibility):
    s = result['summary']
    def fmt(v):
        return '—' if v is None else f'{v:.2f}'
    def full(v):
        return '未完成' if v is None else f'{v:.2f}'
    lines = ['# '+result['case_id']+'：学生分段提问与Specific评分', '',
        f"视频Specific完整分：{full(s['specific_score'])}。",
        f"画像完成{s['complete_profiles']}/{s['planned_profiles']}；检查点{s['complete_prefixes']}/{s['planned_prefixes']}；原始问题{s['original_questions']}；适用问题{s['eligible_questions']}；评分组{s['scored_groups']}/{s['question_groups']}。", '',
        f"待评分或未核实组：{s['question_groups'] - s['scored_groups']}。单题满分不代表整条视频满分。", '',
        '分数是模型对完整视频回答这些问题的判断，不是学生成绩或学习增益。参考与画像尚未经专家/真实学生校准；条件均分不能替代缺失的完整分数。', '',
        '| 组 | 原始问题 | 分数 | 理由 |', '| --- | --- | ---: | --- |']
    for key, g in result['question_pool'].items():
        r = (result.get('assessment') or {}).get('groups', {}).get(key, {})
        reason = r.get('reason', '评测未完成').replace('\n', ' ').replace('|', '/')
        lines.append(f"| {key} | {g['question'].replace('|', '/')} | {fmt(r.get('score'))} | {reason} |")
    lines += ['', '## 全部问题与适用性', '']
    for key, q in questions.items():
        e = eligibility.get(key, {})
        lines.append(f"- {key} @{q['cutoff_s']:.2f}s [{e.get('status', 'eligibility_missing')}] {q['question']} — {e.get('reason', '核验缺失')}")
    if result.get('error'):
        lines += ['', '运行错误：'+result['error']]
    if 'student_answers' in result:
        answer_summary = result['student_answers']['summary']
        lines += ['', '## 学生原问题的回答轨迹', '',
                  f"学生最终回答完整分：{full(answer_summary['supported_answer_score'])}；已评分组：{answer_summary['scored_groups']}/{answer_summary['groups']}；待评分或未核实组：{answer_summary['groups'] - answer_summary['scored_groups']}。",
                  '此分数是模型回答的证据支持与充分性，不是视频总分、真实学生成绩或学习增益；不同动态问题池不可直接排名。', '']
        for session in result['sessions']:
            for record in session.get('trajectory', []):
                lines.append(f"- {session['profile_id']} @{record['cutoff_s']:.2f}s：{len(record['answers'])}/{record['planned_questions']}条回答，{record['status']}。")
    lines += ['', '## 条件统计（仅用于诊断）', '',
              '下列均值只包含已经评分的条目；不补全未知项，不作为完整总分或跨问题池排名。', '',
              '| 评分对象 | 完整分 | 已评分/计划组 | 未评分或未核实 | 条件均分 |',
              '| --- | ---: | ---: | ---: | ---: |',
              f"| 视频回答充分性 | {full(s['specific_score'])} | {s['scored_groups']}/{s['question_groups']} | {s['question_groups'] - s['scored_groups']} | {fmt(s['mean_among_scored_groups'])} |"]
    if 'student_answers' in result:
        a = result['student_answers']['summary']
        lines.append(f"| 学生最终回答充分性 | {full(a['supported_answer_score'])} | {a['scored_groups']}/{a['groups']} | {a['groups'] - a['scored_groups']} | {fmt(a['mean_among_scored_groups'])} |")
    (Path(out)/'REPORT.md').write_text('\n'.join(lines)+'\n')
