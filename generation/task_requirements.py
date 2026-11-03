"""Current task obligations shared by planning and video acceptance.

Historical instructions deliberately never enter this list. The complete prompt
remains an obligation so list metadata cannot silently narrow the request.
"""

def requirements(case):
    rows = []
    prompt = case.get('prompt_text')
    if isinstance(prompt, str) and prompt.strip():
        rows.append({'id': 'prompt', 'text': prompt, 'kind': 'instruction'})
    for field in ('expected_concepts', 'expected_visual_elements', 'expected_narrative_order', 'discipline_specific_rubric'):
        values = case.get(field) or []
        if not isinstance(values, list):
            raise ValueError(f'{field} must be a list')
        for index, value in enumerate(values):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{field} contains an empty or non-text requirement')
            rows.append({'id': f'{field}:{index}', 'text': value, 'kind': field})
    if not rows or rows[0]['id'] != 'prompt':
        raise ValueError('current task needs a nonempty prompt_text')
    return rows
