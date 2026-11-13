"""Bind scene wording to the compiled camera/strokes before resynthesizing speech.

The receipts establish rendering facts, not domain truth. Language still needs
independent media evaluation; citations alone do not certify semantic support.
"""
import copy
import json
from pathlib import Path

from PIL import Image

from .common import digest, public_case, write_json
from .evidence import image_content
from .scene import validate_plan
from .spatial_graph import compile_graph, draw_graph

VERSION = 'compiled-view-narration-v1'
TEXT_FIELDS = {'title', 'caption', 'slide_text', 'narration'}


def view_facts(plan, case, scenes):
    facts = {}
    if not scenes or len(set(scenes)) != len(scenes):
        raise ValueError('nonempty distinct scene indices required')
    for i in scenes:
        if type(i) is not int or not 0 <= i < len(plan['scenes']):
            raise ValueError('in-range scene required')
        primitives = plan['scenes'][i]['primitives']
        if len(primitives)==1 and primitives[0].get('type')=='spatial_correspondence':
            from .spatial_correspondence import view_facts as paired_facts
            record,check=paired_facts(primitives[0],case['prompt_text'])
            for j,stroke in enumerate(record['strokes']):
                facts[f'S{i}.stroke{j}']={'scene':i,'kind':'actual_paired_stroke',**stroke,
                    'meaning_limit':'Toward/away depends on the actual solid/hashed wedge; plain line is not exact coplanarity. Distinguish initial and product panels.'}
            facts[f'S{i}.correspondence']={'scene':i,'kind':'checked_endpoint_correspondence','check':check,
                'same_camera_and_scale':True,'retained_labels':primitives[0]['roles']['retained'],
                'meaning_limit':'Both endpoints are simultaneously visible. Matching labels/colors show identity, not motion. Separate LG arrow is a departure cue, not a simulated reaction trajectory. No CIP/R/S assignment.'}
            continue
        if len(primitives) != 1 or primitives[0].get('type') != 'spatial_graph':
            raise ValueError('only existing compiled spatial scenes supported')
        graph = primitives[0]['graph']
        checks = compile_graph(graph, case['prompt_text'])['checks']
        receipt = draw_graph(Image.new('RGB', (1024, 576), 'white'), graph)
        labels = {n['id']:n['label'] for n in graph['nodes']}
        for j, stroke in enumerate(receipt['strokes']):
            facts[f'S{i}.stroke{j}'] = {'scene':i, 'kind':'actual_rendered_stroke', **stroke,
                'source_label':labels[stroke['source']], 'target_label':labels[stroke['target']],
                'meaning_limit':'Solid/hashed wedges encode toward/away from the source. A plain line alone does not prove exact coplanarity. Arrow source->target is direction of travel, not the vector from center to the approaching object.'}
        for j, check in enumerate(checks):
            facts[f'S{i}.relation{j}'] = {'scene':i, 'kind':'declared_checked_geometry', **check,
                'meaning_limit':'Model-declared node roles are unverified. Opposite_sides compares two positions relative to a common center; it does not say an incoming vector and outgoing bond vector point opposite ways. These checks do not establish a reaction or transition-state mechanism.'}
    return facts


def apply(plan, case, raw, scenes, facts, *, max_words=180, scene_word_limits=None):
    if not isinstance(raw, dict) or set(raw) != {'edits'} or not isinstance(raw['edits'], list):
        raise ValueError('edits array required')
    candidate, seen = copy.deepcopy(plan), set()
    for edit in raw['edits']:
        if not isinstance(edit, dict) or set(edit) != {'scene','text','fact_ids','reason'}:
            raise ValueError('scene/text/fact_ids/reason fields required')
        i = edit['scene']
        if type(i) is not int or i not in scenes or i in seen:
            raise ValueError('scene outside scope or repeated')
        seen.add(i)
        updates = edit['text']
        if not isinstance(updates, dict) or not {'narration'} <= set(updates) <= TEXT_FIELDS:
            raise ValueError('only narration/title/caption/slide_text may change')
        if any(not isinstance(v, str) or not v.strip() for v in updates.values()):
            raise ValueError('nonempty text fields required')
        ids = edit['fact_ids']
        if not isinstance(ids, list) or not ids or any(not isinstance(k,str) or k not in facts or facts[k]['scene'] != i for k in ids):
            raise ValueError('cite render facts belonging to this scene')
        if not isinstance(edit['reason'], str) or not edit['reason'].strip():
            raise ValueError('nonempty reason required')
        candidate['scenes'][i].update(copy.deepcopy(updates))
        if scene_word_limits and len(candidate['scenes'][i]['narration'].split()) > scene_word_limits[i]:
            raise ValueError(f'scene {i} exceeds its fixed-slot narration word limit')
    if sum(len(s['narration'].split()) for s in candidate['scenes']) > max_words:
        raise ValueError('whole-lesson narration exceeds word budget')
    validate_plan(copy.deepcopy(candidate), case)
    for i, (old, new) in enumerate(zip(plan['scenes'],candidate['scenes'])):
        allowed = TEXT_FIELDS if i in seen else set()
        if {k:v for k,v in old.items() if k not in allowed} != {k:v for k,v in new.items() if k not in allowed}:
            raise ValueError('geometry, timing or untouched scene changed')
    if seen: candidate.pop('timing_compilation',None)
    return candidate, {'version':VERSION,'edited_scenes':sorted(seen), 'source_hash':digest(plan),
        'candidate_hash':digest(candidate),'facts_hash':digest(facts),'edits':copy.deepcopy(raw['edits']),
        'semantic_acceptance':'unverified; fact IDs validate provenance, not truth of the wording'}


