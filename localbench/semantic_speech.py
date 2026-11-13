"""Natural speech with explicit surface witnesses for required semantic slots.

Span existence and source IDs are checkable; semantic entailment is not. A model
can cite an irrelevant phrase, so a valid record never certifies the explanation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import digest, public_case, write_json

VERSION = 'semantic-speech-witness-v1'
SLOTS = ('context', 'process', 'transfer', 'recipient', 'outcome', 'mechanism')
EDIT_VERSION = 'source-bound-speech-edits-v1'


def compile_edits(roles, program, max_words):
    """Execute externally authored exact-span edits using frozen role values.

    An edit program supplies intent; the compiler does not discover or certify
    it. Source text and operations are returned in the receipt for inspection.
    """
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite speech word budget required')
    if not isinstance(program, list) or len(program) > 4:
        raise ValueError('at most four explicit speech operations required')
    values = {k: roles[k] for k in ('process','transfer','recipient','outcome')}
    if any(not isinstance(v,str) or not v.strip() for v in values.values()):
        raise ValueError('frozen nonempty role values required')
    original = roles['narration']
    if not isinstance(original,str) or not original.strip():
        raise ValueError('frozen source narration required')
    current, log = original, []

    def expand(template):
        if not isinstance(template,str) or not template.strip():
            raise ValueError('nonempty edit template required')
        fields = re.findall(r'\{([^{}]*)\}',template)
        remainder = re.sub(r'\{[^{}]*\}','',template)
        if set(fields)-set(values) or '{' in remainder or '}' in remainder:
            raise ValueError('edit placeholders must be exact frozen role names')
        return template.format_map(values)

    for operation in program:
        if not isinstance(operation,dict):raise ValueError('speech operation must be an object')
        if operation.get('op')=='replace' and set(operation)=={'op','before','after'}:
            before,after = expand(operation['before']),expand(operation['after'])
            if current.count(before)!=1:raise ValueError('replacement anchor must occur exactly once')
            if before==after:raise ValueError('replacement is a no-op')
            current=current.replace(before,after,1)
            log.append({'op':'replace','before':before,'after':after,
                        'scope':'Externally authored phrase template expanded from frozen roles.'})
        elif operation.get('op')=='append_relation' and set(operation)=={'op','index'}:
            index=operation['index']
            if type(index) is not int or index not in (0,1):raise ValueError('relation index must be0or1')
            text=roles['relation_explanations'][index]
            if not isinstance(text,str) or not text.strip():raise ValueError('nonempty frozen relation required')
            if text in current:raise ValueError('relation text already present')
            current=current.rstrip()+' '+text
            log.append({'op':'append_relation','source_field':f'relation_explanations[{index}]','text':text})
        else:raise ValueError('unsupported speech operation')
    if not 5<=len(current.split())<=max_words:
        raise ValueError('edited speech outside word budget; no relation may be dropped')
    return current,{'version':EDIT_VERSION,'source_hash':digest(roles),'program_hash':digest(program),
        'original_narration':original,'narration':current,'operations':log,
        'changed':current!=original,'word_count':len(current.split()),
        'semantic_acceptance':'unverified','program_intent_source':'external; not discovered by compiler'}


def compile_speech(raw, references, max_words):
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite speech word budget required')
    if not isinstance(raw, dict) or set(raw) != {'narration', 'witnesses'}:
        raise ValueError('exact narration and witnesses fields required')
    narration = raw['narration']
    if not isinstance(narration, str) or narration != ' '.join(narration.split()):
        raise ValueError('normalized nonempty narration required')
    if not 5 <= len(narration.split()) <= max_words:
        raise ValueError('speech outside word budget; do not silently delete a required relation')
    witnesses = raw['witnesses']
    if not isinstance(witnesses, dict) or set(witnesses) != set(SLOTS):
        raise ValueError('all context, role and mechanism witnesses required')
    ids = {r['id'] for r in references if r.get('kind') == 'public_reference'}
    checks = {}
    for slot, witness in witnesses.items():
        if not isinstance(witness, dict) or set(witness) != {'quote', 'evidence_ids'}:
            raise ValueError(f'{slot}: exact quote and evidence_ids required')
        quote, sources = witness['quote'], witness['evidence_ids']
        if not isinstance(quote, str) or not quote.strip() or quote not in narration:
            raise ValueError(f'{slot}: quote must occur verbatim in spoken narration')
        if not isinstance(sources, list) or any(not isinstance(x, str) for x in sources):
            raise ValueError(f'{slot}: evidence_ids must be a string list')
        if len(set(sources)) != len(sources) or set(sources) - ids:
            raise ValueError(f'{slot}: unknown or duplicate public reference')
        if slot != 'context' and not sources:
            raise ValueError(f'{slot}: a public reference is required')
        # Record every occurrence rather than silently selecting one repetition.
        starts = [i for i in range(len(narration)) if narration.startswith(quote, i)]
        checks[slot] = {'quote': quote, 'character_spans': [[i, i+len(quote)] for i in starts],
                        'evidence_ids': sources, 'semantic_support': 'unverified'}
    return narration, {'version': VERSION, 'input_hash': digest(raw),
        'word_count': len(narration.split()), 'witnesses': checks,
        'narration_authorship': 'supplied natural-language realization; no compiler paraphrase',
        'semantic_acceptance': 'unverified',
        'checked_scope': 'Required slots have exact spoken-text witnesses and valid source IDs. '
                         'Neither quote meaning nor source entailment has been certified.'}


def propose_speech(client, case, roles, context, references, max_words, out):
    out = Path(out)
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs or not isinstance(context, str) or not context.strip():
        raise ValueError('public sources and introduction required')
    payload = {'public_task': public_case(case), 'frozen_roles': roles,
               'original_introduction': context, 'public_sources': refs,
               'max_words': max_words, 'required_slots': list(SLOTS)}
    write_json(out / 'input.json', payload)
    system = '''Write concise fluent English speech for the first scene of this existing
lesson. Return JSON with exactly narration and witnesses. narration is a single
string of at most max_words whitespace-separated words. witnesses is an object
with exactly context, process, transfer, recipient, outcome, mechanism. Each value
is {quote:"exact nonempty substring in narration", evidence_ids:["public source ID"]}.
Every slot except context needs a source ID. Context may use an empty ID list.
The original introductory facts must remain, but wording may be shortened. The
four frozen role values describe the diagram; express their meanings accurately
in fluent speech without mechanically repeating identical transfer statements.
Explicitly explain WHY the transfer supports the outcome (the mechanism), rather
than merely restating that it does. Use the supplied relation explanations only
to the extent supported by public sources. Keep the recipient explicit. Preserve
the named participants, qualifiers and scientific scope; do not invent quantities.
Your quotes must actually express their assigned meanings, not just contain a
related noun. A keyword or a generic 'supports' clause alone is not a mechanism.
You may cite the same meaningful phrase for related slots. No scores, graph,
coordinates, full lesson, internal reasoning or unsupported pedagogical claims.
This is only a spoken surface realization; the rest of the lesson is unchanged.'''
    messages = [{'role':'system','content':system},
                {'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages,purpose=f'semantic_speech:{case["id"]}:{attempt}',max_tokens=1600)
        write_json(out / f'raw_{attempt}.json',raw)
        try:
            narration, receipt = compile_speech(raw,refs,max_words)
            write_json(out / 'realization.json',raw)
            write_json(out / 'compilation.json',receipt)
            return narration, receipt
        except (ValueError,TypeError,KeyError) as exc:
            write_json(out / f'error_{attempt}.json',{'error':str(exc)})
            if attempt:raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                {'role':'user','content':'Correct this structure/word-budget issue, preserving the scientific content: '+str(exc)}])
