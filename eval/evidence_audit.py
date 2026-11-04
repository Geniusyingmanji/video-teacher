"""Reconcile overview ratings with inspected local defects using identical anchors.

This is a declared non-compensatory rubric, not a calibrated scientific scale.
No deduction is made from silence, absent certification, or CV proxies alone.
Every constraint retains the source criterion, finding and local citations.
"""
import copy
import math

# An essential failure cannot be averaged away by unrelated clean typography.
# All bounds use the SAME (rating - 1) * 25 mapping as the overview rubric.
PRESENTATION_LINKS = {
    'layout_readability': ('visual_quality', 'signal_quality', 'pedagogical_clarity', 'audience_appropriateness'),
    'visual_explanation': ('pedagogical_clarity', 'didactic_affordances'),
    'temporal_contribution': ('temporal_consistency', 'narrative_structure', 'didactic_affordances'),
    'representation_integrity': ('conceptual_correctness', 'visual_quality'),
    'instructional_focus': ('pedagogical_clarity',),
    'perceptual_pacing': ('temporal_consistency', 'narrative_structure', 'audience_appropriateness'),
}
SPEECH_LINKS = {
    'speech_accuracy': ('conceptual_correctness',),
    'explanatory_coverage': ('pedagogical_clarity', 'didactic_affordances'),
    'visual_alignment': ('pedagogical_clarity', 'narrative_structure'),
    'speech_pacing': ('audience_appropriateness',),
}


def reconcile(result):
    """Keep independent raw scores and an auditable list of binding observations."""
    audit = []
    axes = result.get('axes', {})
    for source, links in [('instructional_presentation', PRESENTATION_LINKS), ('narration_review', SPEECH_LINKS)]:
        review = result.get(source, {})
        if review.get('valid') is not True:
            continue
        for row in review.get('criteria', []):
            rating = row.get('score')
            cited = bool(row.get('evidence_frames')) if source == 'instructional_presentation' else bool(row.get('speech_ids') and row.get('window_ids'))
            if (not cited or not row.get('finding') or type(rating) not in (int, float)
                    or not math.isfinite(rating) or not 1 <= rating <= 5):
                continue
            bound = (rating - 1) * 25
            for axis in links.get(row['id'], ()):
                target = axes.get(axis, {})
                value = target.get('score')
                if type(value) not in (int, float):
                    continue
                target.setdefault('overview_score_before_evidence_audit', value)
                if value > bound:
                    record = {'axis': axis, 'source': source, 'criterion': row['id'],
                              'rating': rating, 'bound': bound, 'previous_score': value,
                              'evidence': copy.deepcopy(row), 'rule': 'weakest essential criterion on shared anchors'}
                    audit.append(record)
                    target['score'] = bound
                    target.setdefault('evidence_constraints', []).append(record)
    # Geometric clipping is independently measurable on settled text boxes.
    # Require repetition at different actual render times; ignore animation transients.
    clipped = {}
    for check in result.get('render_geometry', {}).get('checks', []):
        for failure in check.get('failures', []):
            if failure.get('kind') == 'text_outside_frame' and failure.get('outside_fraction', 0) >= .2:
                clipped.setdefault(failure.get('text', ''), []).append({'time_s': check.get('time_s'), **failure})
    for label, findings in clipped.items():
        times = {f['time_s'] for f in findings if type(f['time_s']) in (int,float)}
        if len(times) < 2 or max(times)-min(times) < 1:
            continue
        for axis in ('visual_quality', 'signal_quality', 'pedagogical_clarity'):
            target = axes.get(axis, {})
            value = target.get('score')
            if type(value) in (int,float) and value > 25:
                target.setdefault('overview_score_before_evidence_audit',value)
                record = {'axis':axis,'source':'render_geometry','criterion':'persistent_text_clipping',
                          'rating':2,'bound':25,'previous_score':value,'evidence':findings,
                          'rule':'major defect: >=20% text box outside frame in >=2 settled checks spanning >=1s'}
                target['score']=25
                target.setdefault('evidence_constraints',[]).append(record)
                audit.append(record)
    extra = result.get('supplementary', {}).get('teaching_engagement', {})
    # Engagement design cannot claim meaningful progress contrary to the inspected
    # temporal contribution, or claim salience contrary to essential occlusion.
    if extra.get('valid') is True and result.get('instructional_presentation', {}).get('valid') is True:
        local = {row['id']: row for row in result['instructional_presentation'].get('criteria', [])}
        mapping = {'meaningful_progress': 'temporal_contribution', 'perceptual_salience': 'layout_readability',
                   'audience_fit': 'perceptual_pacing'}
        extra['overview_score_before_evidence_audit'] = extra.get('score')
        revised = []
        for row in extra.get('criteria', []):
            item = copy.deepcopy(row)
            evidence = local.get(mapping.get(row['id']))
            if (item.get('applicable') and evidence and evidence.get('evidence_frames')
                    and evidence.get('finding') and item['score'] > evidence['score']):
                item['overview_rating'] = item['score']
                item['score'] = evidence['score']
                item['binding_segment_evidence'] = copy.deepcopy(evidence)
            revised.append(item)
        values = [row['score'] for row in revised if row.get('applicable')]
        if values:
            extra['criteria'] = revised
            extra['score'] = round(sum((v-1)*25 for v in values)/len(values), 4)
    result['evidence_audit'] = {'version': 'criterion-reconciliation-v1', 'constraints': audit,
        'calibration_status': 'declared rubric; human agreement and external validity not yet calibrated'}