def propose(client, case, plan, scenes, frames, references, out, *, max_words=180, scene_word_limits=None):
    out = Path(out)
    facts = view_facts(plan,case,scenes)
    context = {'public_task':public_case(case),'plan':plan,'editable_scenes':scenes,
        'actual_render_facts':facts,'public_references':references,'max_whole_lesson_words':max_words,
        'fixed_slot_scene_word_limits':scene_word_limits}
    write_json(out/'input.json',context)
    content = [{'type':'text','text':json.dumps(context,ensure_ascii=False)}]
    for frame in frames: content.extend(image_content(frame))
    system = '''Revise camera-dependent teaching wording AFTER geometry compilation.
Read actual stroke facts and the supplied frames; do not guess which bonds lie in
the plane. Keep geometry and all other scenes unchanged. Explain compact symbols
without unrelated theory. Correct every affected caption, title, slide_text and
narration. A hashed wedge means away, not in plane. Solid wedge means toward.
Ordinary lines can reflect small depth under this renderer and do not establish
exact coplanarity. Opposite sides describes positions from the SAME center;
incoming Nu->C and outgoing C->LG vectors can be parallel, not opposite. Do not
describe the whole transition state as linear or claim these code checks certify
reaction chemistry. The current tetrahedral frame is not a transition-state model.
Use references only for their scoped domain facts. No private answers, scores or
invented empirical observations. Citations do not excuse incorrect statements.
Return JSON only {edits:[{scene:zero_based_index,text:{narration:"English speech",
title:"optional",caption:"optional",slide_text:"optional"},fact_ids:["actual ID"],
reason:"specific inconsistency corrected"}]}. Edit each permitted scene at most
once; preserve durations. Honor any fixed_slot_scene_word_limits. Speech is measured
inside those original slots; extra speech cannot extend a scene or cut another. Return
an empty list if no justified change exists. Do not regenerate diagrams.'''
    if any(f.get('kind')=='actual_paired_stroke' for f in facts.values()):
        system += '''
For a paired endpoint diagram, revise speech/caption to guide the viewer through
the actual comparison: distinguish the initial and product panels, use matching
retained labels/colors, and explain the departure cue if present. Relate the
visible depth marks to the comparison without claiming an animated reaction path.
The old generic inversion slogan alone does not guide this new two-panel visual.
Keep the word/time budget; select the most informative concrete relations. No
R/S assignment for unspecified substituents. Do not change noneditable scenes.
'''
    messages = [{'role':'system','content':system},{'role':'user','content':content}]
    for attempt in range(2):
        raw=client.chat(messages,purpose=f'compiled_view_narration:{case["id"]}:{attempt}',max_tokens=3500)
        write_json(out/f'raw_{attempt}.json',raw)
        try:
            candidate,receipt=apply(plan,case,raw,scenes,facts,max_words=max_words,scene_word_limits=scene_word_limits)
            write_json(out/'receipt.json',receipt)
            return candidate,receipt
        except (ValueError,KeyError,TypeError) as exc:
            write_json(out/f'error_{attempt}.json',{'error':str(exc)})
            if attempt: raise
            messages.extend([{'role':'assistant','content':json.dumps(raw)},
                             {'role':'user','content':'Correct this schema/scope failure: '+str(exc)}])
