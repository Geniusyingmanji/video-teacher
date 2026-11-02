"""Non-compensatory acceptance using the existing approved v4 thresholds."""


def assess(generation, evaluation):
    diagnostics = generation.get('strict_diagnostics', {})
    contract_source = diagnostics.get('source_preservation')
    def supported(axis, keys):
        rows = {row['id']: row for row in evaluation.get('axes', {}).get(axis, {}).get('criteria', [])}
        return all(key in rows and rows[key].get('applicable') is True
                   and type(rows[key].get('score')) in (int, float)
                   and rows[key]['score'] >= 4 and bool(rows[key].get('evidence_frames')) for key in keys)
    checks = {
        'generation': generation.get('complete') is True,
        'strict_duration': generation.get('timing', {}).get('valid') is True,
        'source_preservation': (contract_source is None and not generation.get('source_required')) or (
            contract_source is not None and
            contract_source.get('valid') is True
            and contract_source.get('pre_encoding', {}).get('valid') is True),
        'rubric_valid': evaluation.get('scoring', {}).get('valid') is True,
        'v4_strict_pass': evaluation.get('scoring', {}).get('strict_pass') is True,
        'task_coverage': supported('conceptual_correctness', ['final_state']),
        'correctness': supported('conceptual_correctness', ['core_fact', 'no_contradiction']),
        'readability': supported('pedagogical_clarity', ['readability', 'takeaway']),
        'engagement_report_valid': evaluation.get('supplementary', {}).get(
            'teaching_engagement', {}).get('valid') is True,
    }
    # Engagement is reported separately; its numeric score never affects acceptance.
    failures = [name for name, passed in checks.items() if not passed]
    return {'passed': not failures, 'checks': checks, 'failures': failures,
            'quality_evidence': {'axes': evaluation.get('axes', {}),
                                 'defects': evaluation.get('defects', []),
                                 'scoring': evaluation.get('scoring', {})}}
