"""Bounded, evidence-referenced narration/diagram revision for development lessons.

This operator validates edit scope and render constraints. It does not certify the
truth of new explanations or the validity of a student diagnostic.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .common import digest, public_case, write_json
from .evidence import image_content
from .scene import PLAN_SYSTEM, inspect_layout, validate_plan

VERSION = 'bounded-evidence-lesson-revision-v2-explicit-brief'
FIELDS = {'title', 'narration', 'caption', 'slide_text', 'primitives'}
PROTECTED = {'source_visual', 'state_visual', 'spoken_units', 'nephron_path',
             'bond_cashflows', 'contact_pair'}


def validate_scope(plan, scope):
    if not isinstance(scope, dict) or set(scope) != {'scene_indices', 'max_total_words', 'evidence', 'objective'}:
        raise ValueError('revision scope requires scene_indices, max_total_words, evidence and objective')
    if not isinstance(scope['objective'], str) or not scope['objective'].strip() or len(scope['objective']) > 2000:
        raise ValueError('bounded explicit edit objective required')
    indices = scope['scene_indices']
    if not isinstance(indices, list) or not 1 <= len(indices) <= 3 or any(
        type(i) is not int or not 0 <= i < len(plan['scenes']) for i in indices
    ) or len(set(indices)) != len(indices):
        raise ValueError('1-3 distinct in-range scene indices required')
    if type(scope['max_total_words']) is not int or not 20 <= scope['max_total_words'] <= 600:
        raise ValueError('finite whole-lesson word budget required')
    evidence = scope['evidence']
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 12:
        raise ValueError('1-12 explicit evidence records required')
    ids = set()
    for row in evidence:
        if not isinstance(row, dict) or set(row) != {'id', 'kind', 'text', 'source'}:
            raise ValueError('evidence needs id, kind, text and source')
        if row['kind'] not in {'development_diagnostic', 'public_reference'}:
            raise ValueError('unsupported revision evidence kind')
        if any(not isinstance(row[k], str) or not row[k].strip() for k in ['id', 'text', 'source']):
            raise ValueError('nonempty evidence fields required')
        if row['id'] in ids:
            raise ValueError('duplicate evidence id')
        ids.add(row['id'])
    for i in indices:
        scene = plan['scenes'][i]
        if any(scene.get(k) for k in PROTECTED) or any(
            p.get('type') in {'piano_walk', 'chart', 'interval_keyboard'} for p in scene.get('primitives', [])
        ):
            raise ValueError('revision cannot override compiled/source/timed scenes')
    return ids


def apply_revision(plan, raw, case, scope):
    evidence_ids = validate_scope(plan, scope)
    if not isinstance(raw, dict) or set(raw) != {'replacements'} or not isinstance(raw['replacements'], list):
        raise ValueError('return replacements array only')
    if len(raw['replacements']) > len(scope['scene_indices']):
        raise ValueError('too many replacements')
    candidate = copy.deepcopy(plan)
    seen = set()
    for replacement in raw['replacements']:
        if not isinstance(replacement, dict) or set(replacement) != {'scene', 'updates', 'evidence_ids', 'reason'}:
            raise ValueError('replacement needs scene, updates, evidence_ids and reason')
        i = replacement['scene']
        if type(i) is not int or i not in scope['scene_indices'] or i in seen:
            raise ValueError('scene outside frozen edit scope or duplicated')
        seen.add(i)
        updates = replacement['updates']
        if not isinstance(updates, dict) or not {'narration', 'primitives'} <= set(updates) <= FIELDS:
            raise ValueError('revise narration and primitives together; other fields are protected')
        citations = replacement['evidence_ids']
        if not isinstance(citations, list) or not citations or any(
            not isinstance(c, str) or c not in evidence_ids for c in citations
        ) or len(set(citations)) != len(citations):
            raise ValueError('valid distinct revision evidence IDs required')
        if not isinstance(replacement['reason'], str) or not replacement['reason'].strip():
            raise ValueError('revision reason required')
        candidate['scenes'][i].update(copy.deepcopy(updates))
        if candidate['scenes'][i] == plan['scenes'][i]:
            raise ValueError('unchanged replacement must be omitted; an empty list can represent no justified revision')
    if sum(len(s['narration'].split()) for s in candidate['scenes']) > scope['max_total_words']:
        raise ValueError('whole-lesson narration exceeds frozen word budget')
    # The shared validator fills some defaults; do not let that mutate untouched scenes.
    validate_plan(copy.deepcopy(candidate), case)
    # Measured speech compilation is regenerated after an actual narrative edit.
    changed = [i for i, (a, b) in enumerate(zip(plan['scenes'], candidate['scenes'])) if a != b]
    if changed:
        candidate.pop('timing_compilation', None)
    return candidate, {'version': VERSION, 'status': 'changed' if changed else 'unchanged',
        'changed_scenes': changed, 'source_plan_hash': digest(plan),
        'candidate_plan_hash': digest(candidate), 'scope_hash': digest(scope),
        'replacements': copy.deepcopy(raw['replacements']),
        'validation_scope': 'Edit/schema scope only; evidence citations and semantic fidelity need review.',
        'semantic_acceptance': 'unverified'}


def propose_revision(client, case, plan, scope, frames, out):
    validate_scope(plan, scope)
    out = Path(out)
    context = {'public_task': public_case(case), 'original_plan': plan, 'revision_scope': scope,
        'policy': 'Development diagnostics are fallible leads, references supply public teaching content. Do not optimize scores or invent student learning.'}
    write_json(out / 'revision_input.json', context)
    content = [{'type': 'text', 'text': json.dumps(context, ensure_ascii=False)}]
    for frame in frames:
        content.extend(image_content(frame))
    # Reuse the renderer contract, not the conflicting whole-plan output schema.
    primitive_contract = PLAN_SYSTEM[PLAN_SYSTEM.index('Diagrams are rendered by code'):]
    system = primitive_contract + '''
You are executing the explicit revision_scope.objective, not revalidating unchanged
introductory facts. Public task constraints and supplied references bound this edit.
Return ONLY JSON {replacements:[{scene:zero_based_index,
updates:{narration:"English explanation",primitives:[...],title:"optional",caption:"optional",slide_text:"optional"},
evidence_ids:["supplied ID"],reason:"why this addresses a documented gap"}]}.
Only edit frozen scope.scene_indices, at most once each. Always revise narration and
primitives together, with coherent short labels and directly visible relationships.
You may return an empty replacements list if the evidence does not justify a revision.
No change to scene count, durations, original question, givens, constraints or other fields.
Keep all untouched scenes exactly. Respect the whole-lesson word budget. Explanations
must fit the stated audience and requested task; avoid unrelated syllabus content.
Use public_reference evidence for factual additions; a student's question is not factual
authority. Cite supplied evidence IDs only. Do not announce that a student has learned.
Use clear schematic objects and actual connecting arrows. A relation stated in a caption
does not replace its diagram. Distinguish viewpoint, altitude or stage when direction
changes; keep correct existing relations and required objects visible. Keep diagrams
inside the panel with readable labels and adequate contrast. Avoid label/arrow overlaps.
Prefer a compact explanation of the missing causal link over more terminology.
Only use the declarative primitives described above; no arbitrary code or backend override.
Do not use delayed appearance/motion unless it is justified by the narration timing.
Semantic/factual correctness will be checked separately after render; do not self-score.
'''
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}]
    for attempt in range(3):
        raw = client.chat(messages, purpose=f'lesson_revision:{case["id"]}:{attempt}', max_tokens=6500)
        write_json(out / f'raw_revision_{attempt}.json', raw)
        try:
            candidate, receipt = apply_revision(plan, raw, case, scope)
            issues = inspect_layout(candidate)
            if issues:
                raise ValueError('blocking layout findings: ' + json.dumps(issues[:8]))
            write_json(out / 'revision_receipt.json', receipt)
            return candidate, receipt
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out / f'revision_error_{attempt}.json', {'error': str(exc)})
            if attempt == 2:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct the bounded schema/layout issue; retain the same public facts and edit scope: ' + str(exc)}])
