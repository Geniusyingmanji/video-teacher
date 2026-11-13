"""Small semantic chains compiled into explicit connected instructional diagrams.

Only the edge topology and its displayed geometry are checked here. Supplied
citations, causal explanations, and a model's reading of narration remain fallible.
This experimental operator is not part of the default generation pipeline.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from .common import digest, public_case, write_json
from .scene import font

VERSION = 'cited-causal-chain-v2-variable-height'
FOUR_NODE_VERSION = 'cited-causal-chain-v3-four-node'
NARRATED_VERSION = 'cited-narration-and-chain-v1'
PANEL_W, PANEL_H = 896, 302


def validate_chain(chain, references, *, max_nodes=3):
    if type(max_nodes) is not int or max_nodes not in (3, 4):
        raise ValueError('node budget must be3or4')
    refs = {r['id'] for r in references if r.get('kind') == 'public_reference'}
    if not refs:
        raise ValueError('public factual references required')
    if not isinstance(chain, dict) or set(chain) != {'nodes', 'links'}:
        raise ValueError('exact nodes and links fields required')
    nodes, links = chain['nodes'], chain['links']
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= max_nodes:
        raise ValueError(f'two to {max_nodes} ordered nodes required')
    ids, labels = [], set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'id', 'label'}:
            raise ValueError('node requires id and label only')
        if not isinstance(node['id'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,15}', node['id']) or node['id'] in ids:
            raise ValueError('distinct short node IDs required')
        label = node['label']
        if not isinstance(label, str) or not 1 <= len(label) <= 48 or label != ' '.join(label.split()):
            raise ValueError('single-line plain labels of at most 48 characters required')
        if label.casefold() in labels:
            raise ValueError('distinct node labels required')
        ids.append(node['id']); labels.add(label.casefold())
    if not isinstance(links, list) or len(links) != len(nodes) - 1:
        raise ValueError('every adjacent node pair needs exactly one link')
    for i, link in enumerate(links):
        if not isinstance(link, dict) or set(link) != {'source', 'target', 'explanation', 'evidence_ids'}:
            raise ValueError('link requires source, target, explanation and evidence_ids')
        if (link['source'], link['target']) != (ids[i], ids[i + 1]):
            raise ValueError('links must follow the ordered adjacent node IDs')
        reason = link['explanation']
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 240:
            raise ValueError('bounded causal explanation required')
        citations = link['evidence_ids']
        if not isinstance(citations, list) or not citations or any(
            not isinstance(c, str) or c not in refs for c in citations
        ) or len(citations) != len(set(citations)):
            raise ValueError('links must cite distinct supplied public references')


def _wrap(label, width_px, size):
    face = font(size)
    lines = []
    for word in label.split():
        if face.getlength(word) > width_px:
            raise ValueError('a label word is too wide; do not shrink or truncate it')
        if lines and face.getlength(lines[-1] + ' ' + word) <= width_px:
            lines[-1] += ' ' + word
        else:
            lines.append(word)
    if len(lines) > 2:
        raise ValueError('label requires more than two readable lines')
    return lines


def compile_chain(chain, references, *, region=(.54, .04, .42, .90), max_nodes=3):
    """Place every relation at the boundaries of its actual labeled node boxes."""
    validate_chain(chain, references, max_nodes=max_nodes)
    if not isinstance(region, (list, tuple)) or len(region) != 4 or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in region
    ):
        raise ValueError('finite x,y,width,height region required')
    x, y, w, h = region
    if x < .02 or y < .02 or w <= 0 or h <= 0 or x + w > .98 or y + h > .98:
        raise ValueError('chain region outside diagram safe area')
    size, pad, line_height = 24, 12, 28
    labels = [_wrap(n['label'], w * PANEL_W - 2 * pad, size) for n in chain['nodes']]
    heights = [len(lines) * line_height + 2 * pad for lines in labels]
    n = len(labels)
    gap = (h * PANEL_H - sum(heights)) / (n - 1)
    if gap < 24:
        raise ValueError('region too short for readable labels and distinct connectors')
    prims, nodes = [], []
    for i, (node, lines, box_h) in enumerate(zip(chain['nodes'], labels, heights)):
        top = y + (sum(heights[:i]) + i * gap) / PANEL_H
        cy = top + box_h / (2 * PANEL_H)
        prims.append({'type': 'rect', 'x': x, 'y': top, 'w': w, 'h': box_h / PANEL_H,
                      'color': '#1868ae', 'fill': '#edf5fb'})
        for j, line in enumerate(lines):
            prims.append({'type': 'text', 'x': x + w / 2,
                          'y': cy + (j - (len(lines) - 1) / 2) * line_height / PANEL_H,
                          'text': line, 'font_size': size, 'color': '#14283e', 'align': 'center'})
        nodes.append({'id': node['id'], 'label': node['label'],
                      'bbox': [x, top, x + w, top + box_h / PANEL_H]})
    edges = []
    for i, link in enumerate(chain['links']):
        start = [x + w / 2, nodes[i]['bbox'][3] + 3 / PANEL_H]
        end = [x + w / 2, nodes[i + 1]['bbox'][1] - 3 / PANEL_H]
        index = len(prims)
        prims.append({'type': 'arrow', 'x': start[0], 'y': start[1],
                      'x2': end[0], 'y2': end[1], 'color': '#a54814'})
        edges.append({**copy.deepcopy(link), 'primitive_index': index,
                      'start': start, 'end': end})
    return prims, {'version': FOUR_NODE_VERSION if max_nodes == 4 else VERSION,
        'chain_hash': digest(chain), 'region': list(region),
        'nodes': nodes, 'links': edges, 'primitives_hash': digest(prims),
        'semantic_acceptance': 'unverified',
        'checked_scope': 'Adjacent node topology, readable fit and connector endpoints only.'}


def propose_chain(client, case, narration, objective, references, out):
    """Extract a tiny semantic plan; do not expose coordinates or old full plans."""
    out = Path(out)
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError('existing narration required')
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs:
        raise ValueError('public factual references required')
    context = {'public_task': public_case(case), 'existing_narration': narration,
               'objective': objective, 'public_references': refs}
    write_json(out / 'input.json', context)
    system = '''Represent the supplied narration's requested causal bridge as a small
instructional chain. Return ONLY JSON {nodes:[{id:"N1",label:"short readable concept"},...],
links:[{source:"N1",target:"N2",explanation:"why this causal connection follows from the references",
evidence_ids:["supplied public source ID"]},...]}.
Use exactly two or three nodes in causal order, and one directed link for each adjacent pair.
Labels are at most 48 characters and preferably fewer than 30. Include the receiving
entity when an arrow would otherwise leave unclear who gets heat, material or force.
Use references to check facts, not to add topics absent from the existing narration.
A causal link is not merely a temporal sequence. Avoid stronger necessity/sufficiency
claims than the sources support. State each link's warrant in its explanation.
Do not write coordinates, drawing code, new narration, rubric ratings or student claims.
Do not imply this compact chain is a complete scientific model. The caller preserves
the existing full lesson and draws the chain beside its required spatial diagram.'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'causal_chain:{case["id"]}:{attempt}', max_tokens=1600)
        write_json(out / f'raw_{attempt}.json', raw)
        try:
            compile_chain(raw, refs)
            write_json(out / 'chain.json', raw)
            return raw
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out / f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct the schema only, preserving facts and cited sources: ' + str(exc)}])


def validate_narrated_chain(raw, references, original_narration, max_words):
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite scene narration budget required')
    if not isinstance(raw, dict) or set(raw) != {'narration', 'nodes', 'links'}:
        raise ValueError('exact narration, nodes and links fields required')
    narration = raw['narration']
    if not isinstance(narration, str) or not 5 <= len(narration.split()) <= max_words:
        raise ValueError(f'narration must have 5..{max_words} words')
    if ' '.join(narration.split()) == ' '.join(original_narration.split()):
        raise ValueError('unchanged narration is a no-op, not a content revision')
    chain = {k: copy.deepcopy(raw[k]) for k in ('nodes', 'links')}
    # A fit failure is explicit; no automatic font shrinking or semantic rewrite.
    compile_chain(chain, references)
    return chain


def propose_narrated_chain(client, case, narration, objective, references, max_words, out):
    """A bounded content edit: generate prose and semantic links, never coordinates."""
    refs = [r for r in references if r.get('kind') == 'public_reference']
    if not refs or not isinstance(narration, str) or not narration.strip():
        raise ValueError('original narration and public references required')
    if type(max_words) is not int or not 5 <= max_words <= 90:
        raise ValueError('finite scene narration budget required')
    out = Path(out)
    context = {'public_task': public_case(case), 'original_scene_narration': narration,
               'objective': objective, 'public_references': refs, 'max_narration_words': max_words}
    write_json(out / 'input.json', context)
    system = '''Revise one short English teaching explanation according to the explicit
objective and supplied public references. Return ONLY JSON with exactly these fields:
{narration:"revised English spoken explanation",nodes:[{id:"N1",label:"short concept"},...],
links:[{source:"N1",target:"N2",explanation:"source-grounded reason for this causal link",
evidence_ids:["supplied public source ID"]},...]}.
Write five to max_narration_words spoken words. Preserve the introduction's required
objects while adding the missing mechanism. Do not merely copy or validate the old
narration. Keep language suitable for the stated audience. Do not add other topics.
Give two or three nodes in causal order and exactly one link per adjacent pair. Use
short labels, preferably fewer than 30 characters (hard maximum 48). Name the recipient
of heat/material/force explicitly where omission would make a relationship ambiguous.
The nodes must express the same causal mechanism as your narration. A causal link is
not merely a chronological sequence; cite source IDs and explain why each link holds.
Avoid turning supportive mechanisms into unconditional necessity/sufficiency claims.
Code will place readable boxes and connect their edges beside a spatial schematic.
Do not return drawing coordinates, a full lesson plan, scores or claims about learning.
Only revise this one scene; the caller retains the rest of the lesson unchanged.'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'narrated_chain:{case["id"]}:{attempt}', max_tokens=1800)
        write_json(out / f'raw_{attempt}.json', raw)
        try:
            chain = validate_narrated_chain(raw, refs, narration, max_words)
            write_json(out / 'narrated_chain.json', raw)
            return raw['narration'], chain
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out / f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': 'Correct this bounded output/fit issue using the same factual scope: ' + str(exc)}])
