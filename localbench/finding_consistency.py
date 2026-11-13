"""Reject explicit fulfillment/decision contradictions without inventing scores."""
from __future__ import annotations

import re

VERSION = 'finding-decision-consistency-v1'
STATES = {'complete','partial','absent','incorrect','uncertain'}


def contradiction(item):
    verdict = item.get('verdict',item.get('status'))
    fulfillment = item.get('fulfillment')
    if fulfillment is not None and (not isinstance(fulfillment,str) or fulfillment not in STATES):
        return 'Unknown fulfillment state.'
    if verdict != 'met':
        return None
    if fulfillment is not None and fulfillment != 'complete':
        return 'met contradicts explicit '+fulfillment+' fulfillment.'
    # These are explicit self-reports of an unmet obligation, not generic words
    # such as "no" (which would wrongly flag "no overlap" or "no missing steps").
    patterns = [r'^\s*partial[.!]?\s*$', r'\bpartially\s+(?:met|satisfied|fulfilled|shown|covered|addressed|demonstrated)\b',
                r'\bonly partial(?:ly)?\b', r'\b(?:coverage|requirement|obligation|fulfillment)\s+(?:is\s+)?partial\b', r'\b(?:obligation|requirement|coverage)\s+(?:is\s+)?incomplete\b',
                r'\b(?:unverified|uncertain|not verified)\b',
                r'\b(?:no|missing|absent)\s+(?:spoken\s+)?(?:narration|visual check|requested demonstration)\b',
                r'\b(?:example|demonstration|narration)\s+(?:is\s+|was\s+)?(?:absent|missing|not shown)\b',
                r'\bnot\s+(?:shown|demonstrated|satisfied|fulfilled|addressed)\b']
    for field in ('finding','observed','reason'):
        text = item.get(field,'')
        if not isinstance(text,str):continue
        for pattern in patterns:
            match = re.search(pattern,text,re.I)
            if match:
                prefix=text[max(0,match.start()-12):match.start()].lower()
                if re.search(r'\b(?:not|no)\s+$',prefix):continue
                return f'met contradicts {field}: {match.group()}'
    return None


def validate(item):
    reason = contradiction(item)
    if reason:
        raise ValueError('fulfillment/decision conflict: '+reason)
    return item
