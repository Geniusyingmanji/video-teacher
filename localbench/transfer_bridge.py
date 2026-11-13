"""Required process/transfer/recipient/outcome roles for a small explanatory bridge.

The schema prevents an omitted role from silently vanishing during compilation.
It cannot establish that the supplied roles or causal relation are scientifically true.
"""
from __future__ import annotations

import json
from pathlib import Path

from .causal_chain import compile_chain
from .common import digest, public_case, write_json

VERSION = 'required-transfer-roles-v1'
SPOKEN_VERSION = 'shared-transfer-roles-narration-v1'
ROLES = ('process', 'transfer', 'recipient', 'outcome')


def validate_bridge(raw, references, original_narration, max_words):
    fields = {'narration', *ROLES, 'evidence_ids', 'relation_explanations'}
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite narration word budget required')
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ValueError('exact narration, four roles, evidence_ids and relation_explanations required')
    narration = raw['narration']
    if not isinstance(narration, str) or not 5 <= len(narration.split()) <= max_words:
        raise ValueError(f'narration must have 5..{max_words} words')
    if ' '.join(narration.split()) == ' '.join(original_narration.split()):
        raise ValueError('unchanged narration is a no-op')
    for role in ROLES:
        value = raw[role]
        if not isinstance(value, str) or not 1 <= len(value) <= 36 or value != ' '.join(value.split()):
            raise ValueError(f'{role} needs a nonempty short plain-text value')
    explanations = raw['relation_explanations']
    if not isinstance(explanations, list) or len(explanations) != 2 or any(
        not isinstance(v, str) or not 1 <= len(v.strip()) <= 240 for v in explanations
    ):
        raise ValueError('two bounded causal explanations required')
    # The roles are displayed by construction, not entrusted to a second model.
    chain = {'nodes': [
        {'id': 'process', 'label': raw['process']},
        {'id': 'recipient', 'label': raw['transfer'] + ' to ' + raw['recipient']},
        {'id': 'outcome', 'label': 'Supports ' + raw['outcome']}],
        'links': [
            {'source': 'process', 'target': 'recipient', 'explanation': explanations[0],
             'evidence_ids': raw['evidence_ids']},
            {'source': 'recipient', 'target': 'outcome', 'explanation': explanations[1],
             'evidence_ids': raw['evidence_ids']}]}
    compile_chain(chain, references)
    return chain


def compose_narration(raw, references, original_context, max_words):
    """Compile the same model role values into speech; retain source context.

    This guarantees lexical inclusion, not grammatical or scientific validity.
    The caller still checks actual synthesized media and context compatibility.
    """
    if not isinstance(original_context, str) or not original_context.strip():
        raise ValueError('existing spoken introduction required')
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite compiled narration word budget required')
    validate_bridge(raw, references, original_context, 90)
    context = original_context.strip()
    if context[-1] not in '.!?':
        context += '.'
    process = raw['process'].rstrip('.') + '.'
    transfer = ('This transfers ' + raw['transfer'] + ' to ' + raw['recipient'] +
                ', supporting ' + raw['outcome'].rstrip('.') + '.')
    narration = ' '.join([context, process, transfer])
    if len(narration.split()) > max_words:
        raise ValueError('compiled narration exceeds the budget; no role may be silently dropped')
    return narration, {'version': SPOKEN_VERSION, 'bridge_hash': digest(raw),
        'context_hash': digest(original_context), 'role_values': {k: raw[k] for k in ROLES},
        'generated_free_prose_used': False, 'compiled_narration': narration,
        'word_count': len(narration.split()), 'semantic_acceptance': 'unverified',
        'checked_scope': 'Role strings included in intended narration; actual audio and meaning need review.'}


def propose_bridge(client, case, narration, objective, references, max_words, out):
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs or not isinstance(narration, str) or not narration.strip():
        raise ValueError('original narration and public references required')
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite narration word budget required')
    out = Path(out)
    context = {'public_task': public_case(case), 'original_scene_narration': narration,
               'objective': objective, 'public_references': refs, 'max_narration_words': max_words}
    write_json(out / 'input.json', context)
    system = '''Write a bounded English teaching revision from the objective and public
sources. Return ONLY JSON with exactly these fields:
{narration:"revised spoken explanation",process:"short process clause",transfer:"quantity or material",
recipient:"receiving entity",outcome:"result supported by that transfer",evidence_ids:["source ID"],
relation_explanations:["why the process transfers this to that recipient","why that supports the outcome"]}.
All four process/transfer/recipient/outcome roles are required. Each is a short plain
phrase of at most36characters. Name the actual receiving entity; do not replace it with
the general topic. Outcome is a noun phrase that fits after the word Supports. Process
is a short clause. Avoid adding stronger causal necessity/sufficiency than the sources.
The renderer displays three connected boxes verbatim: process; transfer + to + recipient;
Supports + outcome. Do not provide alternative nodes or coordinates. Facts and wording
must fit the public sources and original task. Do not add unrelated concepts.
Revise the original narration with the requested mechanism in five to max_narration_words
English words, appropriate to the audience. Preserve required introductory context.
The spoken revision must explain these same displayed roles. Only this first scene is
being edited; the rest is preserved. Do not output a full plan, scores or learning claims.
These are qualitative explanatory relations, not a full scientific simulator.'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'transfer_bridge:{case["id"]}:{attempt}', max_tokens=1800)
        write_json(out / f'raw_{attempt}.json', raw)
        try:
            chain = validate_bridge(raw, refs, narration, max_words)
            write_json(out / 'transfer_bridge.json', raw)
            write_json(out / 'derived_chain.json', chain)
            return raw['narration'], chain
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out / f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct this bounded output/fit issue with the same facts: ' + str(exc)}])
