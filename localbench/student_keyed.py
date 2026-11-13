"""Optional lossless learner decoding with explicit review item identities.

IDs identify complete original observations, not semantic atomic claims. This is
a response-format experiment; it does not establish reviewer truth or learning.
"""
from __future__ import annotations

import copy
import json

VERSION = 'student-diagnostics-dev7-keyed-retention'


def item_table(response):
    rows = {}
    for key, prefix in [('understandings', 'U'), ('questions', 'Q')]:
        for index, row in enumerate(response[key]):
            rows[f'{prefix}{index}'] = {'kind': key, 'original_index': index,
                                       'observation': copy.deepcopy(row)}
    return rows


def review_request(request, response):
    """Change only review serialization; keep the original response and media."""
    request = copy.deepcopy(request)
    data = json.loads(request[1]['content'][0]['text'])
    items = item_table(response)
    data['review_items'] = items
    data['required_review_ids'] = list(items)
    request[1]['content'][0]['text'] = json.dumps(data, ensure_ascii=False)
    template = {'items': {}, 'profile_consistency': {'status': None, 'reason': None}}
    for id_, row in items.items():
        template['items'][id_] = {'status': None, 'evidence_ids': [], 'reason': None}
        if row['kind'] == 'questions':
            template['items'][id_]['rubric_targets'] = []
    request[0]['content'] = request[0]['content'].split('Return JSON:', 1)[0] + '''
Return one JSON object using the exact item IDs in required_review_ids. Each ID
denotes the ENTIRE original observation, even when it contains several clauses.
Do not split a compound observation into new IDs, merge IDs, rewrite observations,
or drop recap items. Duplicate wording at distinct IDs still requires both IDs.
For a compound understanding, supported requires support for every essential
assertion; a contradicted essential assertion makes the item contradicted; if
support for any essential assertion is unresolved, use unverified. Explain which
clause determines that judgment. This is media support, not global factual truth.
Use the existing question statuses and rubric rules above. Preserve all evidence
requirements and the ban on pending_instruction at the final checkpoint.
Fill every null with the appropriate status or specific reason, and every
evidence_ids list with actual evidence from the supplied prefix. Do not output
indices, claims, or any keys outside this complete template:
''' + json.dumps(template, ensure_ascii=False)
    return request


def validate(raw, response, observation):
    from .student import validate_review
    expected = item_table(response)
    if not isinstance(raw, dict) or set(raw) != {'items', 'profile_consistency'}:
        raise ValueError('keyed review requires exactly items and profile_consistency')
    items = raw['items']
    if not isinstance(items, dict) or set(items) != set(expected):
        raise ValueError(f'keyed review must cover exactly {list(expected)}; '
                         'do not split, merge, add or drop original observations')
    canonical = {'understandings': [], 'questions': [],
                 'profile_consistency': copy.deepcopy(raw['profile_consistency'])}
    for id_, original in expected.items():
        row = items[id_]
        fields = {'status', 'evidence_ids', 'reason'}
        if original['kind'] == 'questions':
            fields.add('rubric_targets')
        allowed_shapes = [fields]
        if original['kind'] == 'questions':
            # Match the canonical validator: a non-defect need not invent a
            # rubric mapping. Evidence remains mandatory, including pending items.
            allowed_shapes.append(fields - {'rubric_targets'})
        if not isinstance(row, dict) or set(row) not in allowed_shapes:
            raise ValueError(f'{id_} requires exactly {sorted(fields)}')
        canonical[original['kind']].append({'index': original['original_index'],
                                          **copy.deepcopy(row)})
    # Normalize only identity representation; never manufacture a model verdict.
    return validate_review(canonical, response, observation)


GUIDANCE = ('Keep exactly the required_review_ids from the original request in the items object. '
            'Each ID covers one complete original observation, including compound clauses. '
            'Do not split, merge or rewrite observations. Use the SAME media and evidence IDs; '
            'do not change a judgment just to improve it. Keep the complete keyed template.')
