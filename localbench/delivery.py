"""Shared final-media reporting for all selected tasks, including failures."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

from .common import write_json
from .rubric import DIMENSIONS, TEACHING_GROUPS
from .score_validity import valid_score, invalid_reasons
from .acceptance import assess as assess_acceptance


def build_report(out, cases, generated, evaluated, students=None, *, specific_requested=False):
    out = Path(out)
    generation = {r['id']: r for r in generated}
    scores = {r['case_id']: r for r in evaluated}
    student_results = {r['case_id']: r for r in students or []}
    specific_requested = specific_requested or any('specific' in r for r in evaluated)
    rows = []
    for case in cases:
        id_ = case['id']; gen = generation.get(id_, {}); score = scores.get(id_, {})
        artifact = next((a for a in gen.get('artifacts', []) if a.get('complete')), {})
        scoring = score.get('scoring', {})
        row = {'id': id_, 'discipline': case.get('discipline_canonical', case.get('discipline')),
               'framework': gen.get('framework'), 'upstream_commit': gen.get('upstream_commit'),
               'task_type': case.get('task_type'), 'generation_status': gen.get('status', 'not_started'),
               'evaluation_status': score.get('evaluation_status', score.get('status', 'not_started')),
               'quality_check_status':score.get('output_checks',{}).get('status','unverified'),
               'failed_checks':score.get('output_checks',{}).get('failed',[]),
               'review_checks':score.get('output_checks',{}).get('review',[]),
               'unverified_checks':score.get('output_checks',{}).get('unverified',[]),
               'video_path': artifact.get('video_path'), 'duration_s': artifact.get('duration_s'),
               'video': scoring.get('groups', {}).get('video'),
               'teaching': scoring.get('groups', {}).get('teaching'), 'overall': valid_score(score,'overall'),
               'error': gen.get('error') or score.get('error')}
        invalid=invalid_reasons(score)
        for group in ('video','teaching'):
            if any(name in invalid for name,d in DIMENSIONS.items() if d['group']==group):row[group]=None
        acceptance=assess_acceptance(score)
        row['acceptance_status']=acceptance['status']
        row['acceptance_failures']=acceptance['failures']
        row['acceptance_unverified']=acceptance['unverified']
        panel, specific = score.get('judge_panel', {}), score.get('specific', {})
        row.update(judge_count=panel.get('expected_judges'),
                   complete_judges=panel.get('complete_judges'),
                   pending_judge_criteria=panel.get('pending_criteria'),
                   specific_status=specific.get('status', 'not_evaluated' if specific_requested else 'not_requested'),
                   specific=specific.get('specific_score'),
                   specific_scored_questions=specific.get('scored_questions'),
                   specific_planned_questions=specific.get('planned_questions'))
        row['rubric_version'] = score.get('rubric_version')
        if students is not None:
            learner = student_results.get(id_, {})
            metric = learner.get('metrics', {})
            row.update(student_status=learner.get('status', 'not_started'),
                       student_profile_coverage=metric.get('profile_coverage', 0),
                       student_final_gap_reports=metric.get('final_video_gap_reports'),
                       student_supported_claim_rate=metric.get('supported_claim_rate_among_assessed'))
            verdicts = metric.get('understanding_verdicts')
            for status in ('supported', 'contradicted', 'unverified'):
                row[f'student_{status}_claims'] = verdicts.get(status, 0) if verdicts is not None else None
        for name in TEACHING_GROUPS:
            row[name] = (None if any(k in invalid for k in TEACHING_GROUPS[name]['dimensions']) else
                         scoring.get('teaching_groups', {}).get(name, {}).get('score'))
        for name in DIMENSIONS:
            row[name] = valid_score(score,name)
        rows.append(row)
    valid = [r['overall'] for r in rows if r['overall'] is not None]
    n = len(rows)
    summary = {'planned_cases': n, 'delivered_cases': sum(bool(r['video_path']) for r in rows),
               'accepted_cases':sum(r['acceptance_status']=='passed' for r in rows),
               'acceptance_rate':sum(r['acceptance_status']=='passed' for r in rows)/n if n else 0,
               'acceptance_statuses':dict(Counter(r['acceptance_status'] for r in rows)),
               'scored_cases': len(valid), 'valid_score_coverage': len(valid)/n if n else 0,
               'mean_overall_among_valid': sum(valid)/len(valid) if valid else None,
               'all_cases_mean': sum(valid)/n if n and len(valid) == n else None,
               'generation_statuses': dict(Counter(r['generation_status'] for r in rows)),
               'evaluation_statuses': dict(Counter(r['evaluation_status'] for r in rows)),
               'quality_check_statuses':dict(Counter(r['quality_check_status'] for r in rows)),
               'scope': 'All selected cases retained. Missing/invalid evaluation is null, not zero. Development rubric, human calibration pending.',
               'cases': rows}
    specific_valid = [r['specific'] for r in rows if r['specific'] is not None]
    summary['specific_evaluation'] = {
        'requested_cases': n if specific_requested else 0,
        'scored_cases': len(specific_valid),
        'mean_among_valid': sum(specific_valid)/len(specific_valid) if specific_valid else None,
        'weight_in_general': 0}
    if students is not None:
        planned_profiles = sum(r.get('metrics', {}).get('planned_profiles', 0) for r in students)
        complete_profiles = sum(r.get('metrics', {}).get('complete_profiles', 0) for r in students)
        summary['student_evaluation'] = {
            'planned_cases': n, 'complete_cases': sum(r.get('status') == 'complete' for r in students),
            'planned_profiles': planned_profiles, 'complete_profiles': complete_profiles,
            'profile_coverage': complete_profiles/planned_profiles if planned_profiles else 0,
            'statuses': dict(Counter(r['student_status'] for r in rows)),
            'total_weight': 0, 'score': None,
            'scope': 'Separate learner diagnostic; not quality/learning score. Missing results are null.'}
    write_json(out/'summary.json', summary)
    with (out/'scores.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ['id'])
        writer.writeheader(); writer.writerows(rows)
    def fmt(x):
        return '—' if x is None else f'{x:.2f}'
    lines = ['# RISE-Teacher 运行报告', '',
             f'计划 {n} 题；交付 {summary["delivered_cases"]} 条；综合分有效 {len(valid)} 条；质量验收通过 {summary["accepted_cases"]} 条。',
             f'有效样本综合均分：{fmt(summary["mean_overall_among_valid"])}。全体均分：{fmt(summary["all_cases_mean"])}。',
             '评分仅来自最终视频证据；有效格式不保证判断正确。缺失评分不记零，失败题不移出分母。', '',
             '| 题号 | 生成 | 评测 | 质量核查 | 质量验收 | 视频 | 教学内容 | 教学组织 | 教学表达 | 综合 |',
             '| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:
        label = r['id']
        if r['video_path']:
            import os
            label = f'[{label}]({os.path.relpath(r["video_path"], out).replace(os.sep, "/")})'
        lines.append(f'| {label} | {r["generation_status"]} | {r["evaluation_status"]} | {r["quality_check_status"]} | {r["acceptance_status"]} | '+
                     ' | '.join(fmt(r[k]) for k in ('video', 'content', 'organization', 'expression', 'overall'))+' |')
    lines += ['', '质量核查中的 fail 表示观察到具体缺陷，review 表示需复核；高均分不等于通过。',
              '十个叶维度与逐题错误见 `scores.csv`、`summary.json`；证据见 `evaluation/`。',
              '视频／教学各占 50%。教学内七叶维度等权，因此内容／组织／表达在教学内分别占 2/7、3/7、2/7。',
              'API 台账见 `api/usage.jsonl`。运行配置中不保存 API key。', '']
    if any(r['judge_count'] for r in rows):
        lines += ['## 三评委与 Specific', '',
                  '视觉／教学准则需三份有效整数评分，逐项取中位数；极差达到 2 分或缺评时留空待复核。音频是共享听音模型的独立单评，不计作三票。Specific 独立于 General。', '',
                  '| 题号 | General 完整评委 | 待复核准则 | Specific 状态 | Specific | 有效问题/计划问题 |',
                  '| --- | --- | ---: | --- | ---: | --- |']
        for r in rows:
            def count(value): return '—' if value is None else str(value)
            lines.append(f'| {r["id"]} | {count(r["complete_judges"])}/{count(r["judge_count"])} | {count(r["pending_judge_criteria"])} | '
                         f'{r["specific_status"]} | {fmt(r["specific"])} | '
                         f'{count(r["specific_scored_questions"])}/{count(r["specific_planned_questions"])} |')
        lines += ['', '每位评委的分数、理由和证据见 `evaluation/<id>/judges/<judge_id>/scores.json`；'
                  '分歧与缺评见 `evaluation/<id>/review_queue.json`。Specific 明细见同题 `specific/`。', '']
    if students is not None:
        lines += ['## 第三块：模拟学生诊断', '',
                  '学生复述理解并提出疑问，另一个模型回查画面与转写证据。下表是核验器的判断，尚非独立确认的事实；有据标签不代表内容正确或学生学会。',
                  '使用采样帧和已完成音频片段的独立转写，未直接听音；前置知识画像尚未经真实学生校准。此块不计入原 50/50 总分。', '',
                  '| 题号 | 状态 | 画像完成覆盖 | 有据/矛盾/未核实条目 | 判有据比例（排除未核实） | 末段视频缺口报告数 |',
                  '| --- | --- | ---: | --- | ---: | ---: |']
        for r in rows:
            rate = r['student_supported_claim_rate']
            counts = '/'.join('—' if r[f'student_{status}_claims'] is None
                              else str(r[f'student_{status}_claims'])
                              for status in ('supported', 'contradicted', 'unverified'))
            lines.append(f'| {r["id"]} | {r["student_status"]} | {r["student_profile_coverage"]:.0%} | '+
                         counts+' | '+
                         ('—' if rate is None else f'{rate:.0%}')+' | '+
                         ('—' if r['student_final_gap_reports'] is None else str(r['student_final_gap_reports']))+' |')
        lines += ['', '理解条目跨画像和检查点累计，可能重复。判有据比例=supported/(supported+contradicted)，未核实条目单列；100%不等于满分。缺口数按画像计数，0不表示没有缺陷。未完成画像仍保留在覆盖率分母。逐段原始响应、核验、错误与证据见 `student/`。', '']
        for result in students:
            if result.get('error'):
                lines += [f'- {result["case_id"]}：{result["error"]}', '']
            for session in result.get('sessions', []):
                for checkpoint in session['checkpoints']:
                    if checkpoint['status'] != 'complete':
                        lines.append(f'- {result["case_id"]}/{session["profile_id"]} @ {checkpoint["cutoff_s"]:.1f}s：{checkpoint.get("error", checkpoint["status"])}')
                        continue
                    for question in checkpoint['review']['questions']:
                        original = checkpoint['response']['questions'][question['index']]['question']
                        reason = question['reason'].replace('\n', ' ')
                        lines.append(f'- {result["case_id"]}/{session["profile_id"]} @ {checkpoint["cutoff_s"]:.1f}s '
                                     f'**{question["status"]}**：{original} — {reason} '
                                     f'（{", ".join(question["evidence_ids"])}）')
        lines.append('')
    # Keep actionable evidence next to the score table, rather than hiding it in JSON.
    for r in rows:
        score=scores.get(r['id'],{});issues=[]
        for failure in r['acceptance_failures']:issues.append(('验收失败',failure))
        for unknown in r['acceptance_unverified']:issues.append(('验收未验证',unknown))
        if r['error']:issues.append(('运行错误',r['error']))
        for issue in score.get('stage_errors',[]):
            issues.append(('评测阶段 '+issue['stage'],issue['error']))
        for dimension,value in score.get('dimensions',{}).items():
            for key,item in value.get('criteria',{}).items():
                if item.get('status')=='unverified':
                    issues.append(('评分未验证 '+dimension+'.'+key,item.get('reason','')))
        for issue in score.get('output_checks',{}).get('checks',[]):
            if issue.get('status') in {'fail','review','unverified'}:
                issues.append((issue['status']+' '+issue['id'],issue['reason']+' 证据：'+', '.join(issue.get('evidence_ids',[]))))
        if issues:
            lines += ['### '+r['id']+'：问题与未验证项','']
            for label,reason in issues:
                clean=str(reason).replace('\n',' ').replace('<','&lt;').replace('>','&gt;')
                lines.append('- **'+label+'**：'+clean)
            lines.append('')
    (out/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary
