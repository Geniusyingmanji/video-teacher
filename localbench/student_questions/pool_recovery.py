"""Preserve failed batches without suppressing independent question standards."""
from __future__ import annotations

import copy
from .protocol import validate_pool


def recover_batch(raw, eligible, references):
    """Inspect every saved group; replace invalid content only with explicit unknown.

    Does not repair facts, source citations, questions, or target wording.
    Exact membership is required before independently accepting any group.
    """
    membership_error = None
    try:
        if not isinstance(raw, dict) or set(raw) != {'groups'} or not isinstance(raw['groups'], list):
            raise ValueError('missing unambiguous group list')
        members = [g['members'][0] for g in raw['groups'] if isinstance(g, dict) and isinstance(g.get('members'), list) and len(g['members']) == 1]
        if len(members) != len(raw['groups']) or sorted(members) != sorted(eligible):
            raise ValueError('membership incomplete, duplicated or not one-question-per-group')
    except (ValueError, TypeError, KeyError) as exc:
        membership_error = str(exc)
    indexed = {g['members'][0]: g for g in raw['groups']} if membership_error is None else {}
    groups, receipt = {}, []
    for i, (qid, question) in enumerate(eligible.items()):
        original = indexed.get(qid)
        error = membership_error
        if error is None:
            try:
                accepted = validate_pool({'groups': [original]}, {qid: question}, references)['S01']
            except (ValueError, TypeError, KeyError) as exc:
                error = str(exc)
        if error is not None:
            accepted = {'members': [qid], 'representative_id': qid, 'question': question['question'],
                        'reference_status': 'insufficient', 'targets': [], 'construction_error': error}
        groups[f'S{i+1:02d}'] = copy.deepcopy(accepted)
        receipt.append({'question_id': qid, 'status': 'unverified_placeholder' if error else 'structurally_retained',
                        'error': error, 'original_group': copy.deepcopy(original)})
    return groups, receipt
