"""A visible intermediate mechanism extracted from existing narrated content.

The four named stages cannot disappear into private link explanations during
rendering. Scientific validity and narration entailment still need review.
This experimental operator leaves audio and the surrounding lesson unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

from .causal_chain import compile_chain
from .common import digest, public_case, write_json

VERSION = 'explicit-mechanism-chain-v1'
ROLES = ('process', 'recipient_effect', 'mechanism', 'outcome')
REGION = (.54, .02, .42, .94)
EXTRACTIVE_VERSION = 'extractive-transfer-mechanism-v1'
EXTRACTIVE_ROLES = ('process', 'transfer', 'recipient', 'state_change', 'outcome')


def compile_extractive(raw, narration, references):
    """Only display selected narration spans; absent intermediate change is allowed."""
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError('existing narration required')
    if isinstance(raw, dict) and set(raw) == {'unsupported'}:
        if not isinstance(raw['unsupported'], str) or not 1 <= len(raw['unsupported'].strip()) <= 300:
            raise ValueError('bounded unsupported reason required')
        return None, {'version': EXTRACTIVE_VERSION, 'status': 'not_applicable',
                      'reason': raw['unsupported'], 'semantic_acceptance': 'unverified'}
    if not isinstance(raw, dict) or set(raw) != {*EXTRACTIVE_ROLES, 'links'}:
        raise ValueError('exact five extraction roles and links required, or one unsupported reason')
    for role in EXTRACTIVE_ROLES:
        value = raw[role]
        if role == 'state_change' and value is None:
            continue
        if not isinstance(value, str) or not 1 <= len(value) <= 34 or value != ' '.join(value.split()):
            raise ValueError(f'{role} requires a short contiguous narration span')
        if value not in narration:
            raise ValueError(f'{role} is absent from the original narration; select an exact span without paraphrasing')
    nodes = [{'id': 'process', 'label': raw['process']},
             {'id': 'recipient', 'label': raw['transfer'] + ' to ' + raw['recipient']}]
    if raw['state_change'] is not None:
        nodes.append({'id': 'state_change', 'label': raw['state_change']})
    nodes.append({'id': 'outcome', 'label': raw['outcome']})
    if not isinstance(raw['links'], list) or len(raw['links']) != len(nodes) - 1:
        raise ValueError(f'exactly {len(nodes) - 1} link warrants required for the selected stages')
    refs = {r['id']: r for r in references if r.get('kind') == 'public_reference'}
    links, quotes = [], []
    for i, link in enumerate(raw['links']):
        if not isinstance(link, dict) or set(link) != {'explanation', 'evidence_ids', 'source_quote'}:
            raise ValueError('link requires explanation, evidence_ids and exact source_quote')
        ids = link['evidence_ids']
        if not isinstance(ids, list) or not ids or any(not isinstance(v, str) or v not in refs for v in ids):
            raise ValueError('link must cite supplied public sources')
        quote = link['source_quote']
        if not isinstance(quote, str) or not 8 <= len(quote.strip()) <= 1000 or not any(
            quote in refs[k].get('verbatim_excerpt', refs[k].get('text', '')) for k in ids
        ):
            raise ValueError('source_quote must be an exact passage from a cited public source')
        links.append({'source': nodes[i]['id'], 'target': nodes[i + 1]['id'],
                      'explanation': link['explanation'], 'evidence_ids': ids})
        quotes.append({'link': i, 'quote': quote, 'evidence_ids': ids})
    chain = {'nodes': nodes, 'links': links}
    prims, layout = compile_chain(chain, references, region=REGION, max_nodes=4)
    return prims, {'version': EXTRACTIVE_VERSION, 'status': 'compiled', 'proposal_hash': digest(raw),
        'narration_hash': digest(narration), 'roles': {k: raw[k] for k in EXTRACTIVE_ROLES},
        'chain': chain, 'layout': layout, 'source_quotes': quotes,
        'semantic_acceptance': 'unverified',
        'checked_scope': 'Selected role strings occur in narration and are displayed; cited quote strings exist; topology and fit valid. Role meaning and quote entailment remain unverified.'}


def propose_extractive(client, case, narration, references, out):
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs or not isinstance(narration, str) or not narration.strip():
        raise ValueError('existing narration and public references required')
    out = Path(out)
    context = {'public_task': public_case(case), 'existing_scene_narration': narration,
               'public_references': refs}
    write_json(out / 'input.json', context)
    system = '''Extract a concise diagram of an already narrated transfer mechanism.
Return ONLY JSON with these exact fields: process, transfer, recipient, state_change,
outcome, links. Each of the five roles MUST be an exact contiguous case-sensitive
substring of existing_scene_narration, at most 34 characters. Select short spans
with their original wording; no paraphrasing or inferred extra forces/relations.
process names the initiating process. transfer names the quantity/material passed.
recipient names the entity receiving it. state_change names an intermediate change
already stated in that recipient. outcome names the resulting supported motion/effect.
The visible nodes are process; transfer + " to " + recipient; state_change; outcome.
Do not reuse the same event as both state_change and outcome. If no distinct state
change is stated, set state_change:null and use three nodes instead. If the other
required roles cannot be extracted faithfully, return only {"unsupported":"reason"}.
This refusal is valid; never invent a role just to fill the template.
links has one entry for each adjacent node pair, in order, each exactly:
{explanation:"bounded explanation supported by the provided material",
evidence_ids:["public source ID"],source_quote:"exact passage from a cited source"}.
Use three links with state_change, two without it. Quote complete relevant source
phrases, not isolated keywords; the quote must support the stated relation. Do not
introduce unspoken comparisons, assume scientific conditions not given, or make
a stronger causal claim. Keep labels short enough for one line.
No new narration, code, geometry, scores or student predictions. The existing full
lesson, exact audio and surrounding spatial diagram remain unchanged.'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'extractive_mechanism:{case["id"]}:{attempt}', max_tokens=2400)
        write_json(out / f'raw_{attempt}.json', raw)
        try:
            compile_extractive(raw, narration, refs)
            write_json(out / 'mechanism.json', raw)
            return raw
        except (ValueError, KeyError, TypeError) as exc:
            write_json(out / f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct this extraction/schema/fit issue using exact existing spans. '
                 'The null state_change and unsupported response remain available; do not invent content: ' + str(exc)}])


def compile_mechanism(raw, references):
    if not isinstance(raw, dict) or set(raw) != {*ROLES, 'links'}:
        raise ValueError('exact process, recipient_effect, mechanism, outcome and links fields required')
    for role in ROLES:
        text = raw[role]
        if not isinstance(text, str) or not 1 <= len(text) <= 34 or text != ' '.join(text.split()):
            raise ValueError(f'{role} requires a short plain label of 1..34 characters')
    links = raw['links']
    if not isinstance(links, list) or len(links) != 3:
        raise ValueError('exactly three adjacent relation warrants required')
    chain = {'nodes': [{'id': role, 'label': raw[role]} for role in ROLES], 'links': []}
    for i, link in enumerate(links):
        if not isinstance(link, dict) or set(link) != {'explanation', 'evidence_ids'}:
            raise ValueError('each link requires explanation and evidence_ids only')
        chain['links'].append({'source': ROLES[i], 'target': ROLES[i + 1], **link})
    primitives, layout = compile_chain(chain, references, region=REGION, max_nodes=4)
    return primitives, {'version': VERSION, 'proposal_hash': digest(raw), 'chain': chain,
        'layout': layout, 'all_roles_displayed_verbatim': True,
        'semantic_acceptance': 'unverified',
        'checked_scope': 'Four visible role labels, public citation IDs, adjacent topology and readable geometric fit only.'}


def propose_mechanism(client, case, narration, references, out):
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError('existing narration required')
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs:
        raise ValueError('public references required')
    context = {'public_task': public_case(case), 'existing_scene_narration': narration,
               'public_references': refs}
    out = Path(out)
    write_json(out / 'input.json', context)
    system = '''Turn the existing narrated teaching mechanism into four short visible
stages. Return ONLY JSON with exactly these fields:
{process:"initiating process",recipient_effect:"what changes in the receiving entity",
mechanism:"intermediate reason why that change produces the outcome",outcome:"supported result",
links:[{explanation:"why process leads to recipient_effect",evidence_ids:["public source ID"]},
{explanation:"why recipient_effect leads to mechanism",evidence_ids:["public source ID"]},
{explanation:"why mechanism supports outcome",evidence_ids:["public source ID"]}]}.
The four stage labels are rendered verbatim, in that order, in connected boxes.
Each must be 1..34 characters, preferably under 28 characters, and fit one readable
line. Keep the receiving entity explicit where otherwise ambiguous. The mechanism
label must express the intermediate explanation, not merely repeat the process or
outcome. Put this reason in the visible label, not only in an internal link warrant.
Extract the explanation already present in the narration, using public references
to check it. Do not invent a new mechanism, transfer domain assumptions, replace
the original lesson, or claim a complete physical simulation. Qualify causality
appropriately to the narrated context. Cite the most directly relevant supplied
passage for each relation. Do not return narration edits, coordinates, display
instructions, scores, student predictions or hidden answer material.'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'mechanism_chain:{case["id"]}:{attempt}', max_tokens=1800)
        write_json(out / f'raw_{attempt}.json', raw)
        try:
            compile_mechanism(raw, refs)
            write_json(out / 'mechanism.json', raw)
            return raw
        except (ValueError, KeyError, TypeError) as exc:
            write_json(out / f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct this schema or label-fit issue using the same narrated facts. '
                 'Do not drop a role or add new content. Keep labels short enough for a single line: ' + str(exc)}])
