"""Validate and compile all declared source edits into deterministic Manim operations."""
import json
from generation.strict_video_contract import validate_regions, region_union_area


def validate_plan(plan, contract):
    boxes = validate_regions(plan.get('source_edit_regions', []), True, contract['source_size_pixels'])
    frozen = contract.get('quality_feedback', {}).get('frozen_source_edit_regions')
    if frozen is not None and boxes != frozen:
        raise ValueError('changed validated frozen source target boxes')
    operations = plan.get('source_operations')
    if not isinstance(operations, list) or not 1 <= len(operations) <= 32:
        raise ValueError('source_operations must contain 1..32 explicit source edits')
    ids = set()
    inset = contract.get('source_stroke_inset_pixels', 3)
    for op in operations:
        if not isinstance(op, dict) or not isinstance(op.get('id'), str) or op['id'] in ids:
            raise ValueError('source operations require unique string IDs')
        ids.add(op['id'])
        box = op.get('box')
        validate_regions([box], True, contract['source_size_pixels'])
        if not any(a <= box[0] < box[2] <= c and b <= box[1] < box[3] <= d for a,b,c,d in boxes):
            raise ValueError('operation outside declared target boxes')
        if op.get('kind') not in ('text', 'curve', 'highlight'):
            raise ValueError('unknown source operation')
        maximum = 18 if contract.get('source_viewport') else 3
        if type(op.get('step')) is not int or not 1 <= op['step'] <= maximum:
            raise ValueError(f'source operation step must be in 1..{maximum}')
        if not isinstance(op.get('reason'), str) or not op['reason'].strip():
            raise ValueError('each edit needs its task-specific target and reason')
        if op['kind'] == 'text' and (not isinstance(op.get('text'), str) or not op['text'].strip()):
            raise ValueError('text operation needs an explicit answer')
        if op['kind'] == 'curve':
            points = op.get('points', [])
            if not isinstance(points, list) or not 2 <= len(points) <= 96:
                raise ValueError('curve needs 2..96 source-pixel points')
            for point in points:
                if (not isinstance(point, list) or len(point) != 2 or
                    any(type(v) not in (int, float) for v in point) or
                    not (box[0]+inset <= point[0] <= box[2]-inset and box[1]+inset <= point[1] <= box[3]-inset)):
                    raise ValueError('curve point leaves its edit box with stroke margin')
    # Check actual helper geometry before a plan can become immutable. In
    # particular, an unreadably small answer box must not become frozen.
    if contract.get('source_image'):
        from manim import tempconfig
        from generation.source_primitives import SourcePrimitives
        with tempconfig({'pixel_width': 854, 'pixel_height': 480}):
            primitives = SourcePrimitives(contract['source_image'], boxes, contract.get('source_viewport'),
                                          min_label_pixels=0 if contract.get('generation_profile') == 'draft' else 16)
            for op in operations:
                if op['kind'] == 'text':
                    primitives.text(op['text'], op['box'])
                elif op['kind'] == 'curve':
                    primitives.curve(op['points'], op['box'])
                else:
                    primitives.highlight(op['box'])
    return operations


def compile_plan(plan, contract):
    operations = validate_plan(plan, contract)
    lines = ['from manim import *', 'class Section1Scene(Scene):', '    def construct(self):']
    for step in sorted({op['step'] for op in operations}):
        names = []
        for index, op in enumerate(operations):
            if op['step'] != step:
                continue
            name = f'edit_{index}'
            color = op.get('color', '#D62728')
            if op['kind'] == 'text':
                expr = f'self.source_text({op["text"]!r}, {op["box"]!r}, color={op.get("color", "#000000")!r})'
            elif op['kind'] == 'curve':
                expr = f'self.source_curve({op["points"]!r}, {op["box"]!r}, color={color!r})'
            else:
                expr = f'self.source_highlight({op["box"]!r}, color={color!r})'
            lines.append(f'        {name} = {expr}')
            names.append(f'FadeIn({name})' if op['kind'] == 'text' else f'Create({name})')
        lines.append('        self.play(' + ', '.join(names) + ', run_time=0.7)')
    return '\n'.join(lines) + '\n'


def review_plan(api, plan, contract):
    """A separate, grounded planning check; no model score is silently promoted."""
    from generation.strict_video_contract import ContractAPI
    if isinstance(api, ContractAPI):
        # Do not leak failed attempts into a reviewer judging the new plan.
        current = {key: value for key, value in contract.items()
                   if key not in ('quality_feedback', 'storyboard_repair')}
        api = ContractAPI(current, api.output, include_render_diagnostics=False)
    geometry = {'validated_by_code': True, 'source_size_pixels': contract['source_size_pixels'],
                'edit_union_fraction': region_union_area(plan['source_edit_regions']) / (contract['source_size_pixels'][0]*contract['source_size_pixels'][1])}
    prompt = ('Geometry and the 25% union area limit have already been checked by deterministic code. '
              'Use those supplied measurements; focus on semantic correctness and task coverage. '
              'Review ONLY the proposed plan below. Previous quality_feedback, render diagnostics and '
              'generation errors describe older attempts, not defects in this plan. Narration synthesis '
              'duration is checked separately after rendering; do not reject source edits because older speech overran. '
              'Inspect the actual supplied source image and the proposed source-pixel edits against the CURRENT task. '
              'Check EVERY requested answer, its exact target position, graph/board rules and unchanged objects. '
              'Reject missing answers, guessed unrelated diagrams, incorrect spatial locations, paths through blockers, '
              'or annotations that merely claim completion. Coordinates are ORIGINAL image pixels. '
              'Return only JSON {"valid":boolean,"finding":string}. Be conservative; no unsupported claims. '
              'Do not propose widening target boxes.\nMEASURED GEOMETRY:\n' + json.dumps(geometry) + '\nPROPOSED PLAN:\n' + json.dumps(plan, ensure_ascii=False))
    response, _ = api(prompt, max_tokens=1500)
    text = response.choices[0].message.content.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    result = json.loads(text)
    if type(result.get('valid')) is not bool or not isinstance(result.get('finding'), str):
        raise ValueError('source-plan reviewer returned invalid schema')
    return result
