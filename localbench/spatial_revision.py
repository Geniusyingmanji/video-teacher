"""Scene-scoped symbolic geometry repair; no reaction or semantic certification."""
import copy
import json
from pathlib import Path

from .common import digest, public_case, write_json
from .lesson_revision import PROTECTED
from .scene import inspect_layout, validate_plan
from .spatial_plan import SYSTEM as SPATIAL_SYSTEM, compile_plan

VERSION = 'scene-scoped-spatial-revision-v1'
TEXT_FIELDS = {'title', 'caption', 'slide_text', 'narration'}


def apply(plan, case, raw, allowed_scenes, *, max_words=180):
    if not allowed_scenes or any(type(i) is not int or not 0 <= i < len(plan['scenes']) for i in allowed_scenes):
        raise ValueError('explicit in-range editable scene indices required')
    if public_case(case).get('public_attachments'):
        raise ValueError('cannot replace required source media')
    if not isinstance(raw, dict) or set(raw) != {'replacements'} or not isinstance(raw['replacements'], list):
        raise ValueError('replacements array required')
    candidate, seen = copy.deepcopy(plan), set()
    for row in raw['replacements']:
        if not isinstance(row, dict) or set(row) != {'scene', 'scope_quote', 'reason', 'text', 'spec'}:
            raise ValueError('scene/scope_quote/reason/text/spec fields required')
        i = row['scene']
        if type(i) is not int or i not in allowed_scenes or i in seen:
            raise ValueError('scene outside scope or repeated')
        seen.add(i)
        if any(candidate['scenes'][i].get(k) for k in PROTECTED):
            raise ValueError('cannot override protected scene')
        if not isinstance(row['scope_quote'], str) or not row['scope_quote'].strip() or row['scope_quote'] not in case['prompt_text']:
            raise ValueError('exact public-task scope quote required')
        if not isinstance(row['reason'], str) or not row['reason'].strip():
            raise ValueError('nonempty revision reason required')
        text = row['text']
        if not isinstance(text, dict) or not {'narration'} <= set(text) <= TEXT_FIELDS:
            raise ValueError('narration and optional title/caption/slide_text only')
        if any(not isinstance(v, str) or not v.strip() for v in text.values()):
            raise ValueError('nonempty text required')
        spec = row['spec']
        if not isinstance(spec, dict) or not isinstance(spec.get('nodes'), list):
            raise ValueError('symbolic spec nodes required')
        if any(not isinstance(n, dict) or not isinstance(n.get('label'), str) or not 1 <= len(n['label']) <= 4 for n in spec['nodes']):
            raise ValueError('compact node symbols must have1..4characters; expand roles in narration')
        candidate['scenes'][i].update(copy.deepcopy(text))
        candidate['scenes'][i]['primitives'] = [{'type': 'symbolic_spatial_graph', 'spec': copy.deepcopy(spec)}]
    if sum(len(s['narration'].split()) for s in candidate['scenes']) > max_words:
        raise ValueError('whole-lesson narration exceeds frozen word budget')
    # Existing compiled/source scenes are not edited. Only fresh symbolic scenes compile.
    compiled, receipt = compile_plan(candidate, public_case(case))
    if {r['scene'] for r in receipt['constructions']} != seen:
        raise ValueError('unexpected symbolic scene outside revision scope')
    validate_plan(copy.deepcopy(compiled), case)
    for i in range(len(plan['scenes'])):
        if i not in seen and compiled['scenes'][i] != plan['scenes'][i]:
            raise ValueError('untouched scene changed')
    if seen:
        compiled.pop('timing_compilation', None)
    return compiled, {'version': VERSION, 'changed_scenes': sorted(seen),
        'status': 'changed' if seen else 'unchanged', 'source_hash': digest(plan),
        'candidate_hash': digest(compiled), 'replacements': copy.deepcopy(raw['replacements']),
        'geometry': receipt, 'semantic_scope_alignment': 'unverified'}


def propose(client, case, plan, references, diagnostics, out, *, allowed_scenes, max_words=180):
    out = Path(out)
    data = {'public_task': public_case(case), 'original_plan': plan,
            'editable_scenes': [{'index': i, 'scene': plan['scenes'][i]} for i in allowed_scenes],
            'public_references': references, 'development_diagnostics': diagnostics,
            'max_whole_lesson_words': max_words}
    write_json(out/'input.json', data)
    system = SPATIAL_SYSTEM + '''
Revise only the indexed scenes of the supplied complete narrated lesson. Preserve
each scene's teaching phase. Use short1..4character node symbols so labels fit;
explain their roles in narration/slide_text. Do not put long names in node circles.
For each revised scene supply one symbolic spec; code constructs coordinates,
chooses a readable view and displays a wedge/hashed-wedge legend. Tie narration to
those depth conventions. A plain dashed partial bond is not a hashed depth wedge.
The constructor supports initial tetrahedral geometry and opposite-side approach,
NOT transition states or inverted products. Do not imply it verifies these later
phases. Preserve unchanged scenes and all durations; speech is measured afterward.
Do not supply coordinates, arbitrary code, private answers or self-scores.
Return ONLY JSON {replacements:[{scene:zero_based_index,scope_quote:"exact public
task span",reason:"bounded reason",text:{title:"short title",caption:"short caption",
slide_text:"short explanation",narration:"English speech"},spec:{nodes,links,constraints}}]}.
Each replacement requires narration, other text fields optional. An empty list is
allowed when no supported correction is justified. Diagnostics are fallible leads;
public task and references bound additions. Do not rewrite the whole lesson.
'''
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(data, ensure_ascii=False)}]
    for attempt in range(2):
        raw = client.chat(messages, purpose=f'scoped_spatial_revision:{case["id"]}:{attempt}', max_tokens=6000)
        write_json(out/f'raw_{attempt}.json', raw)
        try:
            result, receipt = apply(plan, case, raw, allowed_scenes, max_words=max_words)
            issues = inspect_layout(result)
            if issues:
                raise ValueError('blocking layout issues: ' + json.dumps(issues[:6]))
            write_json(out/'receipt.json', receipt)
            return result, receipt
        except (ValueError, TypeError, KeyError) as exc:
            write_json(out/f'error_{attempt}.json', {'error': str(exc)})
            if attempt:
                raise
            messages.extend([{'role': 'assistant', 'content': json.dumps(raw)},
                             {'role': 'user', 'content': 'Correct the construction/schema failure: ' + str(exc)}])
