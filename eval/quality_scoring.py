"""Transparent v12 quality aggregation; acceptance is a separate decision.

Weights are declared policy, not empirically validated learning measurements.
No score floor, weakest-item total, cross-axis cap, or target score distribution.
v11 modules and saved results remain available for historical reproduction.
"""
import copy
import math

VERSION='video-teacher-quality-v12'
WEIGHTS_WITH_SPEECH={'video_quality':.4,'teaching_quality':.4,'spoken_teaching':.2}


def numeric(value):
    return type(value) in (int,float) and math.isfinite(value) and 0<=value<=100


def criterion_mean(review):
    rows=[r for r in review.get('criteria',[]) if r.get('applicable',True)]
    if not rows:return None
    scores=[r.get('score') for r in rows]
    if any(type(s) not in (int,float) or not math.isfinite(s) or not 1<=s<=5 for s in scores):return None
    return round(sum((s-1)*25 for s in scores)/len(scores),4)


def aggregate_quality(axes, *, speech_score=None, narration_required=False, acceptance_failures=()):
    from eval.benchmark_scoring import VIDEO_AXES,TEACHING_AXES
    errors=[a for a in VIDEO_AXES+TEACHING_AXES if not numeric(axes.get(a))]
    if narration_required and not numeric(speech_score):errors.append('spoken_teaching_unverified')
    groups={}
    for name,keys in [('video_quality',VIDEO_AXES),('teaching_quality',TEACHING_AXES)]:
        groups[name]=round(sum(axes[a] for a in keys)/len(keys),4) if all(numeric(axes.get(a)) for a in keys) else None
    if narration_required:groups['spoken_teaching']=speech_score
    weights=WEIGHTS_WITH_SPEECH if narration_required else {'video_quality':.5,'teaching_quality':.5}
    score=round(sum(groups[k]*w for k,w in weights.items()),4) if not errors else None
    failures=list(dict.fromkeys(acceptance_failures))
    if not errors:
        if any(axes[a]<60 for a in VIDEO_AXES+TEACHING_AXES):failures.append('axis_below_acceptance_threshold')
        if groups['video_quality']<70 or groups['teaching_quality']<70:failures.append('group_below_acceptance_threshold')
        if axes['conceptual_correctness']<70 or axes['pedagogical_clarity']<70:failures.append('critical_teaching_below_acceptance_threshold')
    return {'valid':not errors,'score':score,'groups':groups,'weights':weights,
            'axis_scores_after_caps':dict(axes),'axis_scores':dict(axes),'numeric_caps_applied':False,
            'strict_pass':not errors and not failures,'acceptance_failures':failures,'gates':failures,'errors':errors,
            'calibration_status':'declared criterion-based policy; external human validity not yet established'}


def apply(evaluation):
    import os
    if os.environ.get("VIDEO_TEACHER_SCORING_POLICY") == "quality-v13":
        from eval.dimension_scoring import apply as apply_dimensions
        return apply_dimensions(evaluation)
    return apply_v12(evaluation)


def apply_v12(evaluation):
    """Use independent criterion ratings, retaining legacy decisions as diagnostics.

    Observed failures still fail acceptance. A missing/ambiguous comparison is
    reported as unverified comparison evidence, not a manufactured zero score.
    """
    from eval.benchmark_scoring import VIDEO_AXES,TEACHING_AXES
    result=copy.deepcopy(evaluation);legacy=result.get('scoring',{})
    result['legacy_v11_diagnostics']={'scoring':legacy,'evidence_audit':result.get('evidence_audit',{})}
    axes={}
    for name in VIDEO_AXES+TEACHING_AXES:
        axis=result.get('axes',{}).get(name,{})
        value=criterion_mean(axis)
        if value is None and not axis.get('criteria'):
            value=axis.get('overview_score_before_evidence_audit',axis.get('score'))
        axes[name]=value
        axis['legacy_score']=axis.get('score');axis['score']=value
        axis['aggregation']='mean of applicable evidenced criteria; no cross-axis numeric caps'
    required=result.get('narration_required',False)
    speech=result.get('narration_review',{})
    speech_score=criterion_mean(speech) if speech.get('valid') is True else None
    if not required:speech_score=None
    failures=[]
    for field in ('task_completion','instructional_presentation','narration_review'):
        if field=='narration_review' and not required:continue
        review=result.get(field,{})
        if review.get('valid') is not True:failures.append(field+'_unverified')
        elif review.get('passed') is not True:failures.append(field+'_not_accepted')
    if result.get('consistency_review',{}).get('valid') is not True:failures.append('consistency_unverified')
    scoring=aggregate_quality(axes,speech_score=speech_score,narration_required=required,acceptance_failures=failures)
    if result.get('consistency_review',{}).get('valid') is not True and result.get('axes'):
        scoring.update(valid=False,score=None,strict_pass=False)
        scoring['errors'].append('unresolved_factual_evidence')
    scoring['spoken_teaching_score']=speech_score
    scoring['presentation_score']=criterion_mean(result.get('instructional_presentation',{}))
    result['scoring']=scoring;result['version']=VERSION
    scoring['ranking_eligible']=bool(scoring['valid'] and result.get('task_completion',{}).get('valid') is True)
    result['quality_policy']={'version':VERSION,'weights':scoring['weights'],
        'zero_policy':'Zero is possible only from actual zero-valued measured components, never a single-item total veto.',
        'acceptance_separate':True,'no_target_score_distribution':True}
    from eval.run_benchmark_v2 import assessment_coverage
    result['assessment_coverage']=assessment_coverage(result)
    return result


def aggregate(rows):
    from eval.benchmark_scoring import aggregate as legacy_aggregate
    result=legacy_aggregate(rows)
    result.update(version=VERSION,calibration_status='declared policy; human calibration pending',
                  numeric_caps_applied=False,acceptance_separate=True)
    if any(not row.get('scoring',{}).get('ranking_eligible',False) for row in rows):
        result.update(ranking_publishable=False,ranking_score=None)
    return result
