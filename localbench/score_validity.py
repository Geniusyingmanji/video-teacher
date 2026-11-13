"""Propagate unresolved evidence to affected dimensions without editing raw ratings."""
from __future__ import annotations

import copy
import math

from .rubric import DIMENSIONS, aggregate_dimensions

VERSION = 'dimension-evidence-validity-v1'
TEACHING = [k for k, d in DIMENSIONS.items() if d['group'] == 'teaching']
VISUAL = [k for k in DIMENSIONS if k != 'audio_quality']
RELATIONS = ['conceptual_correctness', 'visual_teaching', 'crossmodal_alignment']


def affected_dimensions(affected, fallback):
    if not isinstance(affected, list) or not affected:
        return list(fallback)
    names = {a.split('.')[0] for a in affected if isinstance(a, str)}
    return sorted(names) if names and names <= set(DIMENSIONS) else list(fallback)


def invalid_reasons(result):
    """Also understands immutable legacy files at read/compare time."""
    reasons = {name: [] for name in DIMENSIONS}

    def block(names, reason):
        for name in names:
            if reason not in reasons[name]:
                reasons[name].append(reason)

    for name, d in result.get('dimensions', {}).items():
        if name not in reasons:
            continue
        validity = d.get('score_validity', {})
        if validity.get('status') == 'unverified':
            for reason in validity.get('reasons') or ['dimension_evidence_unverified']:
                block([name],reason)
        if d.get('score') is None and not validity.get('reasons'):
            block([name],'missing_dimension_score')
        if d.get('evidence_status', '').startswith(('unverified', 'incomplete', 'evaluation_stage_error')):
            block([name], d['evidence_status'])
    for conflict in result.get('verification_conflicts', []):
        block(affected_dimensions([conflict.get('criterion')], VISUAL), 'unresolved_verification_conflict')
    for concern in result.get('reference_concerns', []):
        # Unstructured concerns cannot silently count as resolved.
        block(affected_dimensions(concern.get('affected') if isinstance(concern, dict) else None, TEACHING),
              'unresolved_reference_concern')
    verification = result.get('critical_verification', {})
    if verification.get('status') in {'auxiliary_check_error', 'partial', 'error', 'unverified'}:
        block(affected_dimensions(verification.get('affected'),
                                  ['conceptual_correctness', 'task_completeness', 'visual_teaching']),
              'incomplete_specialized_verification')
    for check in verification.get('checks', []):
        if check.get('verdict') == 'unverified':
            block(affected_dimensions(check.get('affected'), VISUAL), 'unverified_check:' + check.get('id', 'unknown'))
    relation = verification.get('screen_relation_review', {})
    if relation and relation.get('status') != 'reviewed':
        block(RELATIONS, 'incomplete_screen_relation_review')
    if any(row.get('verdict') == 'ambiguous' for row in relation.get('frames', [])):
        block(RELATIONS, 'ambiguous_screen_relation')
    layout = result.get('dimensions', {}).get('visual_quality', {}).get('layout_audit', {})
    if layout and layout.get('status') != 'reviewed':
        block(['visual_quality'], 'incomplete_layout_review')
    quality=result.get('dimensions',{}).get('visual_quality',{})
    layout_keys={'text_overlap':'text_overlap','text_occlusion':'text_overlap',
                 'container_overflow':'containment','frame_clipping':'containment',
                 'small_text':'legibility','low_contrast':'contrast',
                 'crowding':'composition','glyph_corruption':'artifact_control'}
    for row in layout.get('frames',[]):
        for issue in row.get('issues',[]):
            if issue.get('severity')!='major':continue
            item=quality.get('criteria',{}).get(layout_keys.get(issue.get('kind')), {})
            if item.get('score') is None or item['score']>2:
                block(['visual_quality'],'unresolved_major_layout_conflict')
    timeline = result.get('timeline_review')
    if timeline is not None:
        if timeline.get('status') != 'reviewed' or timeline.get('unreviewed_frame_ids'):
            block(VISUAL, 'incomplete_timeline_review')
        for check in timeline.get('checks', []):
            if check.get('verdict') == 'unverified':
                block(affected_dimensions(check.get('affected'), VISUAL), 'uncertain_timeline_evidence')
    # Recompute disagreements at read time too: legacy files may contain a
    # failing check but lack an explicit verification_conflicts list.
    checks=list(verification.get('checks',[]))+list((timeline or {}).get('checks',[]))
    for check in checks:
        if check.get('verdict')!='fail':continue
        maximum={'critical':1,'major':2,'moderate':3,'minor':4}.get(check.get('severity'),2)
        for key in check.get('affected',[]):
            parts=key.split('.') if isinstance(key,str) else []
            if len(parts)!=2 or parts[0] not in DIMENSIONS:
                block(VISUAL,'unscoped_failed_check');continue
            item=result.get('dimensions',{}).get(parts[0],{}).get('criteria',{}).get(parts[1],{})
            if item.get('score') is not None and item['score']>maximum:
                block([parts[0]],'unresolved_check_rating_conflict')
    alignment = result.get('dimensions', {}).get('crossmodal_alignment', {}).get('coverage', {})
    if alignment and alignment.get('status') != 'reviewed':
        block(['crossmodal_alignment'], 'incomplete_alignment_windows')
    transcript = result.get('transcript_evidence_validity', {})
    if transcript.get('all_transcript_evidence_resolved') is False:
        block([k for k, d in DIMENSIONS.items() if any('transcript' in r for r in d['requires'])],
              'unresolved_transcript_evidence')
    for stage in result.get('stage_errors', []):
        block(affected_dimensions(stage.get('affected_dimensions'), VISUAL), 'stage_error:' + stage.get('stage', 'unknown'))
    return {k: v for k, v in reasons.items() if v}


def valid_score(result, name):
    reasons = invalid_reasons(result)
    if name == 'overall':
        value = result.get('scoring', {}).get('overall')
        if reasons or result.get('scoring', {}).get('status', '').startswith('unresolved'):
            return None
    else:
        if name in reasons:
            return None
        value = result.get('dimensions', {}).get(name, {}).get('score')
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100 else None


def apply(result):
    out = copy.deepcopy(result)
    reasons = invalid_reasons(out)
    for name, dimension in out['dimensions'].items():
        if name in reasons:
            dimension.setdefault('raw_score_before_validity', dimension.get('score'))
            dimension['score'] = None
        dimension['score_validity'] = {'version': VERSION,
            'status': 'unverified' if name in reasons or dimension.get('score') is None else 'verified',
            'reasons': reasons.get(name, []),
            'scope': 'Evidence completeness and consistency, not expert certification.'}
    original = out.get('scoring', {})
    updated = aggregate_dimensions(out['dimensions'])
    out['scoring'] = {**original, **updated, 'version': original.get('version', updated['version'])}
    if reasons:
        out['scoring']['status'] = 'unresolved_dimension_evidence'
        out['scoring']['incomplete_reasons'] = sorted({r for v in reasons.values() for r in v})
        out['evaluation_status'] = 'partial_evidence'
    # Never resurrect a withheld total (e.g. transcript evidence from older files).
    if original.get('overall') is None:
        out['scoring']['overall'] = None
    out['evidence_validity_version'] = VERSION
    return out
