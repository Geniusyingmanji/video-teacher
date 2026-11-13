"""Freeze task-dependent optional criteria before a comparative evaluation."""
from __future__ import annotations

import json
from pathlib import Path

from .common import digest, public_case
from .reference_contract import public_source_hash
from .strict_anchors import OPTIONAL_CRITERIA

VERSION = 'applicability-v1'
INSTRUCTIONS = '''
The frozen criterion_applicability annotation determines which OPTIONAL criteria apply
to this public task, identically for every video of that task. Do not infer applicability
from whether the generated video includes the requested content.
For applicable=true, use observed with an evidence-grounded integer rating, or unverified
if the evidence is insufficient; NEVER not_applicable. A missing requested check is an
omission to evaluate, not a reason to exclude verification.
For applicable=false, return not_applicable and score=null, with the public-task reason.
The annotation sets applicability only, not whether the video satisfies the requirement,
not a preferred implementation, and not any rating. Keep the existing behavior anchors.
'''


def validate_annotation(raw, case):
    if not isinstance(raw, dict) or raw.get('version') != VERSION:
        raise ValueError('invalid applicability version')
    if raw.get('case_id') != case['id'] or raw.get('public_input_hash') != digest(public_case(case)):
        raise ValueError('applicability annotation has a stale public task')
    if raw.get('public_source_sha256') != public_source_hash(case):
        raise ValueError('applicability annotation has a stale public source')
    if raw.get('review_status') != 'editorial_reviewed' or raw.get('expert_verified') is not False:
        raise ValueError('applicability needs explicit editorial review; not expert certification')
    criteria = raw.get('criteria')
    if not isinstance(criteria, dict) or set(criteria) != OPTIONAL_CRITERIA:
        raise ValueError('applicability must cover exactly all optional criteria')
    prompt = public_case(case)['prompt_text']
    for name, row in criteria.items():
        if not isinstance(row, dict) or type(row.get('applicable')) is not bool:
            raise ValueError(name+': applicability must be boolean')
        if not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise ValueError(name+': applicability needs a public-task reason')
        quotes = row.get('prompt_quotes')
        if not isinstance(quotes, list) or any(not isinstance(q, str) or not q.strip() or q not in prompt for q in quotes):
            raise ValueError(name+': applicability quotes must be exact public-prompt spans')
        if row['applicable'] and not quotes:
            raise ValueError(name+': applicable criterion needs public-prompt evidence')
    return raw


def load_annotations(path, cases):
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError('applicability file must map case IDs to annotations')
    return {c['id']: validate_annotation(raw.get(c['id']), c) for c in cases}


def validate_rating(name, key, status, annotation):
    if annotation is None:
        return
    item = annotation['criteria'].get(name+'.'+key)
    if item is None:
        return
    if (status == 'not_applicable') == item['applicable']:
        raise ValueError(name+'.'+key+': rating contradicts frozen public-task applicability')
